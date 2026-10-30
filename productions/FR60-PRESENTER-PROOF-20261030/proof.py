import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
CACHE = BASE / "CACHE"
EXPORTS = BASE / "EXPORTS"
REF = BASE / "ASSETS" / "presenter-studio.png"
STARTS = {"A": 7.6, "B": 42.0}
DURATION = 4.0
SOURCE_SHA = "346b8a25aa0722094f57e51aef3d41a97e1966f7ad1d04c4517c8fbbe5b7297d"
PROMPT = (
    "A locked-off documentary tutorial camera shows the exact same fictional "
    "bald clean-shaven dark-skinned middle-aged man in the reference photograph, "
    "wearing the same blue shirt with a small lavalier microphone, in the exact "
    "same bright home office. He speaks naturally to the camera throughout, "
    "with small realistic mouth movements, subtle breathing and restrained "
    "head movements, one natural blink. Calm engaged tutorial delivery. "
    "His eyes remain open and directed into the lens. His head, shoulders, "
    "clothing, face shape, skin tone and age remain unchanged. The background, "
    "light, lens and camera framing stay perfectly stable. One continuous "
    "realistic shot, natural skin texture, clean clear mouth and eyes."
)


def run(args, timeout=240):
    return subprocess.run(args, check=True, capture_output=True, text=True,
                          encoding="utf-8", timeout=timeout).stdout


def sha(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def save(name, data):
    (BASE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams",
                           "-show_format", "-of", "json", str(path)]))


def ffmpeg(*args):
    destination = Path(args[-1])
    if destination.exists():
        raise FileExistsError(destination)
    run(["ffmpeg", "-nostdin", "-v", "error", "-n", *map(str, args)])


def prepare(source):
    if sha(source) != SOURCE_SHA:
        raise RuntimeError("Input differs from the validated hybrid reference")
    if not REF.is_file():
        raise FileNotFoundError(REF)
    for name, start in STARTS.items():
        ffmpeg("-ss", start, "-i", source, "-t", DURATION, "-map", "0:a:0",
               "-ar", 48000, "-ac", 2, "-c:a", "pcm_s16le", CACHE / f"{name}-audio.wav")
        ffmpeg("-i", CACHE / f"{name}-audio.wav", "-ar", 16000, "-ac", 1,
               "-c:a", "pcm_s16le", CACHE / f"{name}-speech16k.wav")
        ffmpeg("-ss", start, "-i", source, "-t", DURATION, "-map", "0:v:0",
               "-an", "-c:v", "ffv1", CACHE / f"{name}-original.mkv")
    save("provenance.json", {
        "reference_commit": "406e8d6fd27ba6fdd9c120b92ee2cb6154d09176",
        "reference_run": 40957764927, "reference_sha256": SOURCE_SHA,
        "presenter_reference_sha256": sha(REF), "duration_per_test_s": DURATION,
        "source_start_s": STARTS, "source_original_youtube_offset_s": 42,
        "audio_source": "decoded accepted hybrid AAC, no new voice synthesis or retiming",
        "pip_rectangle_xywh": [1428, 0, 492, 444],
        "identity_method": "one fictional photographic identity, one shared I2V master",
        "source_presenter_video_used_for_generation": False,
        "segmentation_used_for_background": False, "full_minute_rendered": False,
    })
    print("PREPARED_TWO_EXACT_FRENCH_EXCERPTS", flush=True)


def animate():
    import modal
    from deploy import modal_ltx_worker as ltx
    if modal.Workspace.from_context().hydrate().name != "lucj76861":
        raise RuntimeError("Unexpected Modal workspace")
    payload = {"prompt": PROMPT, "duration_s": DURATION, "aspect_ratio": "16:9",
               "seed": 2026103017, "audio_mode": "silent", "image_strength": 1.0,
               "image_png_base64": base64.b64encode(REF.read_bytes()).decode(),
               "trace_id": "fr60-new-presenter-proof-20261030"}
    ltx.validate(payload)
    receipt = BASE / "animation.json"
    if receipt.exists():
        raise RuntimeError("An animation attempt already exists; no automatic retry")
    save("animation.json", {"status": "started", "prompt": PROMPT})
    with ltx.app.run(name="ugcv2-fr60-identity-proof-4s", environment_name="main"):
        call = ltx.render_clip.spawn(payload)
        save("animation.json", {"status": "running", "call_id": call.object_id, "prompt": PROMPT})
        try:
            result = call.get(timeout=900)
        except BaseException:
            call.cancel(terminate_containers=True)
            raise
    if result["metadata"]["continuity_mode"] != "image":
        raise RuntimeError("The image reference was not used")
    raw = CACHE / "presenter-i2v.mp4"
    raw.write_bytes(base64.b64decode(result["video_base64"], validate=True))
    save("animation.json", {"status": "rendered_unreviewed", "prompt": PROMPT,
                            "sha256": sha(raw), "metadata": result["metadata"]})
    ffmpeg("-i", raw, "-vf", "fps=25,scale=1920:1080:force_original_aspect_ratio=increase,"
           "crop=1920:1080,setsar=1,format=yuv420p", "-t", DURATION, "-an",
           "-c:v", "libx264", "-crf", 16, "-preset", "fast", CACHE / "presenter-master.mp4")
    print("ONE_SHARED_PRESENTER_MASTER_READY", flush=True)


