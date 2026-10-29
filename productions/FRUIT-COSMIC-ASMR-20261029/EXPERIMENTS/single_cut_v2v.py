#!/usr/bin/env python3
"""One-shot, real-motion V2V glass-cut experiment. No retries. Not a production-quality claim."""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO))
OUT = ROOT / "EXPERIMENTS" / "output"
SOURCE_PAGE = "https://www.pexels.com/video/slicing-a-fresh-strawberry-fruit-with-a-knife-4081319/"
# Pexels free-license source. Download is checked for playable real footage BEFORE any GPU call.
SOURCE_URL = "https://www.pexels.com/video/download/4081319/"
SFX_URL = "https://opengameart.org/sites/default/files/glass_breaking.wav"
SFX_PAGE = "https://opengameart.org/content/glass-break"  # Till Behrend, CC0.
PROMPT = (
    "A single continuous photoreal macro ASMR close-up of ONE strawberry being sliced "
    "straight through by one real chef knife. Precisely preserve the SOURCE VIDEO's knife "
    "trajectory, hand pose, timing of blade contact, mechanical resistance, exact object "
    "positions and physical separation of the two halves. Transform the strawberry into "
    "a lustrous OPAQUE deep midnight-blue glass jewel with a thin enamel-like crystal shell. "
    "Only where the steel blade breaks the shell, expose a bright tiny blue and violet "
    "spiral galaxy core INSIDE the freshly cut surface, NOT on the outside before cutting. "
    "Subtle cracks originate exactly from the knife edge; two distinct separated pieces "
    "remain on the board without transforming back. Minimal dark background, cinematic "
    "macro studio lighting, steady single camera shot. No jump cuts, no teleportation, "
    "no morphing into a new strawberry, no extra fruit, no duplicate knife, no text, "
    "no cartoon, no splashes, no artificial crystals flying everywhere."
)

def cmd(argv, timeout=120, capture=True):
    p = subprocess.run(argv, check=True, text=True, capture_output=capture, timeout=timeout)
    return p.stdout if capture else ""

def probe(path, count=False):
    args = ["ffprobe", "-v", "error"]
    if count:
        args += ["-count_frames"]
    args += ["-show_streams", "-show_format", "-of", "json", str(path)]
    return json.loads(cmd(args))

def video_stream(info):
    return next(s for s in info["streams"] if s["codec_type"] == "video")

def write(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def retrieve(url, target, limit=120_000_000):
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; video-production-proof/1.0)",
        "Referer": "https://www.pexels.com/" if "pexels.com" in url else "https://opengameart.org/",
    })
    with urllib.request.urlopen(request, timeout=35) as response, target.open("wb") as stream:
        total = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise ValueError("Source too large. No GPU requested.")
            stream.write(chunk)
    return total

