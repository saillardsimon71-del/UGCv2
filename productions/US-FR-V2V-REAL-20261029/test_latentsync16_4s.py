#!/usr/bin/env python3
"""4-second French lips pilot on existing approved V2V, LatentSync v1.6.
Inputs come exclusively from verified completed GitHub Actions artifact.
No source rerender. Fixed 4 seconds; hard gate before L40S GPU.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
OUT = Path("productions/US-FR-V2V-REAL-20261029/LATENTSYNC16_4S")
SOURCE_DIR = Path("productions/US-FR-V2V-REAL-20261029/EXISTING_V2V_8S")
START = 1.0
DURATION = 4.0
OUT.mkdir(parents=True, exist_ok=True)

def run(cmd, timeout=180):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout).stdout

def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams",
                           "-show_format", "-of", "json", str(path)]))
def video_duration(path):
    return float(probe(path)["format"]["duration"])
def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n",
                            encoding="utf-8")

def prepare():
    source = SOURCE_DIR / "baseline_french_8s.mp4"
    audio = SOURCE_DIR / "final_french_voice.wav"
    if not source.is_file() or not audio.is_file():
        raise RuntimeError("Missing existing GitHub artifact: MUST NOT regenerate V2V")
    if not 7.7 < video_duration(source) < 8.3 or not 7.7 < video_duration(audio) < 8.3:
        raise RuntimeError("Invalid 8-second baseline or French track")
    vid = OUT / "v2v_original_4s.mp4"
    wav = OUT / "fr_voice_4s_16k.wav"
    # LatentSync expects exactly 25 fps and 16-kHz speech.
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(START), "-i", str(source),
         "-t", str(DURATION), "-map", "0:v:0",
         "-vf", "fps=25,format=yuv420p", "-an",
         "-c:v", "libx264", "-crf", "18", "-preset", "fast",
         "-movflags", "+faststart", str(vid)])
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(START), "-i", str(audio),
         "-t", str(DURATION), "-ar", "16000", "-ac", "1",
         "-af", "apad,atrim=duration=4", "-c:a", "pcm_s16le", str(wav)])
    if abs(video_duration(vid)-4)>0.12 or abs(video_duration(wav)-4)>0.12:
        raise RuntimeError("Clip and speech timing mismatch")
    s = probe(vid)
    v = next(z for z in s["streams"] if z["codec_type"]=="video")
    if int(v["width"]) != 1344 or int(v["height"]) != 768:
        raise RuntimeError("Unexpected original video size")
    save("source_provenance.json",{
        "source_run": 40904419711,
        "source_artifact_name": "US-FR-LIPSYNC-8S-40904419711",
        "source_video_filename": "baseline_french_8s.mp4",
        "start_seconds": START,"duration_seconds": DURATION,
        "v2v_sha256": hashlib.sha256(vid.read_bytes()).hexdigest(),
        "fr_wav_sha256": hashlib.sha256(wav.read_bytes()).hexdigest(),
        "strict_source_only":True, "v2v_rerendered":False,
    })
    print("FOUR_SECOND_SOURCE_AND_FRENCH_AUDIO_VERIFIED",flush=True)

def render():
    import modal
    from deploy import modal_latentsync_fr_worker as worker
    vid = OUT/"v2v_original_4s.mp4"
    wav = OUT/"fr_voice_4s_16k.wav"
    if os.getenv("STUDIO_MODAL_WORKSPACE") != "lucj76861":
        raise RuntimeError("GPU blocked: wrong workspace")
    if os.getenv("CONFIRM_SINGLE_GPU") != "YES" or os.getenv("GITHUB_RUN_ATTEMPT","1") != "1":
        raise RuntimeError("GPU blocked: no confirmed single attempt")
    if not vid.is_file() or not wav.is_file() or not (OUT/"source_provenance.json").exists():
        raise RuntimeError("GPU blocked: source/audio validation absent")
    with worker.app.run(name="ugcv2-fr-latentsync-4s",environment_name="main"):
        try:
            prep=worker.prepare.remote()
            save("model_preparation.json",prep)
            print("LATENTSYNC_MODELS_READY",prep,flush=True)
        except BaseException as exc:
            save("render_status.json",{"status":"PREPARATION_FAILED_NO_GPU",
                "error":str(exc)[-2000:]})
            raise
        save("render_status.json",{"status":"GPU_CALL_STARTED",
            "models_prepared":True,"one_attempt_only":True})
        try:
            result=worker.render_four_seconds.remote(
                base64.b64encode(vid.read_bytes()).decode("ascii"),
                base64.b64encode(wav.read_bytes()).decode("ascii"))
            raw=OUT/"latentsync16_raw.mp4"
            raw.write_bytes(base64.b64decode(result["video_base64"],validate=True))
            save("gpu_metadata.json",result.get("metadata",{}))
        except BaseException as exc:
            save("render_status.json",{"status":"GPU_ATTEMPT_FAILED",
                "error":str(exc)[-4500:]})
            raise
    print("LATENTSYNC_RAW_VIDEO_READY",flush=True)

def finalize():
    raw = OUT/"latentsync16_raw.mp4"
    wav = OUT/"fr_voice_4s_16k.wav"
    if not raw.exists():
        raise RuntimeError("No actual LatentSync video exists")
    info=probe(raw)
    v=next((s for s in info["streams"] if s["codec_type"]=="video"),None)
    if v is None or not 3.5 < float(info["format"]["duration"]) < 4.6:
        raise RuntimeError("Invalid LatentSync 4-second output")
    final=OUT/"fr_latentsync16_4s.mp4"
    run(["ffmpeg","-y","-v","error","-i",str(raw),"-i",str(wav),
         "-map","0:v:0","-map","1:a:0",
         "-vf","fps=24,scale=1344:768:flags=lanczos",
         "-t","4","-c:v","libx264","-crf","18","-preset","fast",
         "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","48000",
         "-movflags","+faststart",str(final)],timeout=240)
    run(["ffmpeg","-v","error","-xerror","-i",str(final),
         "-f","null","-"],timeout=180)
    f=probe(final)
    streams={x["codec_type"] for x in f["streams"]}
    if "video" not in streams or "audio" not in streams:
        raise RuntimeError("Incomplete final MP4")
    base=OUT/"v2v_original_4s.mp4"
    compare=OUT/"compare_original_vs_latentsync16.mp4"
    run(["ffmpeg","-y","-v","error","-i",str(base),"-i",str(final),
         "-filter_complex",
         "[0:v]fps=24,scale=672:384,drawtext=text='AVANT (V2V)':x=10:y=15:fontsize=24:fontcolor=white[v0];"
         "[1:v]fps=24,scale=672:384,drawtext=text='APRES (LatentSync)':x=10:y=15:fontsize=24:fontcolor=white[v1];"
         "[v0][v1]hstack=inputs=2[v]",
         "-map","[v]","-map","1:a:0","-t","4",
         "-c:v","libx264","-crf","20","-pix_fmt","yuv420p",
         "-c:a","aac","-movflags","+faststart",str(compare)])
    for p in (base,final):
        run(["ffmpeg","-y","-v","error","-i",str(p),"-vf",
             "fps=1,scale=336:192,tile=2x2",
             "-frames:v","1",str(OUT/(p.stem+"_contact.jpg"))])
    save("render_status.json",{
        "status":"MP4_TECHNICALLY_RENDERED_HUMAN_REVIEW_REQUIRED",
        "final":str(final),"comparison":str(compare),
        "duration_seconds":float(f["format"]["duration"]),
        "final_sha256":hashlib.sha256(final.read_bytes()).hexdigest(),
        "no_v2v_regeneration":True,
        "human_visual_review":"MANDATORY: inspect facial anatomy and frame-to-frame transitions",
    })
    print("FINAL_FRENCH_LATENTSYNC16_MP4_AVAILABLE",final,flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=["prepare","render","finalize"])
    a=parser.parse_args()
    {"prepare":prepare,"render":render,"finalize":finalize}[a.stage]()
