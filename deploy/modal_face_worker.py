"""UGCv2 — Remplacement de visage sur Modal (FaceFusion), app `ugc-face`.

ÉTAT : écrit d'après la documentation officielle FaceFusion (headless-run),
NON ENCORE EXÉCUTÉ sur GPU. Première exécution = benchmark S1
(docs/BENCHMARKS.md). Ne pas considérer comme production avant revue à l'œil.

Choix : FaceFusion (détection + swap inswapper/simswap + restauration
GFPGAN/CodeFormer) conserve par construction expressions, regards, lumière et
gestuelle de la performance filmée — exactement la philosophie du studio.
Connu : résolution du swap 128–512 selon modèle → la passe d'enhancement est
obligatoire pour les gros plans. Licence des poids inswapper à vérifier avant
usage commercial (docs/LICENCES_A_VERIFIER.md).

Usage :
  modal deploy deploy/modal_face_worker.py
  modal run deploy/modal_face_worker.py --mode doctor     # 0 GPU
"""
from __future__ import annotations

import base64
import os
import subprocess
import tempfile
import time
from pathlib import Path

import modal

APP_NAME = "ugc-face"
GPU = os.getenv("UGC_MODAL_GPU_FACE", "A10G")
FACEFUSION_REF = os.getenv("FACEFUSION_REF", "3.5.1")  # épingler après validation S1
app = modal.App(APP_NAME)
models_vol = modal.Volume.from_name("ugc-face-models", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "curl", "ffmpeg", "libgl1", "libglib2.0-0")
    .run_commands(
        f"git clone --depth 1 --branch {FACEFUSION_REF} https://github.com/facefusion/facefusion /opt/facefusion",
        "cd /opt/facefusion && python install.py --onnxruntime cuda --skip-conda",
    )
)


def _probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-hide_banner", "-show_entries",
                          "stream=codec_type,width,height,duration", "-of", "csv", str(path)],
                         capture_output=True, text=True, timeout=120)
    return {"ffprobe": out.stdout.strip()[-500:], "bytes": path.stat().st_size}


@app.function(image=image, timeout=600, volumes={"/opt/facefusion/.assets/models": models_vol})
def doctor() -> dict:
    """0 GPU : vérifie l'installation et l'état du cache de modèles."""
    r = subprocess.run(["python", "facefusion.py", "--version"], cwd="/opt/facefusion",
                       capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise RuntimeError(f"Installation FaceFusion invalide : {(r.stdout + r.stderr)[-1000:]}")
    cache = Path("/opt/facefusion/.assets/models")
    return {"app": APP_NAME, "facefusion_version": (r.stdout or r.stderr).strip()[:200],
            "models_cached": sorted(p.name for p in cache.rglob("*.onnx"))[:20],
            "note": "Les modèles se téléchargent au premier rendu dans le volume ugc-face-models."}


@app.function(image=image, gpu=GPU, cpu=8, memory=32768, timeout=3600,
              min_containers=0, max_containers=1, scaledown_window=2,
              volumes={"/opt/facefusion/.assets/models": models_vol})
def render_faceswap(video_b64: str, face_b64: str, params: dict) -> dict:
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ugc-face-") as tmp:
        d = Path(tmp)
        (d / "target.mp4").write_bytes(base64.b64decode(video_b64, validate=True))
        (d / "face.jpg").write_bytes(base64.b64decode(face_b64, validate=True))
        out = d / "out.mp4"
        cmd = ["python", "facefusion.py", "headless-run",
               "--source-paths", str(d / "face.jpg"),
               "--target-path", str(d / "target.mp4"),
               "--output-path", str(out),
               "--processors", "face_swapper", "face_enhancer",
               "--face-swapper-model", str(params.get("swapper", "inswapper_128_fp16")),
               "--face-enhancer-model", str(params.get("enhancer", "gfpgan_1.4")),
               "--execution-providers", "cuda",
               "--output-video-encoder", "libx264", "--output-video-quality", "90",
               "--output-audio-encoder", "aac"]
        r = subprocess.run(cmd, cwd="/opt/facefusion",
                           capture_output=True, text=True, timeout=3400)
        if r.returncode != 0 or not out.is_file():
            raise RuntimeError(f"FaceFusion a échoué :\n{(r.stdout + r.stderr)[-2000:]}")
        models_vol.commit()
        return {"video_b64": base64.b64encode(out.read_bytes()).decode(),
                "metadata": {"engine": "facefusion", "gpu": GPU, "params": params,
                             "gpu_wall_seconds": round(time.perf_counter() - t0, 1), **_probe(out)}}


@app.local_entrypoint()
def main(mode: str = "doctor"):
    if mode == "doctor":
        print(doctor.remote())
    else:
        raise SystemExit("Modes : doctor (0 GPU). Les rendus passent par le studio ou le workflow benchmark.")


@app.function(image=image, gpu=GPU, cpu=8, memory=32768, timeout=1800,
              min_containers=0, max_containers=1, scaledown_window=2,
              volumes={"/opt/facefusion/.assets/models": models_vol})
def render_native_fr_lips(video_b64: str, french_audio_b64: str) -> dict:
    """Existing FaceFusion processor: replace ONLY lip motion to match FR audio.

    EDTalk 256 chosen instead of non-commercial Wav2Lip. The generated video
    must be visually approved; no claim of correct lip-sync without inspection.
    """
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ugc-fr-lips-") as tmp:
        d = Path(tmp)
        video = d / "v2v.mp4"
        audio = d / "voice_fr.wav"
        video.write_bytes(base64.b64decode(video_b64, validate=True))
        audio.write_bytes(base64.b64decode(french_audio_b64, validate=True))
        if not video.read_bytes()[4:8] == b"ftyp" or not audio.read_bytes()[:4] == b"RIFF":
            raise RuntimeError("Expected authentic V2V MP4 and PCM French WAV")
        output = d / "lips_fr.mp4"
        cmd = ["python", "facefusion.py", "headless-run",
               "--source-paths", str(audio), "--target-path", str(video),
               "--output-path", str(output), "--processors", "lip_syncer",
               "--lip-syncer-model", "edtalk_256", "--lip-syncer-weight", "0.75",
               "--execution-providers", "cuda", "--output-video-encoder", "libx264",
               "--output-video-quality", "90", "--output-audio-encoder", "aac"]
        run = subprocess.run(cmd,cwd="/opt/facefusion",capture_output=True,text=True,timeout=1650)
        if run.returncode or not output.is_file() or output.stat().st_size < 100000:
            raise RuntimeError("FaceFusion lip_syncer failed: "+(run.stdout+run.stderr)[-2500:])
        models_vol.commit()
        return {"video_b64":base64.b64encode(output.read_bytes()).decode(),
                "metadata":{"engine":"facefusion_edtalk_256","gpu":GPU,
                            "lip_syncer_weight":0.75,
                            "gpu_wall_seconds":round(time.perf_counter()-t0,2),
                            "bytes":output.stat().st_size}}
