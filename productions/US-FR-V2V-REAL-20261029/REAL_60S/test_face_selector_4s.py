#!/usr/bin/env python3
"""Do not repeat an unverified face swap. Test 4s and measure actual ROI pixels.

The original full-minute FaceFusion pass did nothing (MAE 1.3-1.6 pixel due to
recompression). Use --face-selector-mode one, compare original/new center-face
ROI across frames; block 60s rerun if the actor is not visibly different.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0,str(Path.cwd()))
import cv2
import numpy as np

ROOT=Path("productions/US-FR-V2V-REAL-20261029/REAL_60S")
SOURCE=ROOT/"OUTPUT"/"source_window_60s.mp4"
FACE=ROOT/"FACE_SWAP"/"UGCv2_presenter_reference_5s.jpg"
OUT=ROOT/"SELECT_ONE_4S"
OUT.mkdir(parents=True,exist_ok=True)

def sh(cmd,timeout=150):
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    if r.returncode:raise RuntimeError((r.stdout+r.stderr)[-2500:])
    return r.stdout

def sha(p:Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dump(file,obj):
    (OUT/file).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n")

def prepare():
    if not SOURCE.is_file() or not FACE.is_file():
        raise RuntimeError("Authentic original 60s video and artificial LTX actor photo required")
    orig=OUT/"source_fullface_4s.mp4"
    sh(["ffmpeg","-y","-v","error","-ss","6.0","-i",str(SOURCE),
        "-t","4","-map","0:v:0","-vf","fps=25,format=yuv420p",
        "-an","-c:v","libx264","-crf","18","-preset","fast",str(orig)])
    if not 500_000<orig.stat().st_size<20_000_000:raise RuntimeError("Unexpected source 4sec size")
    dump("originals.json",{
        "original_source":40942927735,
        "identity":40899629965,
        "original":orig.name,
        "sha256":sha(orig),"face_jpeg_sha256":sha(FACE),
        "four_seconds":[48,52],"gpu_calls_at_preflight":0,
    })

def render():
    if os.getenv("STUDIO_MODAL_WORKSPACE")!="lucj76861" or os.getenv("SINGLE_FACE4_GPU")!="YES":
        raise RuntimeError("One A10G test authorization or workspace missing")
    if os.getenv("GITHUB_RUN_ATTEMPT","1")!="1":raise RuntimeError("No automatic GPU retry")
    if not (OUT/"originals.json").is_file():raise RuntimeError("CPU source proof missing")
    import modal
    from deploy import modal_fr60_faceswap_selected as face
    orig=OUT/"source_fullface_4s.mp4"
    with face.app.run(name="ugcv2-fr60-face-swap-selector-one-4s",environment_name="main"):
        result=face.face_swap_explicit_one.remote(
            base64.b64encode(orig.read_bytes()).decode(),
            base64.b64encode(FACE.read_bytes()).decode())
    p=OUT/"fixed_selected_one_4s.mp4"
    p.write_bytes(base64.b64decode(result["video_base64"],validate=True))
    if sha(p)!=result["metadata"]["sha256"]:
        raise RuntimeError("FaceFusion model MP4 hash mismatch")
    dump("render_metadata.json",result["metadata"])
    print("EXPLICIT_ONE_FACE_FUSION_RENDERED",flush=True)

def check():
    original=OUT/"source_fullface_4s.mp4"
    new=OUT/"fixed_selected_one_4s.mp4"
    if not original.is_file() or not new.is_file():raise RuntimeError("Missing actual rendered MP4")
    a=cv2.VideoCapture(str(original))
    b=cv2.VideoCapture(str(new))
    metrics=[]
    for second in (1.0,2.0,3.0):
        for cap in (a,b):cap.set(cv2.CAP_PROP_POS_MSEC,second*1000)
        good1,frame1=a.read()
        good2,frame2=b.read()
        if not good1 or not good2:raise RuntimeError("Cannot sample original/new face frames")
        # face centered in source at 1920x1080; use fixed center ROI only
        # to avoid mistaking the rest of the scene for changed identity.
        if frame2.shape!=frame1.shape:
            frame2=cv2.resize(frame2,(frame1.shape[1],frame1.shape[0]))
        rect=(slice(105,660),slice(590,1150))
        original_face=frame1[rect]
        changed_face=frame2[rect]
        diff=np.abs(original_face.astype(np.int16)-changed_face.astype(np.int16))
        metrics.append({
            "second":second,
            "face_roi_mae":round(float(diff.mean()),3),
            "face_roi_px_over_20":round(float(np.mean(diff>20)),5),
            "global_mae":round(float(np.abs(frame1.astype(np.int16)-frame2.astype(np.int16)).mean()),3),
        })
        if second==2:
            cv2.imwrite(str(OUT/"before_face_2s.jpg"),frame1,[cv2.IMWRITE_JPEG_QUALITY,88])
            cv2.imwrite(str(OUT/"after_face_2s.jpg"),frame2,[cv2.IMWRITE_JPEG_QUALITY,88])
    a.release();b.release()
    valid=(sum(m["face_roi_mae"] for m in metrics)/len(metrics)>4.5
           and sum(m["face_roi_px_over_20"] for m in metrics)/len(metrics)>.008)
    dump("pixel_evidence.json",{
        "metrics":metrics,"identity_replacement_detected":valid,
        "face_roi":{"x":[590,1150],"y":[105,660]},
        "original_unmodified_60s_remains_available":True,
        "no_60s_gpu_relaunch_if_no_change":True,
    })
    if not valid:raise RuntimeError("NO VISUAL CHANGE: face selector still ineffective; do not render 60s")
    sh(["ffmpeg","-y","-v","error","-i",str(original),"-i",str(new),
        "-filter_complex","[0:v]scale=672:384[a];[1:v]scale=672:384[b];[a][b]hstack=inputs=2[v]",
        "-map","[v]","-t","4","-an","-c:v","libx264","-crf","20",
        str(OUT/"compare_selector_one_4s.mp4")])
    print("NEW_ACTOR_VISUAL_CHANGE_DETECTED",json.dumps(metrics),flush=True)

if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "prepare"
    {"prepare":prepare,"render":render,"check":check}[mode]()
