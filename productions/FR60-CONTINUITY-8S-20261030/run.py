import argparse
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
REF = BASE.parent / "FR60-PRESENTER-PROOF-20261030"
SOURCE = ROOT.parent / "reference-hybrid/UGCv2_FR_60s_TBDub_HYBRID_TEST.mp4"
CACHE = BASE / "CACHE"
ASSETS = BASE / "ASSETS"
RENDERS = BASE / "RENDERS"
EXPECTED = {
    "ASSETS/presenter-studio.png": "bd5ce8b0b67fd7cae6f197fc4608e7dff8b78882c162aba54c9e177d6e37bea3",
    "CACHE/presenter-i2v.mp4": "8ed4ba8dd5822dfd33bd366699f87a75e7bc59a81fe60da2c833894f8fc47c1b",
    "CACHE/presenter-master.mp4": "a4395b9b9cf78e3de1dbca39db5b13fe970c1f1f955ca2b154723f6c4cae634b",
    "EXPORTS/Clip_A_gros_plan.mp4": "3bbe9bec2e127178d5b944602cfff6fc16536a635568e686537154a6f5e82ba2",
    "EXPORTS/Clip_B_PiP.mp4": "9636954842f8e37f10751320b565ed7f0f23c498f648641bdd9143a11357504f",
}
SOURCE_SHA = "346b8a25aa0722094f57e51aef3d41a97e1966f7ad1d04c4517c8fbbe5b7297d"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(args, timeout=240):
    return subprocess.run(list(map(str, args)), check=True, capture_output=True,
                          text=True, encoding="utf-8", timeout=timeout).stdout


def ffmpeg(*args):
    if Path(args[-1]).exists():
        raise FileExistsError(args[-1])
    run(["ffmpeg", "-nostdin", "-v", "error", "-n", *args])


def save(filename, value):
    (BASE / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]))


def protect_references():
    for filename, expected in EXPECTED.items():
        if sha(REF / filename) != expected:
            raise RuntimeError(f"Validated reference changed: {filename}")
    if sha(SOURCE) != SOURCE_SHA:
        raise RuntimeError("Validated French source changed")


def prepare():
    protect_references()
    if (BASE / "recipe.json").exists():
        raise RuntimeError("Already prepared")
    original = json.loads((REF / "animation.json").read_text())
    # Native frame 95 maps to the last retained 25fps frame of the approved master.
    ffmpeg("-i", REF / "CACHE/presenter-i2v.mp4", "-vf", "select=eq(n\\,95)",
           "-frames:v", 1, ASSETS / "anchor-native.png")
    for name, start, length, rate, channels in [
        ("new-speech16k.wav", 11.6, 4, 16000, 1),
        ("new-audio48k.wav", 11.6, 4, 48000, 2),
        ("continuous-audio48k.wav", 7.6, 8, 48000, 2),
    ]:
        ffmpeg("-ss", start, "-i", SOURCE, "-t", length, "-map", "0:a:0",
               "-ar", rate, "-ac", channels, "-c:a", "pcm_s16le", CACHE / name)
    ffmpeg("-ss", 11.6, "-i", SOURCE, "-t", 4, "-map", "0:v:0", "-an",
           "-c:v", "ffv1", CACHE / "original-next-4s.mkv")
    recipe = {
        "base_commit": "b7ac6e05fd7dbae5aa66b59e04aab089a156feec",
        "immutable_references": EXPECTED, "source_sha256": SOURCE_SHA,
        "original_photo": str((REF / "ASSETS/presenter-studio.png").relative_to(ROOT)),
        "new_initial_image": "ASSETS/anchor-native.png",
        "new_initial_image_sha256": sha(ASSETS / "anchor-native.png"),
        "controlled_change_trial_1": "initial frame only: approved native master frame 95 instead of original still",
        "unchanged_identity_reference": True, "duration_request_s": 4,
        "ltx_seed": original["metadata"]["seed"], "prompt": original["prompt"],
        "ltx_reference_metadata": original["metadata"],
        "ltx_image_strength": 1.0, "ltx_audio_mode": "silent", "ltx_aspect_argument": "16:9",
        "normalization": "fps=25,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
        "normalization_encoder": {"codec": "libx264", "crf": 16, "preset": "fast"},
        "tbdub": {"upstream": "19e18e4ba8e2a19e6716cb38110ee2de1dae9bb3", "mode": "student",
                  "steps": 2, "sigma_shift": 1.0, "motion_from_latents": True,
                  "seed": 42, "function": "render_student_four_seconds", "gpu": "L40S"},
        "audio": {"source_start_s": 11.6, "source_end_s": 15.6, "time_stretch": False,
                  "continuous_start_s": 7.6, "continuous_end_s": 15.6,
                  "new_speech_sha256": sha(CACHE / "new-speech16k.wav")},
        "timeline_new_take": [["full", 0, .4], ["title", .4, 2.64],
                              ["pip", 2.64, 3.96], ["domino", 3.96, 4]],
        "limits": {"ltx_generations": 2, "tbdub_generations": 2, "full_minute": False,
                   "new_models": False, "engine_modifications": False},
    }
    for path in ["deploy/modal_ltx_worker.py", "deploy/modal_tbdub_fr_worker.py"]:
        recipe.setdefault("worker_files_sha256", {})[path] = sha(ROOT / path)
    save("recipe.json", recipe)
    print("REFERENCES_LOCKED_AND_NEXT_FRENCH_PHRASE_PREPARED", flush=True)


