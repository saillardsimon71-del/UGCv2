"""Plaques de test — SIMULATION explicitement étiquetée, jamais un rendu IA.

Sert uniquement à valider la chaîne de production (jobs, timeline, montage,
sous-titres, QC, export) quand aucun moteur GPU n'est disponible. Chaque
plaque porte le filigrane « SIMULATION ». Désactivable : STUDIO_ALLOW_MOCK=0
(un job échoue alors proprement au lieu de simuler).
"""
from __future__ import annotations

from .. import graphics, media
from .base import Engine, EngineInfo, EngineOutput, EngineRequest

COLOURS = ["0x1d3557", "0x2a9d8f", "0xe76f51", "0x6d597a", "0x457b9d", "0xe9c46a"]


class TestPlateEngine(Engine):
    def __init__(self, kind: str):
        self.kind = kind
        self.info = EngineInfo(name=f"mock_{kind}", kind=kind, label=f"Plaque de test ({kind}) — SIMULATION",
                               simulated=True, verified=True, maturity="production",
                               notes="Valide la chaîne studio uniquement. Ne prouve rien sur la qualité des modèles.")

    def available(self):
        from ..config import get_settings
        if not get_settings().allow_mock:
            return False, "Simulations désactivées (STUDIO_ALLOW_MOCK=0)"
        return True, ""

    def run(self, request: EngineRequest, ctx) -> EngineOutput:
        if self.kind in ("tts", "voice_convert"):
            return self._audio(request, ctx)
        w, h = {"9:16": (720, 1280), "16:9": (1280, 720), "1:1": (960, 960)}.get(
            request.project.get("format", "9:16"), (720, 1280))
        dur = max(1.0, min(request.duration_s, 30.0))
        idx = int(request.shot.get("idx") or 0)
        colour = COLOURS[idx % len(COLOURS)]
        label = (request.shot.get("title") or request.kind or "Plan")[:40]
        ass = request.out("plate.ass")
        events = [
            graphics.Event(0, dur, "SIMULATION — PAS UN RENDU IA", style="Title"),
            graphics.Event(0, dur, f"{label} · moteur {self.kind} non branché", style="Caption"),
        ]
        # NB : aucun sous-titre de dialogue ici — tout le texte appartient au
        # montage (post-production), sinon il serait incrusté deux fois.
        graphics.build_ass(events, ass, w, h)
        out_path = request.out("plate.mp4")
        # Léger mouvement (zoom lent) pour que le QC « image figée » reste significatif
        vf = (f"zoompan=z='min(1+0.08*on/({dur}*30),1.25)':d={int(dur*30)}:s={w}x{h}:fps=30,"
              f"subtitles=filename='{str(ass).replace(':', chr(92)+':')}'")
        media.run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c={colour}:s={w}x{h}:r=30:d={dur}",
            "-f", "lavfi", "-i", f"sine=frequency={330+idx*40}:sample_rate=48000:d={dur}",
            "-filter_complex", f"[0:v]{vf}[v];[1:a]volume=0.25,afade=t=in:d=0.3,afade=t=out:st={max(0,dur-0.4)}:d=0.4[a]",
            "-map", "[v]", "-map", "[a]", "-t", str(dur),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", str(out_path)], timeout=600)
        out = EngineOutput(notes="SIMULATION")
        out.add(out_path, "video", "video/mp4", engine=self.info.name, simulated=True)
        ctx.log("Plaque de test générée (simulation étiquetée)", progress=1.0, stage="done")
        return out

    def _audio(self, request: EngineRequest, ctx) -> EngineOutput:
        text = str(request.params.get("text") or request.shot.get("dialogue") or "")
        dur = max(1.0, min(0.45 * max(1, len(text.split())), 60.0)) if text else 3.0
        out_path = request.out("voice_simulation.wav")
        media.run_ffmpeg(["-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=48000:d={dur}",
                          "-af", "volume=0.3", "-c:a", "pcm_s16le", str(out_path)], timeout=120)
        out = EngineOutput(notes="SIMULATION — tonalité, pas une voix")
        out.add(out_path, "audio", "audio/wav", engine=self.info.name, simulated=True)
        return out
