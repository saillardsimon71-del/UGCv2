"""Moteurs GPU distants sur Modal — contrat unique, dépense explicite.

Principes (repris du parcours prouvé du studio précédent) :
- Aucun appel si `STUDIO_MODAL_ENABLED=0` → le moteur se déclare indisponible
  avec la raison, le job échoue proprement ou retombe sur une simulation
  *étiquetée* si elle est autorisée. Jamais de faux rendu.
- `spawn()` + sondage : l'annulation depuis l'UI tue le conteneur GPU
  (`terminate_containers=True`) — pas de GPU qui tourne dans le vide.
- Le MP4 retourné est probé avant d'être accepté comme artefact.
- Coût enregistré à partir des secondes GPU retournées par le worker.

Contrat worker (deploy/modal_*_worker.py) : fonction distante qui reçoit des
fichiers en base64 et retourne {"video_b64"|"audio_b64", "metadata": {...}}.
Limite assumée v1 : adaptée aux clips courts (quelques dizaines de Mo).
Les longs formats passeront par un Volume Modal (voir docs/ROADMAP).
"""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from .. import media
from ..config import get_settings
from .base import Engine, EngineInfo, EngineOutput, EngineRequest, Usage

# kind -> (app setting attr, fonction distante, gpu, libellé, vérifié, maturité)
SPECS = {
    "modal_ltx":            ("video", "app_video", "render_clip", "L40S", "LTX-2.5 — Modal (prouvé)", True, "production"),
    "modal_longcat_avatar": ("avatar", "app_avatar", "render_avatar", "A100_80GB", "LongCat Avatar 1.5 — Modal (prouvé)", True, "production"),
    "modal_facefusion":     ("face_swap", "app_face", "render_faceswap", "A10G", "FaceFusion — Modal", False, "benchmark_planned"),
    "modal_animate2":       ("person_replace", "app_perf", "render_perf", "L40S", "Wan2.2 Animate 2 — Modal/WanGP", False, "benchmark_planned"),
    "modal_scail2":         ("person_replace", "app_perf", "render_perf", "L40S", "SCAIL-2 — Modal/WanGP (challenger)", False, "benchmark_planned"),
    "modal_latentsync":     ("lip_sync", "app_lipsync", "render_lipsync", "A10G", "LatentSync 1.6 — Modal", False, "benchmark_planned"),
    "modal_musetalk":       ("lip_sync", "app_lipsync", "render_lipsync", "L4", "MuseTalk 1.5 (brouillon rapide) — Modal", False, "benchmark_planned"),
    "modal_infinitetalk":   ("avatar", "app_talk", "render_talk", "L40S", "InfiniteTalk — Modal (challenger long)", False, "benchmark_planned"),
    "modal_chatterbox":     ("tts", "app_voice", "render_tts", "L4", "Chatterbox Multilingue V3 — Modal", False, "benchmark_planned"),
    "modal_seedvc":         ("voice_convert", "app_voice", "render_vc", "L4", "Seed-VC (conversion de timbre) — Modal", False, "benchmark_planned"),
}


