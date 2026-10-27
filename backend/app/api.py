"""API REST du studio. Une seule origine : l'UI statique est servie par ce
même process en production ; en dev, Vite proxifie /api et /files."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import db, director, jobs, recipes
from .config import get_settings
from .engines import registry

router = APIRouter(prefix="/api")

ALLOWED = {".mp4", ".mov", ".webm", ".mkv", ".png", ".jpg", ".jpeg", ".webp",
           ".wav", ".mp3", ".m4a", ".ogg", ".flac"}
KIND_BY_EXT = {**{e: "video" for e in (".mp4", ".mov", ".webm", ".mkv")},
               **{e: "image" for e in (".png", ".jpg", ".jpeg", ".webp")},
               **{e: "audio" for e in (".wav", ".mp3", ".m4a", ".ogg", ".flac")}}


def _404(what: str):
    raise HTTPException(404, f"{what} introuvable")


class ProjectIn(BaseModel):
    name: str
    brief: str = ""
    recipe: str = "create"
    format: str = "9:16"
    quality: str = "production"


class ShotIn(BaseModel):
    title: str = ""
    kind: str = "b_roll"
    duration_s: float = 5.0
    dialogue: str = ""
    prompt: str = ""
    character_id: str | None = None
    voice_id: str | None = None
    source_asset_id: str | None = None


class GenerateIn(BaseModel):
    engine: str | None = None
    voice_engine: str | None = None
    seed: int = 42
    confirm_spend: bool = False


# ---------------------------------------------------------------- système
@router.get("/system")
def system():
    return registry.system_report()


@router.get("/recipes")
def list_recipes():
    return {"recipes": recipes.list_recipes(), "qualities": recipes.QUALITIES}


# ---------------------------------------------------------------- projets
@router.get("/projects")
def projects():
    out = []
    for p in db.find("projects"):
        p["shots_count"] = len(db.find("shots", "project_id = ?", (p["id"],)))
        p["exports_count"] = len(db.find("exports", "project_id = ?", (p["id"],)))
        out.append(p)
    return out


@router.post("/projects")
def create_project(body: ProjectIn):
    now = db.now_iso()
    recipe = recipes.RECIPES.get(body.recipe)
    if not recipe:
        raise HTTPException(400, f"Recette inconnue : {body.recipe}")
    p = db.insert("projects", {"id": db.new_id("prj"), "name": body.name, "brief": body.brief,
                               "recipe": body.recipe, "format": body.format, "quality": body.quality,
                               "status": "draft", "settings": {"inputs": {}}, "created_at": now, "updated_at": now})
    # Un premier plan prêt à travailler (kind déterminé par la recette)
    db.insert("shots", {"id": db.new_id("shot"), "project_id": p["id"], "idx": 0, "kind": recipe["shot_kind"],
                        "title": "Plan 1", "duration_s": 6.0, "dialogue": "", "prompt": "",
                        "created_at": now, "updated_at": now})
    return get_project(p["id"])


@router.get("/projects/{pid}")
def get_project(pid: str):
    p = db.get("projects", pid) or _404("Projet")
    p["shots"] = db.find("shots", "project_id = ?", (pid,), order="idx ASC")
    for s in p["shots"]:
        s["takes"] = db.find("artifacts", "shot_id = ?", (s["id"],), order="created_at ASC")
    p["assets"] = db.find("assets", "project_id = ?", (pid,))
    p["exports"] = db.find("exports", "project_id = ?", (pid,))
    return p


@router.patch("/projects/{pid}")
def patch_project(pid: str, body: dict[str, Any]):
    allowed = {"name", "brief", "format", "quality", "status", "settings"}
    upd = {k: v for k, v in body.items() if k in allowed}
    upd["updated_at"] = db.now_iso()
    return db.update("projects", pid, upd) or _404("Projet")


@router.delete("/projects/{pid}")
def delete_project(pid: str):
    for s in db.find("shots", "project_id = ?", (pid,)):
        db.delete("shots", s["id"])
    db.delete("projects", pid)
    return {"ok": True}


@router.get("/projects/{pid}/plan")
def project_plan(pid: str):
    p = db.get("projects", pid) or _404("Projet")
    shots = db.find("shots", "project_id = ?", (pid,), order="idx ASC")
    return recipes.plan_production(p, shots, registry.availability_map())


@router.get("/projects/{pid}/costs")
def project_costs(pid: str):
    events = db.find("cost_events", "project_id = ?", (pid,), order="created_at ASC")
    jobs_ = db.find("jobs", "project_id = ?", (pid,))
    exports = db.find("exports", "project_id = ?", (pid,))
    total = round(sum(e["usd"] for e in events), 4)
    succ = [j for j in jobs_ if j["status"] == "succeeded"]
    return {"cost_usd": total, "gpu_seconds": round(sum(e["gpu_seconds"] for e in events), 1),
            "jobs": len(jobs_), "jobs_succeeded": len(succ), "exports": len(exports),
            "cost_per_export_usd": round(total / len(exports), 4) if exports else None,
            "note": "Les tentatives échouées comptent aussi : c'est le coût par vidéo acceptée qui compte."}


# ---------------------------------------------------------------- plans
@router.post("/projects/{pid}/shots")
def add_shot(pid: str, body: ShotIn):
    shots = db.find("shots", "project_id = ?", (pid,))
    now = db.now_iso()
    return db.insert("shots", {"id": db.new_id("shot"), "project_id": pid, "idx": len(shots),
                               **body.model_dump(), "created_at": now, "updated_at": now})


@router.patch("/shots/{sid}")
def patch_shot(sid: str, body: dict[str, Any]):
    allowed = {"title", "kind", "duration_s", "dialogue", "prompt", "character_id",
               "voice_id", "source_asset_id", "status", "selected_artifact", "params", "human_review"}
    upd = {k: v for k, v in body.items() if k in allowed}
    upd["updated_at"] = db.now_iso()
    return db.update("shots", sid, upd) or _404("Plan")


@router.delete("/shots/{sid}")
def delete_shot(sid: str):
    shot = db.get("shots", sid) or _404("Plan")
    db.delete("shots", sid)
    for i, s in enumerate(db.find("shots", "project_id = ?", (shot["project_id"],), order="idx ASC")):
        db.update("shots", s["id"], {"idx": i})
    return {"ok": True}


@router.post("/projects/{pid}/storyboard")
def make_storyboard(pid: str):
    p = db.get("projects", pid) or _404("Projet")
    plans, source = director.storyboard(p.get("brief") or p["name"], p.get("recipe", "create"))
    for s in db.find("shots", "project_id = ?", (pid,)):
        db.delete("shots", s["id"])
    now = db.now_iso()
    for pl in plans:
        db.insert("shots", {"id": db.new_id("shot"), "project_id": pid, "created_at": now, "updated_at": now, **pl})
    return {"source": source, "shots": db.find("shots", "project_id = ?", (pid,), order="idx ASC")}


# ---------------------------------------------------------------- jobs
@router.post("/shots/{sid}/generate")
def generate_shot(sid: str, body: GenerateIn):
    shot = db.get("shots", sid) or _404("Plan")
    job = jobs.enqueue("generate_shot", shot["project_id"], sid, body.engine or "auto",
                       body.model_dump())
    return job


@router.post("/projects/{pid}/generate-all")
def generate_all(pid: str, body: GenerateIn):
    created = [jobs.enqueue("generate_shot", pid, s["id"], body.engine or "auto", body.model_dump())
               for s in db.find("shots", "project_id = ?", (pid,), order="idx ASC")]
    return {"jobs": created}


@router.post("/projects/{pid}/export")
def export_project(pid: str, body: dict[str, Any] | None = None):
    return jobs.enqueue("export", pid, None, "ffmpeg_assembly", body or {})


@router.get("/jobs")
def list_jobs(limit: int = 50):
    return db.find("jobs", order="created_at DESC")[:limit]


@router.get("/jobs/{jid}")
def get_job(jid: str):
    job = db.get("jobs", jid) or _404("Job")
    job["log"] = jobs.log_of(jid)
    return job


@router.post("/jobs/{jid}/cancel")
def cancel_job(jid: str):
    return db.update("jobs", jid, {"status": "cancelled"}) or _404("Job")


@router.post("/artifacts/{aid}/rate")
def rate_artifact(aid: str, body: dict[str, Any]):
    return db.update("artifacts", aid, {"rating": int(body.get("rating", 0))}) or _404("Prise")


# ---------------------------------------------------------------- assets
@router.post("/assets/upload")
async def upload(file: UploadFile = File(...), project_id: str = Form(""),
                 role: str = Form("source"), rights_note: str = Form("")):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"Format non supporté : {ext}")
    dest_dir = get_settings().data_dir / "uploads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    asset_id = db.new_id("asset")
    dest = dest_dir / f"{asset_id}{ext}"
    data = await file.read()
    if len(data) > 800 * 1024 * 1024:
        raise HTTPException(413, "Fichier > 800 Mo")
    dest.write_bytes(data)
    return db.insert("assets", {"id": asset_id, "project_id": project_id or None,
                                "name": file.filename, "kind": KIND_BY_EXT[ext], "path": str(dest),
                                "mime": file.content_type or mimetypes.guess_type(dest.name)[0] or "",
                                "role": role, "rights_note": rights_note, "meta": {},
                                "created_at": db.now_iso()})


@router.get("/assets")
def list_assets():
    return db.find("assets")


@router.post("/assets/{aid}/analyse")
def analyse_asset(aid: str):
    asset = db.get("assets", aid) or _404("Asset")
    return jobs.enqueue("analyse", asset.get("project_id"), None, "analysis", {"asset_id": aid})


@router.get("/assets/{aid}/file")
def asset_file(aid: str):
    a = db.get("assets", aid) or _404("Asset")
    return _safe_file(Path(a["path"]))


@router.get("/artifacts/{aid}/file")
def artifact_file(aid: str):
    a = db.get("artifacts", aid) or _404("Prise")
    return _safe_file(Path(a["path"]))


@router.get("/exports/{eid}/file")
def export_file(eid: str):
    e = db.get("exports", eid) or _404("Export")
    return _safe_file(Path(e["path"]))


def _safe_file(path: Path) -> FileResponse:
    root = get_settings().data_dir.resolve()
    p = path.resolve()
    if not str(p).startswith(str(root)) or not p.is_file():
        raise HTTPException(404, "Fichier introuvable")
    return FileResponse(p, media_type=mimetypes.guess_type(p.name)[0] or "application/octet-stream",
                        filename=p.name)


# ---------------------------------------------------------------- perso/voix
class CharacterIn(BaseModel):
    name: str
    description: str = ""
    ref_asset_id: str | None = None
    consent: bool = False


class VoiceIn(BaseModel):
    name: str
    language: str = "fr"
    ref_asset_id: str | None = None
    transcript: str = ""
    consent: bool = False


@router.get("/characters")
def characters():
    return db.find("characters")


@router.post("/characters")
def create_character(body: CharacterIn):
    now = db.now_iso()
    return db.insert("characters", {"id": db.new_id("char"), "consent": int(body.consent),
                                    "created_at": now, "updated_at": now,
                                    **{k: v for k, v in body.model_dump().items() if k != "consent"}})


@router.patch("/characters/{cid}")
def patch_character(cid: str, body: dict[str, Any]):
    upd = {k: v for k, v in body.items() if k in ("name", "description", "ref_asset_id", "voice_id", "refs")}
    if "consent" in body:
        upd["consent"] = int(bool(body["consent"]))
    upd["updated_at"] = db.now_iso()
    return db.update("characters", cid, upd) or _404("Personnage")


@router.delete("/characters/{cid}")
def delete_character(cid: str):
    db.delete("characters", cid)
    return {"ok": True}


@router.get("/voices")
def voices():
    return db.find("voices")


@router.post("/voices")
def create_voice(body: VoiceIn):
    return db.insert("voices", {"id": db.new_id("voice"), "consent": int(body.consent),
                                "created_at": db.now_iso(),
                                **{k: v for k, v in body.model_dump().items() if k != "consent"}})


@router.patch("/voices/{vid}")
def patch_voice(vid: str, body: dict[str, Any]):
    upd = {k: v for k, v in body.items() if k in ("name", "language", "ref_asset_id", "transcript", "params")}
    if "consent" in body:
        upd["consent"] = int(bool(body["consent"]))
    return db.update("voices", vid, upd) or _404("Voix")


@router.delete("/voices/{vid}")
def delete_voice(vid: str):
    db.delete("voices", vid)
    return {"ok": True}
