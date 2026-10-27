"""Jobs asynchrones — un thread dispatcher, un GPU à la fois, reprise au boot.

Pipelines composés (dans ce module, pas dans une couche abstraite) :
- avatar : dialogue → voix (si pas d'audio fourni) → moteur avatar → QC
- doublage : (voix) → lip-sync → QC
- les autres recettes : moteur unique → QC
L'original n'est jamais modifié : chaque génération ajoute une *prise*
(artifact) au plan ; l'utilisateur compare et sélectionne.
"""
from __future__ import annotations

import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from . import db, qc
from .config import get_settings
from .engines import registry
from .engines.base import EngineRequest, JobCancelled, Usage

_executor: ThreadPoolExecutor | None = None
_dispatcher: threading.Thread | None = None
_running: set[str] = set()
_lock = threading.Lock()
_logs: dict[str, list[str]] = {}


class Ctx:
    def __init__(self, job_id: str):
        self.job_id = job_id

    def log(self, message: str, progress: float | None = None, stage: str = "") -> None:
        _logs.setdefault(self.job_id, []).append(f"[{time.strftime('%H:%M:%S')}] {message}")
        data: dict[str, Any] = {}
        if progress is not None:
            data["progress"] = max(0.0, min(1.0, progress))
        if stage:
            data["stage"] = stage
        if data:
            db.update("jobs", self.job_id, data)

    def check_cancelled(self) -> None:
        job = db.get("jobs", self.job_id)
        if job and job["status"] == "cancelled":
            raise JobCancelled("Job annulé par l'utilisateur")


def log_of(job_id: str) -> list[str]:
    return _logs.get(job_id, [])


def enqueue(job_type: str, project_id: str | None, shot_id: str | None,
            engine: str, params: dict[str, Any]) -> dict[str, Any]:
    job = db.insert("jobs", {"id": db.new_id("job"), "project_id": project_id, "shot_id": shot_id,
                             "type": job_type, "engine": engine, "params": params,
                             "status": "queued", "created_at": db.now_iso()})
    return job


def start() -> None:
    global _executor, _dispatcher
    db.init()
    # Reprise : les jobs « running » d'un process mort repartent en file
    for job in db.find("jobs", "status = 'running'"):
        db.update("jobs", job["id"], {"status": "queued", "progress": 0})
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=max(1, get_settings().max_workers), thread_name_prefix="studio-job")
    if _dispatcher is None or not _dispatcher.is_alive():
        _dispatcher = threading.Thread(target=_dispatch_loop, daemon=True, name="studio-dispatcher")
        _dispatcher.start()


def _dispatch_loop() -> None:
    while True:
        try:
            queued = db.find("jobs", "status = 'queued'", order="created_at ASC")
            for job in queued:
                with _lock:
                    if job["id"] in _running or len(_running) >= max(1, get_settings().max_workers):
                        continue
                    _running.add(job["id"])
                _executor.submit(_run_job, job["id"])  # type: ignore[union-attr]
        except Exception:
            traceback.print_exc()
        time.sleep(0.4)


# --------------------------------------------------------------------------- #
def _asset_path(asset_id: str | None) -> str | None:
    if not asset_id:
        return None
    a = db.get("assets", asset_id)
    return a["path"] if a else None


def _character_image(character_id: str | None) -> str | None:
    if not character_id:
        return None
    c = db.get("characters", character_id)
    return _asset_path(c["ref_asset_id"]) if c else None


def _voice_ref(voice_id: str | None) -> str | None:
    if not voice_id:
        return None
    v = db.get("voices", voice_id)
    return _asset_path(v["ref_asset_id"]) if v else None


def _latest_audio(shot_id: str) -> str | None:
    arts = db.find("artifacts", "shot_id = ? AND kind = 'audio'", (shot_id,), order="created_at DESC")
    return arts[0]["path"] if arts else None


def _job_dir(job: dict) -> Path:
    base = get_settings().data_dir / "projects" / (job.get("project_id") or "_misc") / "jobs" / job["id"]
    base.mkdir(parents=True, exist_ok=True)
    return base


def _store_outputs(job: dict, output, ctx: Ctx) -> list[dict]:
    stored = []
    for art in output.artifacts:
        row = db.insert("artifacts", {"id": db.new_id("art"), "job_id": job["id"],
                                      "project_id": job.get("project_id"), "shot_id": job.get("shot_id"),
                                      "kind": art["kind"], "path": art["path"], "mime": art["mime"],
                                      "bytes": art["bytes"], "meta": art["meta"],
                                      "created_at": db.now_iso()})
        stored.append(row)
    if output.usage and (output.usage.gpu_seconds or output.usage.provider != "local"):
        u: Usage = output.usage
        db.insert("cost_events", {"id": db.new_id("cost"), "project_id": job.get("project_id"), "job_id": job["id"],
                                  "provider": u.provider, "gpu": u.gpu, "gpu_seconds": u.gpu_seconds,
                                  "rate_usd_hr": u.rate_usd_hr or get_settings().rate_for(u.provider, u.gpu),
                                  "usd": u.cost_usd(), "note": u.notes, "created_at": db.now_iso()})
        db.update("jobs", job["id"], {"provider": u.provider, "gpu": u.gpu,
                                      "gpu_seconds": u.gpu_seconds, "cost_usd": u.cost_usd()})
    return stored


