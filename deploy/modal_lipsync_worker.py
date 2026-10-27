"""UGCv2 — Synchronisation labiale sur Modal, app `ugc-lipsync`.

Deux moteurs, un contrat :
- LatentSync 1.6 (ByteDance, diffusion 512 px) = qualité production.
- MuseTalk 1.5 (Tencent, inpainting 1 pas) = brouillon rapide pour valider
  le texte/rythme avant la passe coûteuse.
ÉTAT : écrits d'après les README officiels, NON ENCORE EXÉCUTÉS sur GPU.
Première exécution = benchmark S2 (même vidéo, même audio, comparaison A/B).

  modal deploy deploy/modal_lipsync_worker.py
  modal run deploy/modal_lipsync_worker.py --mode doctor    # 0 GPU
  modal run deploy/modal_lipsync_worker.py --mode prepare   # télécharge les poids (CPU, long)
"""
from __future__ import annotations

import base64
import os
import subprocess
import tempfile
import time
from pathlib import Path

import modal

APP_NAME = "ugc-lipsync"
GPU = os.getenv("UGC_MODAL_GPU_LIPSYNC", "A10G")   # LatentSync 1.6 ≈ 18 Go VRAM
app = modal.App(APP_NAME)
vol = modal.Volume.from_name("ugc-lipsync-models", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0", "libsndfile1")
    .run_commands(
        "pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124",
        "git clone --depth 1 https://github.com/bytedance/LatentSync /opt/LatentSync",
        "cd /opt/LatentSync && pip install -r requirements.txt",
        "git clone --depth 1 https://github.com/TMElyralab/MuseTalk /opt/MuseTalk",
        "cd /opt/MuseTalk && pip install -r requirements.txt || true",
        "pip install huggingface_hub",
    )
)


def _ready(model: str) -> bool:
    base = Path("/models")
    if model == "latentsync16":
        return (base / "latentsync" / "latentsync_unet.pt").exists()
    return (base / "musetalk" / "musetalkV15" / "unet.pth").exists()


@app.function(image=image, timeout=900, volumes={"/models": vol})
def doctor() -> dict:
    return {"app": APP_NAME, "latentsync16_ready": _ready("latentsync16"),
            "musetalk15_ready": _ready("musetalk15"),
            "note": "prepare télécharge les poids dans le volume (LatentSync ~10 Go, MuseTalk ~4 Go)."}


@app.function(image=image, timeout=7200, volumes={"/models": vol})
def prepare() -> dict:
    """Téléchargement des poids dans le volume (CPU, aucun GPU facturé)."""
    cmds = [
        "hf download ByteDance/LatentSync-1.6 --local-dir /models/latentsync_raw || huggingface-cli download ByteDance/LatentSync-1.6 --local-dir /models/latentsync_raw",
        "mkdir -p /models/latentsync && find /models/latentsync_raw -name 'latentsync_unet.pt' -exec cp {} /models/latentsync/ \\;",
        "cd /opt/MuseTalk && (bash download_weights.sh || true)",
        "mkdir -p /models/musetalk && cp -r /opt/MuseTalk/models/* /models/musetalk/ 2>/dev/null || true",
    ]
    logs = []
    for c in cmds:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=7000)
        logs.append((r.stdout + r.stderr)[-300:])
    vol.commit()
    return {**doctor.local(), "logs_tail": logs}


@app.function(image=image, gpu=GPU, cpu=8, memory=32768, timeout=3600,
              min_containers=0, max_containers=1, scaledown_window=2,
              volumes={"/models": vol})
def render_lipsync(video_b64: str, audio_b64: str, params: dict) -> dict:
    model = str(params.get("model", "latentsync16"))
    if not _ready(model):
        raise RuntimeError(f"Poids {model} absents : lancer d'abord --mode prepare")
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ugc-lipsync-") as tmp:
        d = Path(tmp)
        (d / "in.mp4").write_bytes(base64.b64decode(video_b64, validate=True))
        (d / "in.wav").write_bytes(base64.b64decode(audio_b64, validate=True))
        out = d / "out.mp4"
        if model == "latentsync16":
            # Checkpoints attendus par le dépôt dans ./checkpoints : liens vers le volume
            subprocess.run("ln -sfn /models/latentsync /opt/LatentSync/checkpoints", shell=True, check=True)
            cfg = "configs/unet/stage2_512.yaml"
            cmd = ["python", "-m", "scripts.inference", "--unet_config_path", cfg,
                   "--inference_ckpt_path", "checkpoints/latentsync_unet.pt",
                   "--inference_steps", str(params.get("steps", 20)),
                   "--guidance_scale", str(params.get("guidance_scale", 1.5)),
                   "--video_path", str(d / "in.mp4"), "--audio_path", str(d / "in.wav"),
                   "--video_out_path", str(out)]
            r = subprocess.run(cmd, cwd="/opt/LatentSync", capture_output=True, text=True, timeout=3400)
        else:
            subprocess.run("mkdir -p /opt/MuseTalk/models && cp -rn /models/musetalk/* /opt/MuseTalk/models/ || true",
                           shell=True)
            cfg_yaml = d / "task.yaml"
            cfg_yaml.write_text(f"task_0:\n  video_path: \"{d / 'in.mp4'}\"\n  audio_path: \"{d / 'in.wav'}\"\n")
            cmd = ["python", "-m", "scripts.inference", "--inference_config", str(cfg_yaml),
                   "--unet_model_path", "models/musetalkV15/unet.pth",
                   "--unet_config", "models/musetalkV15/musetalk.json",
                   "--version", "v15", "--result_dir", str(d / "res")]
            r = subprocess.run(cmd, cwd="/opt/MuseTalk", capture_output=True, text=True, timeout=3400)
            found = sorted((d / "res").rglob("*.mp4"), key=lambda p: p.stat().st_mtime)
            if found:
                found[-1].rename(out)
        if r.returncode != 0 or not out.is_file():
            raise RuntimeError(f"{model} a échoué :\n{(r.stdout + r.stderr)[-2000:]}")
        return {"video_b64": base64.b64encode(out.read_bytes()).decode(),
                "metadata": {"engine": model, "gpu": GPU, "params": params,
                             "gpu_wall_seconds": round(time.perf_counter() - t0, 1),
                             "bytes": out.stat().st_size}}


@app.local_entrypoint()
def main(mode: str = "doctor"):
    if mode == "doctor":
        print(doctor.remote())
    elif mode == "prepare":
        print(prepare.remote())
    else:
        raise SystemExit("Modes : doctor | prepare (0 GPU).")
