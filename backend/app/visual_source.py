import json
import re
import statistics
import subprocess
import sys
import tempfile
import shutil
import csv
import io
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import media


def youtube_url(value):
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        raise ValueError("URL YouTube HTTPS requise")
    host = parsed.hostname
    if host == "youtu.be":
        video_id = parsed.path.strip("/")
    elif host in {"www.youtube.com", "youtube.com", "m.youtube.com"} and parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    else:
        raise ValueError("URL vidéo YouTube requise")
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Identifiant vidéo invalide")
    return f"https://www.youtube.com/watch?v={video_id}"


def caption_segments(data):
    segments = []
    for event in data.get("events", []):
        text = "".join(part.get("utf8", "") for part in event.get("segs", [])).strip()
        if text:
            segments.append({"start_s": event["tStartMs"] / 1000,
                "duration_s": event.get("dDurationMs", 0) / 1000, "text": text})
    return segments


def scene_cuts(path):
    process = subprocess.run([media.ffmpeg_bin(), "-hide_banner", "-i", str(path),
        "-vf", "scale=320:-2,select='gt(scene,0.28)',showinfo", "-an", "-f", "null", "-"],
        capture_output=True, text=True, timeout=300)
    if process.returncode:
        raise media.MediaError(process.stderr[-1000:])
    return [float(t) for t in re.findall(r"pts_time:([0-9.]+)", process.stderr)]


def visual_types(path, work, duration):
    if not shutil.which("tesseract"):
        return {"status": "unavailable", "reason": "Optional CPU OCR tesseract not installed"}
    samples = []
    for i in range(8):
        timestamp = round(duration * (i + 0.5) / 8, 2)
        thumbnail = work / f"analysis_{i}.png"
        media.run_ffmpeg(["-ss", str(timestamp), "-i", str(path), "-frames:v", "1",
                          "-vf", "scale=1280:-2", str(thumbnail)])
        process = subprocess.run(["tesseract", str(thumbnail), "stdout", "--psm", "11", "tsv"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        if process.returncode:
            raise media.MediaError("OCR failed: " + process.stderr[-500:])
        rows = csv.DictReader(io.StringIO(process.stdout), delimiter="\t")
        words = [r for r in rows if r.get("text", "").strip() and float(r.get("conf", -1)) >= 60]
        kind = "text_dense_interface_or_diagram" if len(words) >= 25 else "text_card_or_sparse_visual" if len(words) >= 8 else "sparse_visual"
        samples.append({"time_s": timestamp, "type_inferred": kind, "recognized_word_count": len(words)})
    return {"status": "heuristic", "samples": samples,
        "method": "8 temporal samples, CPU OCR word density; no semantic vision model",
        "limitations": "Cannot reliably distinguish UI/diagram or presenter/B-roll; cuts between samples may be missed"}


def analyze_url(url, out_dir):
    url = youtube_url(url)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"url": url, "status": "unavailable", "source_media_reused": False,
        "transcript": {"status": "unavailable"}, "rhythm": {"status": "unavailable"},
        "visual_types": {"status": "not_automatically_classified",
            "reason": "CPU scene cuts do not establish semantic visual types"}}
    # Source media is quarantined in a temporary directory and never enters the renderer.
    with tempfile.TemporaryDirectory(prefix="ugcv2-reference-") as temporary:
        work = Path(temporary)
        args = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--socket-timeout", "15",
                "--retries", "0", "--skip-download", "--write-info-json", "--write-subs",
                "--write-auto-subs", "--sub-langs", "en", "--sub-format", "json3",
                "-o", str(work / "source.%(ext)s"), url]
        try:
            process = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
            metadata_path = work / "source.info.json"
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                report.update({"status": "partial", "title": metadata.get("title"),
                    "duration_s": metadata.get("duration"), "chapters": metadata.get("chapters", [])})
            else:
                report["error"] = process.stderr[-3000:]
            captions = list(work.glob("*.json3"))
            if captions:
                segments = caption_segments(json.loads(captions[0].read_text(encoding="utf-8")))
                # Only analytical statistics travel into the public report, not the full transcript.
                text = " ".join(s["text"] for s in segments).lower()
                concepts = [word for word in ("trigger", "action", "workflow", "automation", "dropbox", "zapier", "chatgpt") if word in text]
                report["transcript"] = {"status": "analyzed", "segments": len(segments), "concepts": concepts,
                    "method": "keyword evidence, no semantic LLM inference"}
            # Keep bandwidth bounded: one low-resolution video, no original audio required.
            download = subprocess.run([sys.executable, "-m", "yt_dlp", "--no-playlist",
                "--socket-timeout", "15", "--retries", "0", "--max-filesize", "80M",
                "-f", "bestvideo[height<=360]/worstvideo", "-o", str(work / "reference.%(ext)s"), url],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
            videos = [p for p in work.glob("reference.*") if p.suffix in {".mp4", ".webm", ".mkv"}]
            if videos:
                info = media.probe(videos[0])
                cuts = scene_cuts(videos[0])
                bounds = [0, *cuts, info.duration_s]
                spans = [b - a for a, b in zip(bounds, bounds[1:]) if b > a]
                report["rhythm"] = {"status": "measured", "cut_times_s": cuts,
                    "mean_shot_s": round(statistics.mean(spans), 3),
                    "median_shot_s": round(statistics.median(spans), 3),
                    "method": "FFmpeg scene threshold 0.28 at 320px; misses subtle cuts"}
                report["visual_types"] = visual_types(videos[0], work, info.duration_s)
                report["status"] = "partial"
            elif download.returncode:
                report["visual_access_error"] = download.stderr[-1500:]
        except (subprocess.TimeoutExpired, media.MediaError) as exc:
            report["error"] = str(exc)
    media.write_json(out_dir / "source_analysis.json", report)
    return report