def _run_engine(job: dict, engine_name: str, kind: str, shot: dict, project: dict,
                params: dict, inputs: dict, ctx: Ctx, request_kind: str | None = None):
    engine = registry.get_engine(engine_name)
    req = EngineRequest(kind=request_kind or kind, output_dir=_job_dir(job),
                        project=project, shot=shot, params=params, inputs=inputs)
    out = engine.run(req, ctx)
    if engine.info.simulated:
        db.update("jobs", job["id"], {"simulated": 1})
        ctx.log("⚠ Résultat SIMULÉ (plaque de test) — aucun modèle IA n'a tourné.", stage="simulated")
    return out


def _pipeline_generate_shot(job: dict, ctx: Ctx) -> None:
    shot = db.get("shots", job["shot_id"])
    project = db.get("projects", job["project_id"]) or {}
    params = dict(job.get("params") or {})
    psettings = (project.get("settings") or {})
    pinputs = psettings.get("inputs") or {}
    kind = shot["kind"]
    kind_map = {"avatar": "avatar", "b_roll": "video", "face_swap": "face_swap",
                "person_replace": "person_replace", "motion_transfer": "motion_transfer",
                "lip_sync": "lip_sync", "voice_only": "tts"}
    need = kind_map.get(kind, "video")
    inputs = {"reference_image": _character_image(shot.get("character_id") or pinputs.get("character_id")),
              "source_path": _asset_path(shot.get("source_asset_id") or pinputs.get("video_asset_id")),
              "voice_ref": _voice_ref(shot.get("voice_id"))}
    audio_path = _asset_path(pinputs.get("audio_asset_id")) or _latest_audio(shot["id"])

    # Étape voix (avatar / doublage) : seulement si aucun audio n'existe —
    # une vraie performance fournie n'est jamais régénérée.
    if kind in ("avatar", "lip_sync") and not audio_path:
        if not (shot.get("dialogue") or "").strip():
            raise ValueError("Dialogue vide et aucun audio fourni : écrire le texte du plan ou importer un enregistrement.")
        tts_engine, why = registry.resolve("tts", params.get("voice_engine"))
        if tts_engine is None:
            raise ValueError(f"Voix indisponible — {why}")
        ctx.log(f"Étape voix : {tts_engine.info.label}", progress=0.05, stage="voice")
        vout = _run_engine(job, tts_engine.info.name, "tts", shot, project, params, inputs, ctx)
        _store_outputs(job, vout, ctx)
        audio_path = next((a["path"] for a in vout.artifacts if a["kind"] == "audio"), None)
        if not audio_path:
            raise ValueError("Le moteur voix n'a produit aucun audio")
    inputs["audio_path"] = audio_path

    if kind == "voice_only":
        engine, why = registry.resolve("tts", params.get("engine"))
        if engine is None:
            raise ValueError(why)
        out = _run_engine(job, engine.info.name, "tts", shot, project, params, inputs, ctx)
        _store_outputs(job, out, ctx)
        db.update("shots", shot["id"], {"status": "voiced", "updated_at": db.now_iso()})
        return

    engine, why = registry.resolve(need, params.get("engine"))
    if engine is None:
        raise ValueError(why)
    ctx.log(f"Moteur : {engine.info.label}", progress=0.15, stage="generate")
    if params.get("confirm_spend") is None and engine.info.provider == "modal":
        params["confirm_spend"] = bool(job.get("params", {}).get("confirm_spend"))
    out = _run_engine(job, engine.info.name, need, shot, project, params, inputs, ctx)
    stored = _store_outputs(job, out, ctx)

    # QC automatique sur la prise vidéo + sélection si première prise
    videos = [a for a in stored if a["kind"] == "video"]
    if videos:
        chosen = videos[0]
        try:
            report = qc.inspect_clip(chosen["path"], expected_duration_s=float(shot.get("duration_s") or 0) or None,
                                     expected_aspect=project.get("format", "9:16"))
        except Exception as exc:
            report = {"verdict": "review", "checks": [], "metrics": {}, "error": str(exc)}
        upd: dict[str, Any] = {"status": "generated", "qc": report, "updated_at": db.now_iso()}
        if not shot.get("selected_artifact"):
            upd["selected_artifact"] = chosen["id"]
        db.update("shots", shot["id"], upd)
        ctx.log(f"QC automatique : {report.get('verdict')} (emballage — la qualité du jeu reste à valider à l'œil)",
                progress=0.95, stage="qc")


