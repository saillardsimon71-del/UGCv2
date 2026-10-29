"""UGCv2 — isolated TBDub Student v1.1 pilot on real US->FR V2V footage.

Upstream: https://github.com/TaoLiveAIGC/TBDub (Apache-2.0)
Pinned at 19e18e4ba8e2a19e6716cb38110ee2de1dae9bb3.
Do not change UGCv2 V2V, source face, original voice, or other Modal apps.
Prepare/checkpoint download and face preflight on CPU only. Run a SINGLE
4-second Student inference on L40S only after positive CPU checks.
All results are unreviewed until the user inspects the resulting MP4.
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

APP_NAME = "ugcv2-tbdub-student-fr-pilot"
UPSTREAM_SHA = "19e18e4ba8e2a19e6716cb38110ee2de1dae9bb3"
MODEL_ROOT = Path("/mnt/ugcv2_tbdub_models")
STUDENT_SHA256 = "4e86900f9744b3650bfe58451ae89b3afba758233a3edf5947516268c1ea11e6"
STUDENT_BYTES = 12591523048
LANDMARKER_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)
app = modal.App(APP_NAME)
model_vol = modal.Volume.from_name("ugc-tbdub-student-v11-models", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install(
        "git", "ffmpeg", "curl", "build-essential", "pkg-config",
        "libgl1", "libglib2.0-0", "libsm6", "libxext6", "libgomp1",
        "libsndfile1", "ca-certificates",
    )
    .run_commands(
        "git clone --depth 1 https://github.com/TaoLiveAIGC/TBDub.git /opt/TBDub",
        f"cd /opt/TBDub && git checkout --detach {UPSTREAM_SHA}",
        "python -m pip install --no-cache-dir torch==2.9.0 torchvision==0.24.0 --index-url https://download.pytorch.org/whl/cu128",
        "python -m pip install --no-cache-dir -r /opt/TBDub/requirements.txt",
    )
)


def _env() -> dict:
    """Set HuggingFace caches *after* volume mount, not during Modal build."""
    root = MODEL_ROOT
    (root / "hf").mkdir(parents=True, exist_ok=True)
    return {
        **os.environ,
        "HF_HOME": str(root / "hf"),
        "HF_HUB_ENABLE_HF_TRANSFER": "0",
        "OMP_NUM_THREADS": "4",
        "TOKENIZERS_PARALLELISM": "false",
        "PYTHONUNBUFFERED": "1",
    }


def _media_inputs(folder: Path, video_b64: str, audio_b64: str):
    video = folder / "v2v_original_4s.mp4"
    audio = folder / "voix_fr_4s.wav"
    video.write_bytes(base64.b64decode(video_b64, validate=True))
    audio.write_bytes(base64.b64decode(audio_b64, validate=True))
    if video.stat().st_size < 100_000 or video.read_bytes()[4:8] != b"ftyp":
        raise RuntimeError("Authentic source video missing/invalid")
    if audio.read_bytes()[:4] != b"RIFF":
        raise RuntimeError("Expected French 16-kHz WAV")
    return video, audio


def _run_inference(args: list[str], timeout: int, *, directory: Path) -> tuple[str, str]:
    r = subprocess.run(
        ["python", "inference.py"] + args,
        cwd="/opt/TBDub",
        env=_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if r.returncode:
        raise RuntimeError(
            f"TBDub exited {r.returncode}:\n"
            + (r.stdout + "\n" + r.stderr)[-5000:]
        )
    return r.stdout[-5000:], r.stderr[-2000:]


def _exists_check() -> dict:
    path = MODEL_ROOT
    files = {
        "config": path / "config.json",
        "prompt": path / "null_prompt_emb.pt",
        "student": path / "tbdub_student.safetensors",
        "vae": path / "Wan2.2_VAE.safetensors",
        "hubert_config": path / "hubert-large-ll60k" / "config.json",
        "hubert_preprocessor": path / "hubert-large-ll60k" / "preprocessor_config.json",
        "hubert_weights": path / "hubert-large-ll60k" / "pytorch_model.bin",
        "landmarker": path / "face_landmarker.task",
    }
    return {
        "files": {
            k: {"present": p.is_file(), "size_bytes": p.stat().st_size if p.is_file() else 0}
            for k, p in files.items()
        },
        "all_present": all(p.is_file() and p.stat().st_size > 100 for p in files.values()),
        "student_expected_size": STUDENT_BYTES,
    }


def _landmarker() -> Path:
    import requests
    path = MODEL_ROOT / "face_landmarker.task"
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == LANDMARKER_SHA256:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(LANDMARKER_URL, timeout=120)
    response.raise_for_status()
    contents = response.content
    if hashlib.sha256(contents).hexdigest() != LANDMARKER_SHA256:
        raise RuntimeError("Face Landmarker checksum mismatch")
    path.write_bytes(contents)
    model_vol.commit()
    return path


@app.function(
    image=image, cpu=4, memory=16000, timeout=650,
    min_containers=0, max_containers=1,
    volumes={str(MODEL_ROOT): model_vol},
)
def preflight(video_b64: str, audio_b64: str) -> dict:
    """CPU only: inspect actual source face using *official* TBDub MediaPipe preprocessor."""
    _landmarker()
    with tempfile.TemporaryDirectory(prefix="tbdub-fr-preflight-") as temp:
        folder = Path(temp)
        video, audio = _media_inputs(folder, video_b64, audio_b64)
        output = folder / "preflight"
        output.mkdir()
        report = folder / "face_report.json"
        stdout, stderr = _run_inference(
            [
                "--video", str(video), "--audio", str(audio),
                "--inference-mode", "student",
                "--checkpoint-dir", str(MODEL_ROOT),
                "--preprocess-only",
                "--preprocess-report", str(report),
                "--output-dir", str(output),
                "--sample-name", "UGCv2_V2V_4s",
            ], timeout=510, directory=folder,
        )
        preview = output / "UGCv2_V2V_4s_crop.mp4"
        if not preview.is_file() or preview.stat().st_size < 10000:
            raise RuntimeError("No valid CPU face-detection preview")
        detected = json.loads(report.read_text()) if report.is_file() else {}
        return {
            "status": "CPU_FACE_PREFLIGHT_PASSED",
            "preview_base64": base64.b64encode(preview.read_bytes()).decode(),
            "face_report": detected,
            "log_tail": stdout[-1200:],
            "gpu_calls": 0,
        }


@app.function(
    image=image, cpu=4, memory=18000, timeout=5400,
    min_containers=0, max_containers=1,
    volumes={str(MODEL_ROOT): model_vol},
)
def prepare_student_only() -> dict:
    """CPU only: download *one* 12.59GB Student + shared weights (~15.27 GB total)."""
    from huggingface_hub import hf_hub_download
    start = time.perf_counter()
    _landmarker()
    os.environ.update({
        "HF_HOME": str(MODEL_ROOT / "hf"),
        "HF_HUB_ENABLE_HF_TRANSFER": "0",
    })
    specs = [
        ("TaoLiveAIGC/TBDub", "config.json", MODEL_ROOT),
        ("TaoLiveAIGC/TBDub", "null_prompt_emb.pt", MODEL_ROOT),
        ("TaoLiveAIGC/TBDub", "tbdub_student.safetensors", MODEL_ROOT),
        ("KlingTeam/X-Dub", "Wan2.2_VAE.safetensors", MODEL_ROOT),
        ("facebook/hubert-large-ll60k", "config.json", MODEL_ROOT / "hubert-large-ll60k"),
        ("facebook/hubert-large-ll60k", "preprocessor_config.json", MODEL_ROOT / "hubert-large-ll60k"),
        ("facebook/hubert-large-ll60k", "pytorch_model.bin", MODEL_ROOT / "hubert-large-ll60k"),
    ]
    for rid, filename, local_dir in specs:
        expected = local_dir / filename
        if expected.is_file() and expected.stat().st_size > 100:
            print(f"CACHE: {rid}/{filename} ({expected.stat().st_size} bytes)", flush=True)
            continue
        print(f"DOWNLOAD_CPU: {rid}/{filename}", flush=True)
        hf_hub_download(repo_id=rid, filename=filename, local_dir=str(local_dir), etag_timeout=60)
        if not expected.is_file() or expected.stat().st_size <= 100:
            raise RuntimeError(f"Incomplete checkpoint: {expected}")
        model_vol.commit()
        print(f"CACHED: {filename}, {expected.stat().st_size} bytes", flush=True)
    st = MODEL_ROOT / "tbdub_student.safetensors"
    if st.stat().st_size != STUDENT_BYTES:
        raise RuntimeError(f"Student checkpoint size mismatch ({st.stat().st_size} vs {STUDENT_BYTES})")
    state = _exists_check()
    if not state["all_present"]:
        raise RuntimeError(f"Checkpoints incomplete: {state}")
    model_vol.commit()
    return {
        "status": "STUDENT_WEIGHTS_READY",
        "model": "TBDub V1.1 Student",
        "upstream_sha": UPSTREAM_SHA,
        "seconds": round(time.perf_counter() - start, 2),
        "gpu_seconds": 0,
        **state,
    }


@app.function(
    image=image, gpu="L40S", cpu=8, memory=48000, timeout=2400,
    min_containers=0, max_containers=1, scaledown_window=2,
    volumes={str(MODEL_ROOT): model_vol},
)
def render_student_four_seconds(video_b64: str, audio_b64: str) -> dict:
    """Single Student pass with official paste-back. No fallback to wrong engines."""
    state = _exists_check()
    if not state["all_present"]:
        raise RuntimeError("No model: do CPU prepare first; GPU render forbidden")
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="tbdub-fr-gpu-") as temp:
        folder = Path(temp)
        video, audio = _media_inputs(folder, video_b64, audio_b64)
        output = folder / "result"
        output.mkdir()
        report = folder / "face_report.json"
        stdout, stderr = _run_inference(
            [
                "--video", str(video), "--audio", str(audio),
                "--inference-mode", "student",
                "--num-student-steps", "2",
                "--sigma-shift", "1.0",
                "--motion-from-latents",
                "--seed", "42",
                "--checkpoint-dir", str(MODEL_ROOT),
                "--preprocess-report", str(report),
                "--sample-name", "UGCv2_FR_tbdub_student_4s",
                "--output-dir", str(output),
                "--save-comparison",
            ], timeout=2260, directory=folder,
        )
        candidates = list(output.glob("*_tbdub.mp4"))
        if len(candidates) != 1 or candidates[0].stat().st_size < 100_000:
            raise RuntimeError(f"No unique TBDub video in {list(output.glob('*'))}")
        candidate = candidates[0]
        detail = json.loads(
            subprocess.check_output(
                ["ffprobe","-v","error","-show_entries",
                 "stream=codec_type,width,height,codec_name",
                 "-show_entries","format=duration,size",
                 "-of","json",str(candidate)],
                text=True, timeout=60,
            )
        )
        if not 3.5 < float(detail["format"]["duration"]) < 5.0:
            raise RuntimeError(f"Unexpected TBDub duration: {detail}")
        return {
            "video_base64": base64.b64encode(candidate.read_bytes()).decode(),
            "metadata": {
                "status": "MP4_GENERATED_NOT_HUMAN_VERIFIED",
                "engine": "TBDub v1.1 Student",
                "upstream_sha": UPSTREAM_SHA,
                "gpu": "L40S",
                "student_steps": 2,
                "wall_seconds": round(time.perf_counter()-start,2),
                "video_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                "media": detail,
                "preprocessing": json.loads(report.read_text()) if report.is_file() else {},
                "log_tail": stdout[-1700:],
            },
        }


@app.function(
    image=image, gpu="L40S", cpu=8, memory=48000, timeout=3000,
    min_containers=0, max_containers=1, scaledown_window=2,
    volumes={str(MODEL_ROOT): model_vol},
)
def render_student_french_twelve_to_fifteen_seconds(video_b64: str, audio_b64: str) -> dict:
    """Reuse validated TBDub Student weights and official paste-back for 12-15s."""
    state = _exists_check()
    if not state["all_present"]:
        raise RuntimeError("TBDub v1.1 Student checkpoint cache is absent")
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="tbdub-fr-v3-longer-") as temp:
        folder = Path(temp)
        video, audio = _media_inputs(folder, video_b64, audio_b64)
        output = folder / "rendered"
        output.mkdir()
        report = folder / "face_report.json"
        stdout, stderr = _run_inference(
            [
                "--video", str(video), "--audio", str(audio),
                "--inference-mode", "student",
                "--num-student-steps", "2",
                "--sigma-shift", "1.0", "--motion-from-latents",
                "--seed", "42", "--checkpoint-dir", str(MODEL_ROOT),
                "--preprocess-report", str(report),
                "--sample-name", "UGCv2_Chatterbox_V3_TBDub_15s",
                "--output-dir", str(output),
            ], timeout=2850, directory=folder,
        )
        produced = list(output.glob("*_tbdub.mp4"))
        if len(produced) != 1 or produced[0].stat().st_size < 100_000:
            raise RuntimeError(f"Expected one actual TBDub MP4, got {list(output.iterdir())}")
        file = produced[0]
        media = json.loads(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration,size:stream=codec_type,width,height",
             "-of", "json", str(file)], text=True, timeout=90))
        if not 11.0 <= float(media["format"]["duration"]) <= 15.3:
            raise RuntimeError(f"Invalid lip-sync duration: {media}")
        return {
            "video_base64": base64.b64encode(file.read_bytes()).decode(),
            "metadata": {
                "status": "ACTUAL_TBDUB_OUTPUT_HUMAN_REVIEW_REQUIRED",
                "engine": "TBDub Student v1.1",
                "upstream_sha": UPSTREAM_SHA,
                "gpu": "L40S", "student_steps": 2,
                "render_seconds": round(time.perf_counter() - start, 2),
                "video_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                "media": media,
                "face_report": json.loads(report.read_text()) if report.is_file() else {},
                "log_tail": stdout[-2000:],
            },
        }


@app.function(
    image=image, gpu="L40S", cpu=8, memory=48000, timeout=5100,
    min_containers=0, max_containers=1, scaledown_window=2,
    volumes={str(MODEL_ROOT): model_vol},
)
def dub_real_visible_face_shots(shots: list[dict]) -> dict:
    """One batched TBDub Student GPU call for identified full-frame face shots.

    Full 60-second UI/diagrams are NEVER passed through generative models.
    Input is a list of source-derived video clips and exactly time-aligned
    French WAVs. Short (1.44s) shot may fail gracefully and is marked as such.
    """
    if len(shots) != 4 or not _exists_check()["all_present"]:
        raise RuntimeError("Expected four genuine clips and cached TBDub V1.1 Student")
    start=time.perf_counter()
    result=[]
    for i,shot in enumerate(shots):
        name=str(shot.get("id",""))
        if name not in ("cam_a","cam_b","cam_c_short","cam_d"):
            raise RuntimeError(f"Unrecognized source-scene clip ID {name}")
        with tempfile.TemporaryDirectory(prefix=f"tbdub-fr60-{i}-") as tmp:
            folder=Path(tmp)
            video,audio=_media_inputs(folder,shot["video_base64"],shot["audio_base64"])
            output=folder/"result"
            output.mkdir()
            report=folder/"face_preflight.json"
            command=[
                "--video",str(video),"--audio",str(audio),
                "--inference-mode","student","--num-student-steps","2",
                "--sigma-shift","1.0","--motion-from-latents",
                "--seed","42","--checkpoint-dir",str(MODEL_ROOT),
                "--preprocess-report",str(report),
                "--sample-name",name,
                "--output-dir",str(output),
            ]
            print("TBDUB_60S_SHOT_BEGIN",name,flush=True)
            began=time.perf_counter()
            try:
                stdout,stderr=_run_inference(command,timeout=1200,directory=folder)
                finals=list(output.glob("*_tbdub.mp4"))
                if len(finals)!=1 or finals[0].stat().st_size<50000:
                    raise RuntimeError(f"No generated dubbed face MP4: {list(output.iterdir())}")
                file=finals[0]
                media=json.loads(subprocess.check_output(
                    ["ffprobe","-v","error","-show_entries",
                     "format=duration,size:stream=codec_type,width,height",
                     "-of","json",str(file)],text=True,timeout=60))
                rendered_seconds=float(media["format"]["duration"])
                intended=float(shot["duration_s"])
                if abs(rendered_seconds-intended)>0.60:
                    raise RuntimeError(
                        f"TBDub {name} wrong duration: {rendered_seconds} vs {intended}")
                result.append({
                    "id":name,"status":"real_tbdub_mp4",
                    "video_base64":base64.b64encode(file.read_bytes()).decode(),
                    "duration_s":rendered_seconds,
                    "sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
                    "wall_seconds":round(time.perf_counter()-began,2),
                    "source_start_s":shot["start_s"],
                    "source_end_s":shot["end_s"],
                    "media":media,
                    "face_report":json.loads(report.read_text()) if report.is_file() else {},
                    "log_tail":stdout[-1000:],
                })
                print("TBDUB_60S_SHOT_OK",name,round(rendered_seconds,2),flush=True)
            except BaseException as exc:
                if name!="cam_c_short":
                    raise RuntimeError(f"Required TBDub face shot failed [{name}]: {exc}") from exc
                # Official student might not support 1.44s. Never pretend to fix it:
                # mark precisely which tiny segment remains only face-swapped.
                result.append({
                    "id":name,"status":"short_shot_unsynced",
                    "source_start_s":shot["start_s"],
                    "source_end_s":shot["end_s"],
                    "error":str(exc)[-2200:],
                    "wall_seconds":round(time.perf_counter()-began,2),
                })
                print("TBDUB_60S_SHORT_SHOT_SKIPPED",name,str(exc)[-260:],flush=True)
    return {
        "engine":"TBDub Student v1.1",
        "source":"verified original 60s cut, per-clip face crop only",
        "screens_changed":False,
        "results":result,
        "gpu_wall_seconds":round(time.perf_counter()-start,2),
        "human_review_required":True,
    }