def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    original = OUT / "pexels-original.mp4"
    try:
        size = retrieve(SOURCE_URL, original)
        if size < 100_000 or original.read_bytes()[4:8] != b"ftyp":
            raise ValueError("Pexels returned no valid MP4")
        info = probe(original)
        duration = float(info["format"]["duration"])
        if duration < 5.1:
            raise ValueError("Stock source shorter than 5.1s")
        # Optical variation peak gives a candidate time. It does NOT prove a correct cut.
        data = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(original), "-vf",
             "fps=3,scale=48:84,format=gray", "-f", "rawvideo", "-"],
            capture_output=True, check=True, timeout=150
        ).stdout
        frame_size = 48 * 84
        frames = [data[i:i+frame_size] for i in range(0, len(data), frame_size) if len(data[i:i+frame_size]) == frame_size]
        if len(frames) < 17:
            raise ValueError("Stock source has too few decoded frames")
        changes = [(sum(abs(a-b) for a, b in zip(frames[i], frames[i-1])) / frame_size, i / 3)
                   for i in range(1, len(frames))]
        eligible = [(v, t) for v, t in changes if 1.5 < t < duration - 1.5]
        if not eligible:
            raise ValueError("No usable action window")
        motion, t_peak = max(eligible)
        if motion < 2.0:
            raise ValueError("Insufficient source motion")
        start = max(0, min(duration - 5.1, t_peak - 2.15))
        source = OUT / "guide-real-slicing-121f.mp4"
        cmd(["ffmpeg", "-v", "error", "-y", "-ss", str(round(start,3)), "-i", str(original),
             "-vf", "fps=24,scale=768:1344:force_original_aspect_ratio=increase,"
                    "crop=768:1344,setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration=1",
             "-frames:v", "121", "-an", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "27", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(source)], timeout=180)
        result = probe(source, count=True)
        stream = video_stream(result)
        if (stream["width"], stream["height"], int(stream["nb_read_frames"])) != (768, 1344, 121):
            raise ValueError("V2V conditioning clip does not have 768x1344 121 frames")
        if source.stat().st_size > 23 * 1024 * 1024:
            raise ValueError("V2V clip exceeds 24MiB transport size")
        cmd(["ffmpeg", "-v", "error", "-y", "-i", str(source),
             "-vf", "fps=1,scale=192:336,tile=5x1", "-frames:v", "1",
             str(OUT / "guide-contact-sheet.jpg")])
        record = {"status": "guide_ready_not_artistically_approved", "license": "Pexels free license",
                  "source_page": SOURCE_PAGE, "source_download": SOURCE_URL,
                  "source_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                  "guide_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "guide_frames": 121, "guide_size": source.stat().st_size,
                  "source_duration_s": duration, "source_start_s": round(start,3),
                  "motion_peak_s": round(t_peak,3), "motion_peak_score": round(motion,2),
                  "possible_cut_s_in_guide": round(t_peak-start, 3),
                  "selection_warning": "Largest movement may NOT be the knife cutting. Human review required.",
                  "render_gpu_calls_allowed": 1, "publish": False}
        write("guide_report.json", record)
        return record
    except Exception as exc:
        write("guide_error.json", {"status":"blocked_before_gpu", "error":str(exc),
                                   "source_page":SOURCE_PAGE})
        raise

def render(confirm):
    if confirm != "oui" or os.getenv("GITHUB_RUN_ATTEMPT", "1") != "1":
        raise RuntimeError("One GPU request only, explicit approval and first run required")
    report = json.loads((OUT / "guide_report.json").read_text())
    source = OUT / "guide-real-slicing-121f.mp4"
    source_data = source.read_bytes()
    if hashlib.sha256(source_data).hexdigest() != report["guide_sha256"]:
        raise RuntimeError("Source changed. GPU blocked.")
    if (OUT / "v2v-raw-5s.mp4").exists() or (OUT / "render_receipt.json").exists():
        raise RuntimeError("Existing attempt. No repeat.")
    import modal
    from deploy import modal_ltx_worker as worker
    account = cmd([sys.executable, "-m", "modal", "token", "info"])
    match = re.search(r"^Workspace:\s+(\S+)", account, re.MULTILINE)
    if not match or match.group(1) != "lucj76861":
        raise RuntimeError("Wrong Modal workspace: GPU blocked.")
    # Deliberately execute the checkout V2V implementation: audit showed the older deployed
    # pvs-ltx ignores source video. Ephemeral app, never overwrite pvs-ltx.
    payload = {"prompt": PROMPT, "duration_s": 5, "aspect_ratio": "9:16",
               "seed": 2026102905, "audio_mode": "silent",
               "trace_id": "glasscut-motion-20261029",
               "video_mp4_base64": base64.b64encode(source_data).decode("ascii")}
    request = worker.validate(payload)
    worker.probe_source_video(source, request)
    graph = worker.build_graph(request, output_prefix="glasscut/test", uploaded_video="real-guide.mp4")
    if "3" not in graph or "30" not in graph or graph["30"]["class_type"] != "VAEEncodeTiled":
        raise RuntimeError("Source-guided V2V graph absent. No GPU.")
    receipt = {"status":"starting", "workspace":"lucj76861", "attempt":1,
               "guide_sha256": report["guide_sha256"], "worker":"checkout ephemeral V2V",
               "render_count_cap":1, "actual_billed_usd":None}
    write("render_receipt.json", receipt)
    call = None
    completed = False
    with worker.app.run(name="ugc-glass-cut-v2v-proof", environment_name="main"):
        try:
            call = worker.render_clip.spawn(payload)
            receipt.update(status="running", call_id=call.object_id)
            write("render_receipt.json", receipt)
            result = call.get(timeout=420)
            completed = True
        except BaseException as exc:
            receipt.update(status="failed", error_type=type(exc).__name__, error=str(exc)[:1500])
            raise
        finally:
            if call is not None and not completed:
                try:
                    call.cancel(terminate_containers=True)
                    receipt["cancellation_requested"] = True
                except Exception as error:
                    receipt["cancellation_error"] = str(error)
            write("render_receipt.json", receipt)
    raw = base64.b64decode(result["video_base64"], validate=True)
    target = OUT / "v2v-raw-5s.mp4"
    target.write_bytes(raw)
    metadata = result["metadata"]
    if metadata.get("continuity_mode") != "video" or \
       (metadata.get("source_video") or {}).get("sha256") != report["guide_sha256"]:
        receipt.update(status="reject_source_not_verified", metadata=metadata)
        write("render_receipt.json", receipt)
        raise RuntimeError("Video source conditioning not proven by metadata")
    rawprobe = probe(target, count=True)
    stream = video_stream(rawprobe)
    if abs(float(rawprobe["format"]["duration"]) - 121/24) > .2 or stream["width"] != 768 or stream["height"] != 1344:
        raise ValueError("Unexpected V2V video dimensions or length")
    cmd(["ffmpeg", "-v", "error", "-xerror", "-i", str(target), "-f", "null", "-"], timeout=120)
    receipt.update(status="real_video_technically_verified_human_visual_review_required",
                   raw_sha256=hashlib.sha256(raw).hexdigest(), metadata=metadata,
                   output_duration=float(rawprobe["format"]["duration"]),
                   aesthetic_result="NOT YET VERIFIED")
    write("render_receipt.json", receipt)
    return target