def _pipeline_export(job: dict, ctx: Ctx) -> None:
    project = db.get("projects", job["project_id"]) or {}
    shots = db.find("shots", "project_id = ?", (job["project_id"],), order="idx ASC")
    clips = []
    for s in shots:
        art = db.get("artifacts", s["selected_artifact"]) if s.get("selected_artifact") else None
        if art and art["kind"] == "video":
            clips.append({"path": art["path"], "duration_s": s["duration_s"], "dialogue": s.get("dialogue", ""),
                          "title": s.get("title", ""), "kind": s["kind"]})
    if not clips:
        raise ValueError("Export impossible : aucun plan n'a de prise vidéo sélectionnée. Générer au moins un plan.")
    params = dict(job.get("params") or {})
    params.setdefault("format", project.get("format", "9:16"))
    engine = registry.get_engine("ffmpeg_assembly")
    req = EngineRequest(kind="assembly", output_dir=_job_dir(job), project=project,
                        params=params, inputs={"clips": clips})
    out = engine.run(req, ctx)
    stored = _store_outputs(job, out, ctx)
    main = next((a for a in stored if a["kind"] in ("video", "export")), None)
    if not main:
        raise ValueError("Le montage n'a produit aucune vidéo")
    poster = next((a["path"] for a in stored if a["kind"] in ("poster", "image")), None)
    srt = next((a["path"] for a in stored if a["kind"] == "subtitles"), None)
    report = qc.inspect_export(main["path"], {"format": project.get("format", "9:16")})
    any_sim = any((a.get("meta") or {}).get("simulated") for a in db.find(
        "artifacts", "project_id = ?", (job["project_id"],)) if a["id"] in {s.get("selected_artifact") for s in shots})
    db.insert("exports", {"id": db.new_id("exp"), "project_id": job["project_id"], "path": main["path"],
                          "poster": poster, "srt_path": srt,
                          "spec": {"format": project.get("format"), "clips": len(clips), "contains_simulation": bool(any_sim)},
                          "qc": report, "created_at": db.now_iso()})
    if any_sim:
        ctx.log("⚠ Cet export contient des plaques SIMULÉES — il valide le montage, pas les modèles.", stage="simulated")
        db.update("jobs", job["id"], {"simulated": 1})
    ctx.log(f"Export terminé · QC {report.get('verdict')}", progress=1.0, stage="done")


def _pipeline_analyse(job: dict, ctx: Ctx) -> None:
    params = job.get("params") or {}
    src = _asset_path(params.get("asset_id")) or params.get("source_path")
    if not src:
        raise ValueError("Analyse : asset introuvable")
    engine = registry.get_engine("analysis")
    req = EngineRequest(kind="analysis", output_dir=_job_dir(job), params=params, inputs={"source_path": src})
    out = engine.run(req, ctx)
    _store_outputs(job, out, ctx)
    asset = db.get("assets", params.get("asset_id") or "")
    if asset:
        meta = dict(asset.get("meta") or {})
        meta["analysis"] = out.diagnostics
        db.update("assets", asset["id"], {"meta": meta})


PIPELINES = {"generate_shot": _pipeline_generate_shot, "export": _pipeline_export, "analyse": _pipeline_analyse}


def _run_job(job_id: str) -> None:
    job = db.get("jobs", job_id)
    if not job or job["status"] == "cancelled":
        with _lock:
            _running.discard(job_id)
        return
    db.update("jobs", job_id, {"status": "running", "started_at": db.now_iso(),
                               "attempts": int(job.get("attempts") or 0) + 1})
    ctx = Ctx(job_id)
    try:
        PIPELINES[job["type"]](job, ctx)
        fresh = db.get("jobs", job_id)
        upd = {"status": "succeeded", "progress": 1.0, "finished_at": db.now_iso()}
        if fresh.get("simulated"):
            upd["error"] = "Résultat simulé (plaque de test) : aucun moteur IA réel n'était disponible."
        db.update("jobs", job_id, upd)
        ctx.log("Terminé", progress=1.0, stage="done")
    except JobCancelled:
        db.update("jobs", job_id, {"status": "cancelled", "finished_at": db.now_iso()})
    except Exception as exc:
        _logs.setdefault(job_id, []).append(traceback.format_exc())
        db.update("jobs", job_id, {"status": "failed", "error": f"{type(exc).__name__}: {exc}",
                                   "finished_at": db.now_iso()})
    finally:
        # Le plan est mis à jour AVANT la fin du job (l'UI sonde les jobs)
        with _lock:
            _running.discard(job_id)