def lips():
    import modal
    from deploy import modal_tbdub_fr_worker as tbdub
    if modal.Workspace.from_context().hydrate().name != "lucj76861":
        raise RuntimeError("Unexpected Modal workspace")
    master = CACHE / "presenter-master.mp4"
    encoded = base64.b64encode(master.read_bytes()).decode()
    with tbdub.app.run(name="ugcv2-fr60-proof-two-tbdub-tests", environment_name="main"):
        for name in STARTS:
            if (BASE / f"lips-{name}.json").exists():
                raise RuntimeError(f"TBDub {name} attempt already exists; no automatic retry")
            audio = base64.b64encode((CACHE / f"{name}-speech16k.wav").read_bytes()).decode()
            check = tbdub.preflight.remote(encoded, audio)
            if check["status"] != "CPU_FACE_PREFLIGHT_PASSED":
                raise RuntimeError("TBDub face preflight failed")
            preview = check.pop("preview_base64")
            (CACHE / f"{name}-face-preflight.mp4").write_bytes(base64.b64decode(preview))
            save(f"preflight-{name}.json", check)
            save(f"lips-{name}.json", {"status": "started", "master_sha256": sha(master)})
            call = tbdub.render_student_four_seconds.spawn(encoded, audio)
            try:
                result = call.get(timeout=600)
            except BaseException:
                call.cancel(terminate_containers=True)
                raise
            output = CACHE / f"{name}-tbdub.mp4"
            output.write_bytes(base64.b64decode(result["video_base64"], validate=True))
            if sha(output) != result["metadata"]["video_sha256"]:
                raise RuntimeError("TBDub download checksum mismatch")
            save(f"lips-{name}.json", {"master_sha256": sha(master), **result["metadata"]})
            print(f"REAL_TBDUB_{name}_READY", flush=True)


def compose():
    common = ["-c:v", "libx264", "-crf", 17, "-preset", "fast", "-pix_fmt", "yuv420p"]
    for name in STARTS:
        raw = CACHE / f"{name}-tbdub.mp4"
        if abs(float(probe(raw)["format"]["duration"]) - DURATION) > .08:
            raise RuntimeError("TBDub duration mismatch; padding/retiming forbidden")
        ffmpeg("-i", raw, "-map", "0:v:0", "-an", "-vf", "fps=25,setsar=1",
               "-c:v", "ffv1", CACHE / f"{name}-actor.mkv")
        if name == "A":
            ffmpeg("-i", CACHE / "A-actor.mkv", "-i", CACHE / "A-audio.wav",
                   "-map", "0:v:0", "-map", "1:a:0", *common,
                   "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                   EXPORTS / "Clip_A_gros_plan.mp4")
        else:
            graph = ("[1:v]scale=492:444:force_original_aspect_ratio=increase,"
                     "crop=492:444,setsar=1[pip];"
                     "[0:v][pip]overlay=1428:0:eof_action=pass:repeatlast=0[v]")
            ffmpeg("-i", CACHE / "B-original.mkv", "-i", CACHE / "B-actor.mkv",
                   "-filter_complex", graph, "-map", "[v]", "-an",
                   "-c:v", "ffv1", CACHE / "B-composite-lossless.mkv")
            ffmpeg("-i", CACHE / "B-composite-lossless.mkv", "-i", CACHE / "B-audio.wav",
                   "-map", "0:v:0", "-map", "1:a:0", *common,
                   "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                   EXPORTS / "Clip_B_PiP.mp4")
    records = []
    for final in sorted(EXPORTS.glob("Clip_*.mp4")):
        run(["ffmpeg", "-v", "error", "-xerror", "-i", str(final), "-f", "null", "-"])
        media = probe(final)
        video = next(s for s in media["streams"] if s["codec_type"] == "video")
        audio = next(s for s in media["streams"] if s["codec_type"] == "audio")
        assert (video["width"], video["height"], video["r_frame_rate"]) == (1920, 1080, "25/1")
        assert abs(float(media["format"]["duration"]) - DURATION) < .05
        assert audio["sample_rate"] == "48000"
        records.append({"filename": final.name, "sha256": sha(final), "media": media})
    save("technical-verification.json", {"files": records, "full_decode": "passed",
                                        "visual_and_audible_review": "pending"})
    print("TWO_REAL_FOUR_SECOND_EXPORTS_READY", flush=True)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    CACHE.mkdir(parents=True, exist_ok=True)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "animate", "lips", "compose"])
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.stage == "prepare":
        if args.source is None:
            parser.error("prepare requires --source")
        prepare(args.source)
    else:
        {"animate": animate, "lips": lips, "compose": compose}[args.stage]()