def check_trial(stage, trial):
    protect_references()
    attempts = list(BASE.glob(f"{stage}-trial-*.json"))
    receipt = BASE / f"{stage}-trial-{trial}.json"
    if receipt.exists() or len(attempts) >= 2:
        raise RuntimeError(f"{stage}: existing attempt or hard limit of two attempts reached")
    recipe = json.loads((BASE / "recipe.json").read_text())
    for path, expected in recipe["worker_files_sha256"].items():
        if sha(ROOT / path) != expected:
            raise RuntimeError("Frozen engine code changed")
    import modal
    if modal.Workspace.from_context().hydrate().name != "lucj76861":
        raise RuntimeError("Wrong Modal workspace")
    return recipe


def animate(trial):
    import modal
    from deploy import modal_ltx_worker as ltx
    recipe = check_trial("ltx", trial)
    payload = {"prompt": recipe["prompt"], "duration_s": 4, "aspect_ratio": "16:9",
               "seed": recipe["ltx_seed"] + trial - 1, "audio_mode": "silent",
               "image_strength": 1.0, "image_png_base64": base64.b64encode((ASSETS / "anchor-native.png").read_bytes()).decode(),
               "trace_id": f"fr60-continuity-4s-trial-{trial}-20261030"}
    request = ltx.validate(payload)
    save(f"graph-trial-{trial}.json", ltx.build_graph(request, output_prefix=payload["trace_id"], uploaded_image="anchor-native.png"))
    receipt_name = f"ltx-trial-{trial}.json"
    save(receipt_name, {"status": "started", "seed": payload["seed"], "duration_s": 4})
    with ltx.app.run(name=f"ugcv2-continuity-ltx-4s-trial-{trial}", environment_name="main"):
        call = ltx.render_clip.spawn(payload)
        save(receipt_name, {"status": "running", "call_id": call.object_id, "seed": payload["seed"], "duration_s": 4})
        try:
            result = call.get(timeout=900)
        except BaseException:
            call.cancel(terminate_containers=True)
            raise
    raw = CACHE / f"trial-{trial}-before-raw.mp4"
    raw.write_bytes(base64.b64decode(result["video_base64"], validate=True))
    save(receipt_name, {"status": "rendered", "seed": payload["seed"], "raw_sha256": sha(raw), "metadata": result["metadata"]})
    ffmpeg("-i", raw, "-vf", recipe["normalization"], "-t", 4, "-an", "-c:v", "libx264",
           "-crf", 16, "-preset", "fast", CACHE / f"trial-{trial}-before.mp4")
    print("NEW_FOUR_SECOND_LTX_TAKE_READY", trial, flush=True)


def dub(trial):
    from deploy import modal_tbdub_fr_worker as tbdub
    check_trial("tbdub", trial)
    receipt_name = f"tbdub-trial-{trial}.json"
    before = CACHE / f"trial-{trial}-before.mp4"
    encoded = base64.b64encode(before.read_bytes()).decode()
    audio = base64.b64encode((CACHE / "new-speech16k.wav").read_bytes()).decode()
    with tbdub.app.run(name=f"ugcv2-continuity-tbdub-4s-trial-{trial}", environment_name="main"):
        preflight = tbdub.preflight.remote(encoded, audio)
        if preflight["status"] != "CPU_FACE_PREFLIGHT_PASSED":
            raise RuntimeError("Face preflight failed")
        (CACHE / f"trial-{trial}-face-preview.mp4").write_bytes(base64.b64decode(preflight.pop("preview_base64")))
        save(f"preflight-trial-{trial}.json", preflight)
        save(receipt_name, {"status": "started", "before_sha256": sha(before)})
        call = tbdub.render_student_four_seconds.spawn(encoded, audio)
        try:
            result = call.get(timeout=600)
        except BaseException:
            call.cancel(terminate_containers=True)
            raise
    after = CACHE / f"trial-{trial}-after.mp4"
    after.write_bytes(base64.b64decode(result["video_base64"], validate=True))
    if sha(after) != result["metadata"]["video_sha256"]:
        raise RuntimeError("TBDub checksum mismatch")
    save(receipt_name, {"before_sha256": sha(before), **result["metadata"]})
    print("NEW_FOUR_SECOND_TBDUB_TAKE_READY", trial, flush=True)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    for folder in [CACHE, ASSETS, RENDERS]:
        folder.mkdir(parents=True, exist_ok=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "animate", "dub"])
    parser.add_argument("--trial", type=int, choices=[1, 2], default=1)
    args = parser.parse_args()
    if args.stage == "prepare":
        prepare()
    else:
        {"animate": animate, "dub": dub}[args.stage](args.trial)
