"""Analyse CPU d'une vidéo source — 100 % réel, sans GPU.

Produit : métadonnées (probe), vignettes temporelles (détecter les plans à
l'œil), loudness, segments noirs/figés, et un premier verdict « exploitable
pour la transformation ? ». C'est la première étape de toutes les recettes
partant d'une performance filmée : on regarde avant de transformer.
"""
from __future__ import annotations

from pathlib import Path

from .. import media
from .base import Engine, EngineInfo, EngineOutput, EngineRequest


class AnalysisEngine(Engine):
    info = EngineInfo(name="analysis", kind="analysis", label="Analyse vidéo (probe, vignettes, loudness)",
                      capabilities=["probe", "thumbnails", "loudness", "black_freeze"],
                      verified=True, maturity="production",
                      notes="CPU local, déterministe.")

    def run(self, request: EngineRequest, ctx) -> EngineOutput:
        src = Path(request.inputs.get("source_path") or request.params.get("source_path") or "")
        if not src.is_file():
            raise ValueError("Analyse : fichier source introuvable")
        info = media.probe(src)
        ctx.log(f"{info.width}x{info.height} · {info.duration_s:.1f}s · {info.fps}fps", progress=0.3, stage="probe")
        out = EngineOutput(diagnostics={"media": info.to_dict()})
        # Vignettes : jusqu'à 6 frames réparties
        thumbs = []
        if info.duration_s > 0 and info.width:
            n = 6
            for i in range(n):
                t = round(info.duration_s * (i + 0.5) / n, 2)
                thumb = request.out(f"thumb_{i:02d}.jpg")
                try:
                    media.run_ffmpeg(["-ss", str(t), "-i", str(src), "-frames:v", "1",
                                      "-vf", "scale=360:-2", str(thumb)])
                    thumbs.append(str(thumb))
                except Exception:
                    pass
        detected = media.detect_black_and_freeze(src) if info.width else {}
        loud = media.loudness(src) if info.has_audio else {}
        warnings = []
        if info.width and min(info.width, info.height) < 720:
            warnings.append(f"Résolution faible ({info.width}x{info.height}) : la transformation héritera de ce plafond.")
        if detected.get("freeze_segments"):
            warnings.append(f"{len(detected['freeze_segments'])} segment(s) figé(s) détecté(s).")
        if info.has_audio and loud.get("integrated_lufs") is not None and loud["integrated_lufs"] < -28:
            warnings.append("Audio très faible : prévoir une normalisation ou une nouvelle prise voix.")
        out.diagnostics.update({"black_freeze": detected, "loudness": loud, "warnings": warnings,
                                "thumbnails": thumbs})
        for t in thumbs:
            out.add(Path(t), "thumbnail", "image/jpeg")
        report = request.out("analysis.json")
        media.write_json(report, out.diagnostics)
        out.add(report, "report", "application/json")
        ctx.log("Analyse terminée" + (f" — {len(warnings)} avertissement(s)" if warnings else ""), progress=1.0, stage="done")
        return out
