#!/usr/bin/env python3
"""True V2V US->FR dubbing with upstream TBDub Student; only four seconds.

Pure controller. Github Actions downloads the EXISTING V2V and final French WAV.
No YT re-download, no LTX rerender, no EDTalk or LatentSync, no publication.
Do not report quality success without actual MP4 and human visual review.
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
OUT = Path("productions/US-FR-V2V-REAL-20261029/TBDUB_4S_OUTPUT")
ORIGINAL = Path("productions/US-FR-V2V-REAL-20261029/EXISTING_V2V_8S")
T=4
START=1.0
OUT.mkdir(parents=True,exist_ok=True)


def sh(command: list[str], timeout=180) -> str:
    r=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    if r.returncode:
        raise RuntimeError("Command failed: "+" ".join(command[:5])+"\n"+(r.stdout+r.stderr)[-2400:])
    return r.stdout


def meta(p: Path) -> dict:
    return json.loads(sh(["ffprobe","-v","error","-show_streams","-show_format",
                          "-of","json",str(p)]))


def save(filename, value):
    (OUT/filename).write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",
                              encoding="utf-8")


def source():
    video=ORIGINAL/"baseline_french_8s.mp4"
    speech=ORIGINAL/"final_french_voice.wav"
    if not video.is_file() or not speech.is_file():
        raise RuntimeError("No authentic V2V+voice artifact from GitHub Actions 40904419711")
    d=float(meta(video)["format"]["duration"])
    wavd=float(meta(speech)["format"]["duration"])
    if not 7.7<d<8.3 or not 7.7<wavd<8.3:
        raise RuntimeError(f"Source must be authentic 8-second V2V, got {d} s and {wavd} s")
    vid=OUT/"v2v_original_4s.mp4"
    wav=OUT/"voix_fr_4s.wav"
    sh(["ffmpeg","-y","-v","error","-ss",str(START),"-i",str(video),
        "-t",str(T),"-map","0:v:0","-vf","fps=25,format=yuv420p",
        "-an","-c:v","libx264","-crf","18","-preset","fast",
        "-movflags","+faststart",str(vid)])
    sh(["ffmpeg","-y","-v","error","-ss",str(START),"-i",str(speech),
        "-t",str(T),"-af","apad,atrim=duration=4","-ar","16000",
        "-ac","1","-c:a","pcm_s16le",str(wav)])
    m=meta(vid)
    v=next(x for x in m["streams"] if x["codec_type"]=="video")
    if abs(float(m["format"]["duration"])-4)>0.15 or (v["width"],v["height"])!=(1344,768):
        raise RuntimeError(f"Original V2V clip mismatch: {m}")
    if abs(float(meta(wav)["format"]["duration"])-4)>0.15:
        raise RuntimeError("French driving WAV must be four seconds")
    report={
        "source_branch":"production/us-fr-lipsync-8s-20261029",
        "github_run":40904419711,
        "artifact":"US-FR-LIPSYNC-8S-40904419711",
        "source_file":"baseline_french_8s.mp4",
        "voice_file":"final_french_voice.wav",
        "source_time_range_s":[START,START+T],
        "input_video_sha256":hashlib.sha256(vid.read_bytes()).hexdigest(),
        "input_audio_sha256":hashlib.sha256(wav.read_bytes()).hexdigest(),
        "only_tbdub":True,
        "v2v_rerendered":False,
    }
    save("source_provenance.json",report)
    print("ORIGINAL_FRENCH_V2V_VALIDATED",json.dumps(report),flush=True)


def run():
    if os.environ.get("STUDIO_MODAL_WORKSPACE")!="lucj76861":
        raise RuntimeError("Wrong Modal workspace — aborting")
    if os.getenv("TBDUB_GPU_ALLOW_ONCE")!="YES" or os.getenv("GITHUB_RUN_ATTEMPT","1")!="1":
        raise RuntimeError("No authorized single TBDub test")
    video=OUT/"v2v_original_4s.mp4"
    wav=OUT/"voix_fr_4s.wav"
    if not video.is_file() or not wav.is_file() or not (OUT/"source_provenance.json").exists():
        raise RuntimeError("No validated inputs — GPU forbidden")
    from deploy import modal_tbdub_fr_worker as worker
    video_b64=base64.b64encode(video.read_bytes()).decode()
    audio_b64=base64.b64encode(wav.read_bytes()).decode()
    with worker.app.run(name="ugcv2-tbdub-fr-four-seconds",environment_name="main"):
        try:
            pilot=worker.preflight.remote(video_b64,audio_b64)
            if pilot.get("status")!="CPU_FACE_PREFLIGHT_PASSED":
                raise RuntimeError("TBDub MediaPipe face tracking not validated")
            preview=OUT/"tbdub_detected_face_crop_4s.mp4"
            preview.write_bytes(base64.b64decode(pilot.pop("preview_base64"),validate=True))
            save("tbdub_face_preflight.json",pilot)
            print("OFFICIAL_TBDUB_MEDIAPIPE_PREFLIGHT_PASSED",flush=True)
        except BaseException as exc:
            save("status.json",{"stage":"PREPROCESS_FAILED_NO_WEIGHTS_NO_GPU",
                                 "error":str(exc)[-3500:]})
            raise
        try:
            checkpoints=worker.prepare_student_only.remote()
            save("tbdub_cpu_checkpoints.json",checkpoints)
            print("OFFICIAL_STUDENT_WEIGHTS_PREPARED_CPU",flush=True)
        except BaseException as exc:
            save("status.json",{"stage":"CHECKPOINT_DOWNLOAD_FAILED_NO_GPU",
                                 "error":str(exc)[-3500:]})
            raise
        save("status.json",{"stage":"SINGLE_GPU_CALL_STARTED",
                            "model":"TBDub v1.1 Student",
                            "gpu":"L40S","no_v2v_rerender":True})
        try:
            result=worker.render_student_four_seconds.remote(video_b64,audio_b64)
            if result.get("metadata",{}).get("status")!="MP4_GENERATED_NOT_HUMAN_VERIFIED":
                raise RuntimeError("TBDub did not confirm a real MP4")
            raw=OUT/"tbdub_student_generated_4s.mp4"
            raw.write_bytes(base64.b64decode(result["video_base64"],validate=True))
            save("tbdub_gpu_metadata.json",result["metadata"])
            print("OFFICIAL_TBDUB_STUDENT_REAL_MP4_GENERATED",flush=True)
        except BaseException as exc:
            save("status.json",{"stage":"GPU_ATTEMPT_FAILED_NO_MP4",
                                 "error":str(exc)[-6000:]})
            raise


def finish():
    raw=OUT/"tbdub_student_generated_4s.mp4"
    voice=OUT/"voix_fr_4s.wav"
    if not raw.is_file():
        raise RuntimeError("TBDub generated video missing; do not claim final")
    details=meta(raw)
    v=next((x for x in details["streams"] if x["codec_type"]=="video"),None)
    if v is None or not 3.5<float(details["format"]["duration"])<5.0:
        raise RuntimeError(f"TBDub output invalid: {details}")
    final=OUT/"UGCv2_TBDUB_FR_4s_A_VERIFIER.mp4"
    sh(["ffmpeg","-y","-v","error","-i",str(raw),"-i",str(voice),
        "-map","0:v:0","-map","1:a:0","-t","4",
        "-vf","fps=25,scale=1344:768:flags=lanczos,format=yuv420p",
        "-c:v","libx264","-crf","18","-preset","fast",
        "-c:a","aac","-ar","48000","-b:a","192k",
        "-movflags","+faststart",str(final)],timeout=240)
    sh(["ffmpeg","-v","error","-xerror","-i",str(final),
        "-f","null","-"],timeout=180)
    f=meta(final)
    tracks={x["codec_type"] for x in f["streams"]}
    if not {"video","audio"}.issubset(tracks) or not 3.8<float(f["format"]["duration"])<4.3:
        raise RuntimeError("Final MP4 does not contain exactly four seconds of video+FR speech")
    original=OUT/"v2v_original_4s.mp4"
    compare=OUT/"UGCv2_TBDUB_FR_4s_AVANT_APRES.mp4"
    sh(["ffmpeg","-y","-v","error","-i",str(original),"-i",str(final),
        "-filter_complex",
        "[0:v]fps=25,scale=672:384[v0];[1:v]fps=25,scale=672:384[v1];"
        "[v0][v1]hstack=inputs=2[v]",
        "-map","[v]","-map","1:a:0","-t","4",
        "-c:v","libx264","-crf","19","-preset","fast","-pix_fmt","yuv420p",
        "-c:a","aac","-movflags","+faststart",str(compare)],timeout=240)
    for label,clip in (("original",original),("tbdub",final)):
        sh(["ffmpeg","-y","-v","error","-i",str(clip),"-vf",
            "fps=1,scale=336:192,tile=2x2","-frames:v","1",
            str(OUT/(label+"_contact.jpg"))],timeout=180)
    save("status.json",{
        "stage":"REAL_TBDUB_MP4_GENERATED_HUMAN_REVIEW_REQUIRED",
        "ready_files":[final.name,compare.name],
        "source_modified":False,
        "original_v2v_retained":True,
        "video_duration":f["format"]["duration"],
        "size_bytes":final.stat().st_size,
        "sha256":hashlib.sha256(final.read_bytes()).hexdigest(),
        "instruction":"User must review lip anatomy, teeth, motion and voice before 3min",
    })
    print("REAL_TBDUB_FINAL_MP4_READY",final,flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=["source","run","finish"])
    phase=parser.parse_args().stage
    {"source":source,"run":run,"finish":finish}[phase]()
