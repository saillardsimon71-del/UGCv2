import hashlib
import json
from pathlib import Path

from run_campaign import ROOT, command, now, probe, save

folder = ROOT / "02-golden-reveal"
prepared = folder / "REPORTS/EDIT"
work = folder / "REPORTS/EDIT-V2"
work.mkdir(exist_ok=True)
command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "2", "-i", str(prepared / "shot-03.mp4"), "-t", "3", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", str(work / "hero-warm-3s.mp4")])
paths = [prepared / "shot-01.mp4", prepared / "shot-02.mp4", work / "hero-warm-3s.mp4", prepared / "endcard.mp4"]
listing = work / "concat.txt"
listing.write_text("".join("file '" + p.resolve().as_posix() + "'\n" for p in paths), encoding="utf-8")
picture = work / "picture.mp4"
command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(picture)])
effects = work / "sound-design.wav"
command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(prepared / "sound-design.wav"), "-filter_complex", "[0:a]atrim=0:10.5,asetpts=PTS-STARTPTS[a];[0:a]atrim=12.5:17.5,asetpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=0:a=1[s]", "-map", "[s]", "-c:a", "pcm_s16le", str(effects)])
final = folder / "EXPORTS/02-GOLDEN-REVEAL-V2-MASTER-1080x1920.mp4"
web = folder / "EXPORTS/02-GOLDEN-REVEAL-V2-WEB-720x1280.mp4"
command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(picture), "-ss", "18", "-i", str(folder / "ASSETS/music.mp3"), "-i", str(effects),
         "-filter_complex", "[1:a]atrim=0:15.5,asetpts=PTS-STARTPTS,afade=t=in:d=0.15,afade=t=out:st=14.85:d=0.65,volume=0.8[m];[m][2:a]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9[a]",
         "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-t", "15.5", "-movflags", "+faststart", str(final)])
command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(final), "-vf", "scale=720:1280:flags=lanczos", "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(web)])
exports = []
for path, dimensions in ((final, (1080, 1920)), (web, (720, 1280))):
    info = probe(path)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
    assert (video["width"], video["height"]) == dimensions
    assert video["codec_name"] == "h264" and video["pix_fmt"] == "yuv420p" and video["nb_frames"] == "372"
    assert video["r_frame_rate"] == "24/1" and audio["sample_rate"] == "48000" and audio["channels"] == 2
    assert abs(float(info["format"]["duration"]) - 15.5) < .1
    command(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"])
    exports.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "probe": info,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "full_decode": "pass"})
save(folder / "REPORTS/TECHNICAL_REPORT_V2.json", {"at": now(), "duration_s": 15.5, "exports": exports,
     "edit": "Third real AI shot uses seconds 2 to 5 to avoid the cold lighting reset; the first two takes remain 5 seconds, original 2.5-second endcard. Original music remixed continuously and sound design re-timed. No additional GPU call.", "earlier_version_preserved": True, "quality": "human review required"})
command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(final), "-vf", "fps=2,scale=144:256,tile=8x4", "-frames:v", "1", str(folder / "REPORTS/FINAL-V2-CONTACT.jpg")])
plan_path = folder / "PRODUCTION_PLAN.json"
plan = json.loads(plan_path.read_text(encoding="utf-8"))
plan["target_duration_s"] = 15.5
plan["shots"][2]["timeline_duration_s"] = 3
plan["shots"][2]["source_in_s"] = 2
plan["shots"][2]["timeline_start_s"] = 10
plan["output"]["master"] = str(final.relative_to(folder)).replace("\\", "/")
plan["output"]["web"] = str(web.relative_to(folder)).replace("\\", "/")
plan["final_edit_script"] = "PRODUCTION/finish_golden_v2.py"
save(plan_path, plan)
status_path = folder / "REPORTS/STATUS.json"
status = json.loads(status_path.read_text(encoding="utf-8"))
status.update(final_mp4=str(final.relative_to(ROOT)).replace("\\", "/"), duration_s=15.5, version="v2_cpu_refinement",
              defects=["Mouvement du premier plan plus ample que prévu ; contraste lumineux du raccord final à valider.", "Rythme, stabilité des reflets et musique à juger en lecture continue."],
              recommendation="Présenter la V2 de 15,5 s pour validation ; conserver B avant visionnage et écoute critiques. Aucun nouvel essai GPU.")
save(status_path, status)
print("V2 réelle vérifiée : 15,5 s, 372 images, master et web, zéro nouveau GPU.", flush=True)