def finish():
    source = OUT / "v2v-raw-5s.mp4"
    if not source.is_file():
        raise RuntimeError("No verified real V2V MP4")
    if json.loads((OUT / "render_receipt.json").read_text())["status"] != "real_video_technically_verified_human_visual_review_required":
        raise RuntimeError("Render provenance incomplete")
    # Real CC0 sound (not fake math/noise). Unavailable audio is disclosed, not silently replaced.
    sfx = OUT / "glass_breaking_cc0.wav"
    try:
        if retrieve(SFX_URL, sfx, limit=5_000_000) < 2000:
            raise RuntimeError("Empty glass sample")
        audio = probe(sfx)
        if not any(s["codec_type"] == "audio" for s in audio["streams"]):
            raise RuntimeError("Invalid CC0 audio")
        report = json.loads((OUT / "guide_report.json").read_text())
        impact = max(.3, min(4.0, float(report["possible_cut_s_in_guide"])))
        delay = int(impact * 1000)
        target = OUT / "glass-cut-with-real-cc0-sfx-5s.mp4"
        cmd(["ffmpeg", "-v", "error", "-y", "-i", str(source), "-i", str(sfx),
             "-filter_complex", f"[1:a]volume=-9dB,adelay={delay}|{delay},apad,atrim=duration=5[a]",
             "-map", "0:v:0", "-map", "[a]", "-t", "5", "-c:v", "libx264",
             "-crf", "18", "-preset", "fast", "-vf", "scale=1080:1920:flags=lanczos",
             "-r", "24", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(target)],
            timeout=180)
        write("sfx_report.json", {"status":"cc0_real_recording_mixed",
              "source":SFX_PAGE,"author":"Till Behrend","license":"CC0",
              "approximate_impact_s":impact,"timing_warning":"Heuristic. Must listen and confirm frame-sync."})
    except Exception as err:
        write("sfx_report.json", {"status":"NO_VALID_SFX_RAW_VIDEO_ONLY","error":str(err),
                                   "source":SFX_PAGE})
    cmd(["ffmpeg", "-v", "error", "-y", "-i", str(source),
         "-vf", "fps=1,scale=192:336,tile=5x1", "-frames:v", "1",
         str(OUT / "result-contact-sheet.jpg")])
    print("Finished. One real V2V result for manual knife-cut quality review; never auto-publish.")

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=["prepare","render","finish"])
    p.add_argument("--confirm-spend",default="non")
    args=p.parse_args()
    {"prepare":prepare,"render":lambda:render(args.confirm_spend),"finish":finish}[args.stage]()
