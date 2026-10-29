import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import av
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app import media


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    directory = args.output.resolve()
    path = directory / "PILOTE_VISUAL_ENGINE_FR.mp4"
    metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
    info = media.probe(path)
    errors = []
    if any(scene["voice_duration_s"] > 0 for scene in metrics["scenes"]) and not info.has_audio:
        errors.append("missing_expected_voice")
    if (info.width, info.height, info.fps) != (1920, 1080, 30):
        errors.append("geometry_or_fps")
    if not 30 <= info.duration_s <= 60:
        errors.append("pilot_duration_outside_30_60s")
    frames, previous, bad_intervals = 0, None, 0
    with av.open(str(path)) as container:
        for frame in container.decode(video=0):
            timestamp = float(frame.pts * frame.time_base)
            if previous is not None and abs(timestamp - previous - 1 / 30) > 0.0001:
                bad_intervals += 1
            previous = timestamp
            frames += 1
    if bad_intervals or abs(frames - metrics["frames_expected"]) > 1:
        errors.append("frame_timing_or_count")
    detect = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(path),
        "-vf", "blackdetect=d=0.1:pix_th=0.05,freezedetect=n=-60dB:d=0.6", "-an", "-f", "null", "-"],
        capture_output=True, text=True, timeout=300)
    black_starts = [float(t) for t in re.findall(r"black_start:([0-9.]+)", detect.stderr)]
    freeze_starts = [float(t) for t in re.findall(r"freeze_start: ([0-9.]+)", detect.stderr)]
    if detect.returncode or black_starts:
        errors.append("black_or_detector_failure")
    synchronization = []
    sample_times = []
    for i, scene in enumerate(metrics["scenes"]):
        start = scene["start_s"]
        sample_times.append(round(start + min(3.5, scene["duration_s"] / 2), 3))
        voice_end = scene["voice_start_s"] + scene["voice_duration_s"]
        # The voice must finish before the next visual starts fading in.
        next_start = metrics["scenes"][i + 1]["start_s"] if i + 1 < len(metrics["scenes"]) else info.duration_s
        synchronization.append({"scene": scene["id"], "voice_end_s": round(start + voice_end, 3),
                                "next_transition_s": next_start,
                                "fits": start + voice_end <= next_start + 0.04})
        if not synchronization[-1]["fits"]:
            errors.append("voice_overlaps_transition")
        if i:
            sample_times.extend([round(start - 0.04, 3), round(start + 0.2, 3), round(start + 0.44, 3)])
    qc_dir = directory / "QC"
    qc_dir.mkdir(exist_ok=True)
    previews = []
    for i, timestamp in enumerate(sample_times):
        target = qc_dir / f"frame_{i:02d}_{timestamp:.2f}s.jpg"
        media.run_ffmpeg(["-ss", str(timestamp), "-i", str(path), "-frames:v", "1", "-q:v", "2", str(target)])
        previews.append((timestamp, target))
    sheet = Image.new("RGB", (1440, ((len(previews) + 2) // 3) * 300), "#101E25")
    draw = ImageDraw.Draw(sheet)
    for i, (timestamp, preview) in enumerate(previews):
        thumb = Image.open(preview)
        thumb.thumbnail((480, 270))
        x, y = (i % 3) * 480, (i // 3) * 300
        sheet.paste(thumb, (x, y))
        draw.text((x + 12, y + 275), f"{timestamp:.2f} s", fill="white")
    sheet.save(qc_dir / "contact_sheet.jpg", quality=92)
    loudness = media.loudness(path) if info.has_audio else None
    if loudness and not -16 <= loudness.get("integrated_lufs", -100) <= -12:
        errors.append("loudness_outside_target")
    report = {"status": "pass" if not errors else "fail", "errors": errors,
        "media": info.to_dict(), "decoded_frames": frames, "bad_frame_intervals": bad_intervals,
        "black_starts_s": black_starts, "freeze_starts_s": freeze_starts,
        "freeze_review": "Mostly static pedagogical panels can trigger this detector; review these intervals, not a decoding failure",
        "voice_timing": synchronization, "loudness": loudness,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "visual_inspection": "pending", "voice_listening": "pending",
        "source_reuse": "Renderer accepts no source media; original generated geometric illustrations only"}
    media.write_json(directory / "qc.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
