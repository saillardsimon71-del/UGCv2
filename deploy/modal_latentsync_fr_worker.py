"""Isolated LatentSync v1.6 French lip-sync pilot on an EXISTING V2V clip.

No re-render of V2V. No modification of the previous face worker or video studio.
Pinned upstream implementation, localised lip generation conditioned on French WAV.
Checkpoint preparation on CPU, one L40S GPU test only after CPU readiness.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import modal

APP_NAME = "ugc-latentsync16-fr"
CHECKPOINTS = Path("/mnt/ugcv2_latentsync_fr/checkpoints")
HF_CACHE = "/mnt/ugcv2_latentsync_fr/hf"
LATENTSYNC_SHA = "a229c3948406bc2cf6eaf4873e662e70c6a04746"
app = modal.App(APP_NAME)
volume = modal.Volume.from_name("ugc-latentsync16-fr-models", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install(
        "git", "git-lfs", "ffmpeg", "curl", "build-essential", "cmake", "pkg-config",
        "libgl1", "libglib2.0-0", "libsm6", "libxext6", "libsndfile1",
    )
    .run_commands(
        "git clone https://github.com/bytedance/LatentSync.git /opt/LatentSync",
        f"cd /opt/LatentSync && git checkout --detach {LATENTSYNC_SHA}",
        "python -m pip install --no-cache-dir -r /opt/LatentSync/requirements.txt",
    )
    .env({"HF_HOME": HF_CACHE, "XDG_CACHE_HOME": "/mnt/ugcv2_latentsync_fr/cache"})
)


def readiness() -> dict:
    reqs = (
        CHECKPOINTS / "latentsync_unet.pt",
        CHECKPOINTS / "whisper" / "tiny.pt",
    )
    return {
        "checkpoints": {
            p.name: {"exists": p.is_file(), "bytes": p.stat().st_size if p.is_file() else 0}
            for p in reqs
        },
        "models_ok": all(p.is_file() and p.stat().st_size > 100_000 for p in reqs),
    }


@app.function(image=image, cpu=4, memory=16000, timeout=2400,
              min_containers=0, max_containers=1,
              volumes={"/mnt/ugcv2_latentsync_fr": volume})
def prepare() -> dict:
    """CPU-only checkpoint download. Never allocates a GPU."""
    from huggingface_hub import hf_hub_download, snapshot_download
    started = time.perf_counter()
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    for file in ("latentsync_unet.pt", "whisper/tiny.pt"):
        destination = CHECKPOINTS / file
        if not destination.is_file() or destination.stat().st_size < 100_000:
            hf_hub_download(
                repo_id="ByteDance/LatentSync-1.6",
                filename=file,
                local_dir=str(CHECKPOINTS),
            )
    # Avoid expensive surprise model download while GPU clock is running.
    snapshot_download(
        repo_id="stabilityai/sd-vae-ft-mse",
        allow_patterns=["config.json", "diffusion_pytorch_model.safetensors",
                        "diffusion_pytorch_model.bin"],
        local_files_only=False,
    )
    result = readiness()
    if not result["models_ok"]:
        raise RuntimeError("LatentSync 1.6 weights missing after CPU download")
    volume.commit()
    return {**result, "seconds": round(time.perf_counter() - started, 2),
            "gpu_seconds": 0, "upstream_sha": LATENTSYNC_SHA}


@app.function(image=image, gpu="L40S", cpu=8, memory=32768, timeout=1800,
              min_containers=0, max_containers=1,
              scaledown_window=2, volumes={"/mnt/ugcv2_latentsync_fr": volume})
def render_four_seconds(video_b64: str, audio_b64: str) -> dict:
    """One bounded 4-second native French lip-sync; accepts no arbitrary prompts."""
    if not readiness()["models_ok"]:
        raise RuntimeError("CPU checkpoint preparation required")
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ugcv2-latentsync16-") as folder:
        d = Path(folder)
        source = d / "source.mp4"
        speech = d / "voice.wav"
        output = d / "latentsync.mp4"
        source.write_bytes(base64.b64decode(video_b64, validate=True))
        speech.write_bytes(base64.b64decode(audio_b64, validate=True))
        if source.read_bytes()[4:8] != b"ftyp" or speech.read_bytes()[:4] != b"RIFF":
            raise ValueError("Expected V2V MP4 and PCM WAV")
        root = Path("/opt/LatentSync")
        ckpt = root / "checkpoints"
        if ckpt.is_symlink():
            ckpt.unlink()
        elif ckpt.exists():
            raise RuntimeError("Upstream checkpoints dir exists (refusing to mutate)")
        ckpt.symlink_to(CHECKPOINTS, target_is_directory=True)
        cmd = [
            "python", "-m", "scripts.inference",
            "--unet_config_path", "configs/unet/stage2_512.yaml",
            "--inference_ckpt_path", "checkpoints/latentsync_unet.pt",
            "--inference_steps", "25",
            "--guidance_scale", "1.0",  # official guidance: more guidance may cause distortion
            "--seed", "20261029",
            "--video_path", str(source),
            "--audio_path", str(speech),
            "--video_out_path", str(output),
        ]
        proc = subprocess.run(cmd, cwd=str(root), text=True,
                              capture_output=True, timeout=1600)
        if proc.returncode != 0 or not output.is_file() or output.stat().st_size < 100_000:
            raise RuntimeError("LatentSync run failed: " + (proc.stdout + "\n" + proc.stderr)[-4000:])
        meta = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams",
             "-of", "json", str(output)],
            capture_output=True, text=True, check=True, timeout=50,
        )
        return {
            "video_base64": base64.b64encode(output.read_bytes()).decode(),
            "metadata": {
                "engine": "LatentSync-1.6", "upstream_sha": LATENTSYNC_SHA,
                "guidance_scale": 1.0, "steps": 25, "gpu": "L40S",
                "render_seconds": round(time.perf_counter() - start, 2),
                "video_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "ffprobe": json.loads(meta.stdout),
                "quality": "HUMAN_REVIEW_REQUIRED",
            },
        }
