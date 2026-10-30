#!/usr/bin/env python3
"""UGCv2: immutable Work-approved golden-master integrity gate (CPU-only).

This is a safety-first prerequisite to an autonomous long-video pipeline,
NOT a generator or a claim that all future scenes will match its quality.
Never uploads/distributes private reference audiovisual data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

GOLDEN_SHA = "586db7d3bff9dbc3e1a2c47e70d9ea47b107e10e78b5869eb67ab8a1f9b8be23"
GOLDEN_SECONDS = 6.52
GOLDEN_FRAMES = 163
GOLDEN_SIZE = (1920, 1080)
FPS = "25/1"
ASSETS = {
    "FR60-CONTINUITY-8S-20261030/ASSETS/anchor-native.png": "0cf4ba4de58f5f7b95b7c139026f801e8bdf01b665dac0988b4be0160b5df4e7",
    "FR60-CONTINUITY-8S-20261030/CACHE/trial-1-before-raw.mp4": "fc6460af2dfa82e5433442b215a0c611c0bbf33fa50eacb12ba9c0e911fb3084",
    "FR60-CONTINUITY-8S-20261030/CACHE/trial-1-before.mp4": "e520a95103069e57800581fa35a006b1c0c88cdc87a7d3fa9f7ffcd789cead27",
    "FR60-CONTINUITY-8S-20261030/CACHE/trial-1-after.mp4": "ee23222eab2521b1138a9aec6d547b1842e2f8d1f067009b23b8bf2956550fb3",
    "FR60-CONTINUITY-8S-20261030/CACHE/new-audio48k.wav": "253df73feb4418790a63a3a2af94e6893e8b410ed42f1f868dc6312bfd88e592",
    "FR60-CONTINUITY-8S-20261030/CACHE/continuous-audio48k.wav": "c85b7cebd7192c3884c9655f69b107fad3d982554d165ffe87a2b010a84b47fc",
}


def digest(file):
    h = hashlib.sha256()
    with Path(file).open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def digest_buffer(buf):
    return hashlib.sha256(buf).hexdigest()


def process(cmd, *, timeout=120):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout).stdout


def validate(zip_path: Path, video: Path) -> dict:
    if digest(video) != GOLDEN_SHA:
        raise ValueError("REFUSED: approved MP4 has changed. Never silently regenerate or replace it.")
    with zipfile.ZipFile(zip_path) as z:
        listed = set(z.namelist())
        unknown = set(ASSETS).difference(listed)
        if unknown:
            raise ValueError("Missing approved Work source assets: " + str(sorted(unknown)))
        for name, required_sha in ASSETS.items():
            if digest_buffer(z.read(name)) != required_sha:
                raise ValueError("REFUSED: Work source differs from approved bytes: " + name)
    meta = json.loads(process(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)]))
    fmt = meta["format"]
    v = next((s for s in meta["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in meta["streams"] if s.get("codec_type") == "audio"), None)
    if not v or not a:
        raise ValueError("REFUSED: video or French audio track missing")
    if (v["width"], v["height"]) != GOLDEN_SIZE or v["r_frame_rate"] != FPS or int(v["nb_frames"]) != GOLDEN_FRAMES:
        raise ValueError("REFUSED: approved format changed")
    if abs(float(fmt["duration"]) - GOLDEN_SECONDS) > 0.02:
        raise ValueError("REFUSED: approved duration changed")
    if a["codec_name"] != "aac":
        raise ValueError("REFUSED: approved audio track changed")
    return {
        "state": "APPROVED_WORK_GOLDEN_LOCKED",
        "video_sha256": GOLDEN_SHA,
        "video_frames": GOLDEN_FRAMES,
        "duration_s": GOLDEN_SECONDS,
        "source_zip_sha256": digest(zip_path),
        "verified_work_assets": len(ASSETS),
        "gpu_calls": 0,
        "generator_call": False,
        "future_generated_scenes_are_not_approved_automatically": True,
    }


def frame_hashes(video: Path, selector: str) -> list[str]:
    output = process(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(video),
                      "-map", selector, "-f", "framemd5", "-"], timeout=180)
    return [x.rsplit(",", 1)[1].strip() for x in output.splitlines() if x and not x.startswith("#")]


def replay(zip_path: Path, video: Path, target: Path) -> dict:
    result = validate(zip_path, video)
    if target.resolve() == video.resolve():
        raise ValueError("REFUSED: output may not overwrite approved input")
    if target.exists():
        raise FileExistsError("REFUSED: output already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        process(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-n", "-i", str(video),
                 "-map", "0", "-c", "copy", "-movflags", "+faststart", str(target)], timeout=120)
        for selector in ("0:v:0", "0:a:0"):
            if frame_hashes(video, selector) != frame_hashes(target, selector):
                raise RuntimeError("REFUSED: replay changed decoded content for " + selector)
        if len(frame_hashes(target, "0:v:0")) != GOLDEN_FRAMES:
            raise RuntimeError("REFUSED: replay lost frames")
        result.update({"replay_file": str(target), "replay_sha256": digest(target),
                       "video_packets_preserved": True,
                       "all_decoded_audio_video_frames_bit_identical": True,
                       "approved_input_unchanged": digest(video) == GOLDEN_SHA})
        return result
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description="CPU-only lock of Work-approved UGCv2 video")
    ap.add_argument("command", choices=["verify", "replay"])
    ap.add_argument("--work-zip", type=Path, required=True)
    ap.add_argument("--approved-mp4", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if args.command == "replay" and args.output is None:
        ap.error("replay requires --output")
    try:
        result = (validate(args.work_zip, args.approved_mp4) if args.command == "verify"
                  else replay(args.work_zip, args.approved_mp4, args.output))
    except (ValueError, RuntimeError, OSError, zipfile.BadZipFile, subprocess.CalledProcessError) as e:
        print("FAIL CLOSED: " + str(e), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