def _b64(path: Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


class ModalEngine(Engine):
    def __init__(self, name: str):
        kind, app_attr, func, gpu, label, verified, maturity = SPECS[name]
        self.name, self.func_name, self.app_attr = name, func, app_attr
        self.info = EngineInfo(name=name, kind=kind, label=label, requires_gpu=True,
                               provider="modal", gpu=gpu, verified=verified, maturity=maturity,
                               notes="GPU à la demande — dépense confirmée avant lancement.")

    @property
    def app_name(self) -> str:
        return getattr(get_settings(), self.app_attr)

    def _function(self):
        import modal
        s = get_settings()
        if s.modal_workspace:
            ws = modal.Workspace.from_context().hydrate().name
            if ws != s.modal_workspace:
                raise ValueError(f"Workspace Modal inattendu : {ws} (attendu {s.modal_workspace}) — arrêt avant toute dépense.")
        return modal.Function.from_name(self.app_name, self.func_name, environment_name="main").hydrate()

    def available(self):
        if not get_settings().modal_enabled:
            return False, "Modal désactivé (STUDIO_MODAL_ENABLED=1 + jeton requis, voir docs/MODAL.md)"
        try:
            import modal  # noqa: F401
        except ImportError:
            return False, "Package `modal` absent côté serveur (pip install -r backend/requirements-modal.txt)"
        try:
            self._function()
            return True, ""
        except Exception as exc:
            return False, f"Application Modal « {self.app_name} » injoignable ({type(exc).__name__}) — déployée ? (docs/MODAL.md)"

    # -- construction des payloads par moteur --------------------------------
    def _payload(self, r: EngineRequest) -> tuple:
        p, i = r.params, r.inputs
        if self.name == "modal_ltx":
            payload = {"prompt": r.prompt, "duration_s": r.duration_s,
                       "aspect_ratio": r.project.get("format", "9:16"),
                       "seed": int(p.get("seed", 42)), "audio_mode": p.get("audio_mode", "native")}
            ref = i.get("reference_image")
            if ref and Path(ref).is_file():
                png = r.out("reference.png")
                media.run_ffmpeg(["-i", str(ref), "-frames:v", "1", str(png)])
                payload["image_png_base64"] = _b64(png)
            if not 1 <= r.duration_s <= 15:
                raise ValueError("LTX : plans de 1 à 15 secondes")
            return (payload,)
        if self.name == "modal_longcat_avatar":
            audio = Path(i.get("audio_path") or "")
            if not audio.is_file():
                raise ValueError("Avatar : piste audio manquante (générer la voix d'abord)")
            dur = media.probe(audio).duration_s
            if not 0 < dur <= 3.72:
                raise ValueError(f"Pilote LongCat actuel : voix de 3,72 s maximum (reçu {dur:.1f} s). "
                                 "Découper le dialogue en plans courts ; la continuation longue est au benchmark S4.")
            ref = i.get("reference_image")
            if not ref or not Path(ref).is_file():
                raise ValueError("Avatar : personnage avec photo de référence requis")
            png = r.out("reference.png")
            media.run_ffmpeg(["-i", str(ref), "-frames:v", "1", str(png)])
            return (_b64(png), _b64(audio), r.prompt)
        if self.name == "modal_facefusion":
            video, face = Path(i.get("source_path") or ""), Path(i.get("reference_image") or "")
            if not video.is_file() or not face.is_file():
                raise ValueError("Face swap : vidéo source et photo du visage requises")
            return (_b64(video), _b64(face), {"enhancer": p.get("enhancer", "gfpgan_1.4"),
                                              "swapper": p.get("swapper", "inswapper_128_fp16")})
        if self.name in ("modal_animate2", "modal_scail2"):
            video, img = Path(i.get("source_path") or ""), Path(i.get("reference_image") or "")
            if not video.is_file() or not img.is_file():
                raise ValueError("Performance : vidéo de référence et photo du personnage requises")
            model = "animate2" if self.name == "modal_animate2" else "scail2_14B"
            mode = "replace" if r.kind == "person_replace" or p.get("mode") == "replace" else "animate"
            if r.shot.get("kind") == "person_replace":
                mode = "replace"
            return (_b64(video), _b64(img), {"model": model, "mode": mode, "prompt": r.prompt,
                                             "seed": int(p.get("seed", 42))})
        if self.name in ("modal_latentsync", "modal_musetalk"):
            video, audio = Path(i.get("source_path") or ""), Path(i.get("audio_path") or "")
            if not video.is_file() or not audio.is_file():
                raise ValueError("Lip-sync : vidéo et nouvel audio requis")
            return (_b64(video), _b64(audio), {"model": "latentsync16" if "latent" in self.name else "musetalk15"})
        if self.name == "modal_infinitetalk":
            audio = Path(i.get("audio_path") or "")
            ref = i.get("reference_image"); video = i.get("source_path")
            if not audio.is_file() or not (ref or video):
                raise ValueError("InfiniteTalk : audio + (photo ou vidéo) requis")
            return (_b64(audio), _b64(Path(video)) if video else "", _b64(Path(ref)) if ref else "", {"prompt": r.prompt})
        if self.name == "modal_chatterbox":
            text = str(p.get("text") or r.shot.get("dialogue") or "").strip()
            if not text:
                raise ValueError("Voix : texte vide")
            ref = i.get("voice_ref")
            return (text, _b64(Path(ref)) if ref and Path(ref).is_file() else "",
                    {"language": p.get("language", "fr"), "exaggeration": float(p.get("exaggeration", 0.5)),
                     "cfg_weight": float(p.get("cfg_weight", 0.5))})
        if self.name == "modal_seedvc":
            src, ref = Path(i.get("audio_path") or ""), Path(i.get("voice_ref") or "")
            if not src.is_file() or not ref.is_file():
                raise ValueError("Conversion voix : enregistrement source et référence de timbre requis")
            return (_b64(src), _b64(ref), {})
        raise ValueError(f"Moteur Modal inconnu : {self.name}")

    def _save(self, r: EngineRequest, result: dict) -> EngineOutput:
        meta = result.get("metadata", {})
        r.out("modal_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        seconds = float(meta.get("gpu_wall_seconds", meta.get("generation_seconds", 0)) or 0)
        out = EngineOutput(usage=Usage(provider="modal", gpu=self.info.gpu, gpu_seconds=seconds,
                                        notes="Secondes GPU retournées par le worker Modal"),
                            diagnostics=meta)
        if result.get("audio_b64"):
            path = r.out(f"{self.name}.wav")
            path.write_bytes(base64.b64decode(result["audio_b64"], validate=True))
            out.add(path, "audio", "audio/wav", engine=self.name, simulated=False)
            return out
        key = "video_b64" if "video_b64" in result else "video_base64"
        if key not in result:
            raise ValueError("Modal n'a retourné ni vidéo ni audio")
        path = r.out(f"{self.name}.mp4")
        path.write_bytes(base64.b64decode(result[key], validate=True))
        info = media.probe(path)
        if not info.width or info.duration_s <= 0:
            raise ValueError("Modal n'a pas retourné une vidéo lisible")
        out.add(path, "video", "video/mp4", engine=self.name, simulated=False)
        return out

    def run(self, request: EngineRequest, ctx) -> EngineOutput:
        if not request.params.get("confirm_spend"):
            raise ValueError("Dépense GPU non confirmée : relancer avec confirmation (confirm_spend) depuis l'interface.")
        payload = self._payload(request)
        ctx.check_cancelled()
        call = self._function().spawn(*payload)
        request.out("modal_call.json").write_text(
            json.dumps({"call_id": call.object_id, "app": self.app_name, "function": self.func_name}), encoding="utf-8")
        ctx.log(f"Rendu Modal lancé ({self.app_name}/{self.func_name})", progress=0.2, stage="generate")
        started, complete = time.monotonic(), False
        try:
            while True:
                ctx.check_cancelled()
                if time.monotonic() - started > 2100:
                    raise TimeoutError("Modal : délai maximal de rendu dépassé (35 min)")
                try:
                    result = call.get(timeout=5)
                    complete = True
                    return self._save(request, result)
                except TimeoutError:
                    ctx.log("Rendu Modal en cours…", progress=0.4, stage="generate")
                    continue
        finally:
            if not complete:
                call.cancel(terminate_containers=True)
