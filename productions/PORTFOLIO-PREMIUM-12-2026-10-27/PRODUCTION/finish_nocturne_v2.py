import hashlib
import json
import re
import subprocess

from run_campaign import ROOT, command, now, probe, save

folder = ROOT / "01-dark-luxury"
source = folder / "EXPORTS/01-DARK-LUXURY-MASTER-1080x1920.mp4"
final = folder / "EXPORTS/01-DARK-LUXURY-V2-MASTER-1080x1920.mp4"
web = folder / "EXPORTS/01-DARK-LUXURY-V2-WEB-720x1280.mp4"
command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
         "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-af", "volume=-2.3dB",
         "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(final)])
command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(final),
         "-vf", "scale=720:1280:flags=lanczos", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(web)])
meter = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(final), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
if meter.returncode:
    raise RuntimeError(meter.stderr[-2000:])
lufs = float(re.findall(r"Integrated loudness:\s+I:\s+(-?[\d.]+) LUFS", meter.stderr)[-1])
peak = float(re.findall(r"True peak:\s+Peak:\s+(-?[\d.]+) dBFS", meter.stderr)[-1])
if abs(lufs + 16) > .5 or peak > -1.5:
    raise ValueError("Audio encore hors cible : " + str((lufs, peak)))
(folder / "REPORTS/AUDIO-METER-V2.txt").write_text("\n".join(line.rstrip() for line in meter.stderr[-1800:].splitlines()) + "\n", encoding="utf-8")
exports = []
for path, dimensions in ((final, (1080, 1920)), (web, (720, 1280))):
    info = probe(path)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
    assert (video["width"], video["height"]) == dimensions
    assert video["codec_name"] == "h264" and video["pix_fmt"] == "yuv420p" and video["nb_frames"] == "420"
    assert video["r_frame_rate"] == "24/1" and audio["codec_name"] == "aac" and audio["sample_rate"] == "48000" and audio["channels"] == 2
    assert abs(float(info["format"]["duration"]) - 17.5) < .1
    command(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"])
    exports.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "probe": info,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "full_decode": "pass"})
save(folder / "REPORTS/TECHNICAL_REPORT_V2.json", {"at": now(), "exports": exports, "duration_s": 17.5,
     "edit": "Original picture copied without re-encoding; mixed audio lowered by 2.3 dB on CPU. Original MP4 preserved. No new GPU call.",
     "audio_measured_lufs": lufs, "audio_true_peak_dbfs": peak, "critical_listening": "pending"})
plan_path = folder / "PRODUCTION_PLAN.json"
plan = json.loads(plan_path.read_text(encoding="utf-8"))
plan["output"]["master"] = str(final.relative_to(folder)).replace("\\", "/")
plan["output"]["web"] = str(web.relative_to(folder)).replace("\\", "/")
plan["final_edit_script"] = "PRODUCTION/finish_nocturne_v2.py"
save(plan_path, plan)
status_path = folder / "REPORTS/STATUS.json"
status = json.loads(status_path.read_text(encoding="utf-8"))
status.update(final_mp4=str(final.relative_to(ROOT)).replace("\\", "/"), duration_s=17.5, version="v2_cpu_audio_refinement")
save(status_path, status)
print(json.dumps({"real_v2_mp4": str(final), "lufs": lufs, "true_peak_dbfs": peak, "new_gpu_calls": 0}), flush=True)
