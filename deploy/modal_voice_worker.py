"""UGCv2 — Voix sur Modal, app `ugc-voice`.

- render_tts : Chatterbox Multilingue V3 (Resemble AI) — texte -> voix clonée
  depuis une référence courte (~5 s), français inclus, contrôles
  exaggeration/cfg_weight. Parcours déjà validé dans le studio précédent.
- render_vc : Seed-VC — conversion de timbre zero-shot : l'utilisateur JOUE
  la scène (rythme, respirations, émotions réels), on ne change que le timbre.
  C'est souvent plus crédible qu'une synthèse, et c'est l'esprit du studio.
ÉTAT dans CE dépôt : non exécuté — première validation = écoute comparative
dans les benchmarks S4/S2 (la voix se juge à l'oreille, pas au code de retour).
"""
from __future__ import annotations

import base64
import os
import subprocess
import tempfile
import time
from pathlib import Path

import modal

APP_NAME = "ugc-voice"
GPU = os.getenv("UGC_MODAL_GPU_VOICE", "L4")
app = modal.App(APP_NAME)
vol = modal.Volume.from_name("ugc-voice-models", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libsndfile1")
    .run_commands(
        "pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124",
        "pip install chatterbox-tts",
        "git clone --depth 1 https://github.com/Plachtaa/seed-vc /opt/seed-vc",
        "cd /opt/seed-vc && pip install -r requirements.txt || pip install -r requirements-mac.txt || true",
    )
    .env({"HF_HOME": "/models/hf"})
)


@app.function(image=image, timeout=600, volumes={"/models": vol})
def doctor() -> dict:
    return {"app": APP_NAME, "hf_cache_gb": round(sum(
        f.stat().st_size for f in Path("/models").rglob("*") if f.is_file()) / 1e9, 2),
        "note": "Chatterbox/Seed-VC téléchargent leurs poids au premier appel dans le volume."}


@app.function(image=image, gpu=GPU, cpu=4, memory=16384, timeout=1800,
              min_containers=0, max_containers=1, scaledown_window=2,
              volumes={"/models": vol})
def render_tts(text: str, ref_audio_b64: str, params: dict) -> dict:
    t0 = time.perf_counter()
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    with tempfile.TemporaryDirectory(prefix="ugc-tts-") as tmp:
        d = Path(tmp)
        ref = None
        if ref_audio_b64:
            ref = d / "ref.wav"
            ref.write_bytes(base64.b64decode(ref_audio_b64, validate=True))
        model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
        wav = model.generate(text, language_id=str(params.get("language", "fr")),
                             audio_prompt_path=str(ref) if ref else None,
                             exaggeration=float(params.get("exaggeration", 0.5)),
                             cfg_weight=float(params.get("cfg_weight", 0.5)))
        out = d / "voice.wav"
        torchaudio.save(str(out), wav.cpu(), model.sr)
        vol.commit()
        return {"audio_b64": base64.b64encode(out.read_bytes()).decode(),
                "metadata": {"engine": "chatterbox_multilingual_v3", "gpu": GPU, "sr": model.sr,
                             "chars": len(text), "params": params,
                             "gpu_wall_seconds": round(time.perf_counter() - t0, 1)}}


@app.function(image=image, gpu=GPU, cpu=4, memory=16384, timeout=1800,
              min_containers=0, max_containers=1, scaledown_window=2,
              volumes={"/models": vol})
def render_vc(source_b64: str, ref_b64: str, params: dict) -> dict:
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ugc-vc-") as tmp:
        d = Path(tmp)
        (d / "source.wav").write_bytes(base64.b64decode(source_b64, validate=True))
        (d / "ref.wav").write_bytes(base64.b64decode(ref_b64, validate=True))
        cmd = ["python", "inference.py", "--source", str(d / "source.wav"),
               "--target", str(d / "ref.wav"), "--output", str(d / "out"),
               "--diffusion-steps", str(params.get("steps", 25)),
               "--length-adjust", "1.0", "--inference-cfg-rate", str(params.get("cfg", 0.7)),
               "--f0-condition", "False"]
        r = subprocess.run(cmd, cwd="/opt/seed-vc", capture_output=True, text=True, timeout=1700)
        found = sorted((d / "out").rglob("*.wav"), key=lambda p: p.stat().st_mtime) if (d / "out").exists() else []
        if r.returncode != 0 or not found:
            raise RuntimeError(f"Seed-VC a échoué :\n{(r.stdout + r.stderr)[-2000:]}")
        vol.commit()
        return {"audio_b64": base64.b64encode(found[-1].read_bytes()).decode(),
                "metadata": {"engine": "seed-vc", "gpu": GPU, "params": params,
                             "gpu_wall_seconds": round(time.perf_counter() - t0, 1)}}


@app.local_entrypoint()
def main(mode: str = "doctor"):
    if mode == "doctor":
        print(doctor.remote())
    else:
        raise SystemExit("Modes : doctor (0 GPU).")
