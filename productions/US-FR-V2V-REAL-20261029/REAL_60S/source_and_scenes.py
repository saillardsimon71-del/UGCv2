#!/usr/bin/env python3
"""CPU-only authentic 60 s source and scene audit for UGCv2.
This is NOT the finished French dub and uses zero GPUs.

Only video from the existing user-provided YouTube reference imported through
the previously verified bridge. Verify original full-source checksum against
GitHub artifact 40898616414. Do not rerender screen recordings or UI text.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np

BASE=Path("productions/US-FR-V2V-REAL-20261029")
ROOT=BASE/"REAL_60S"
OUT=ROOT/"OUTPUT"
OUT.mkdir(parents=True,exist_ok=True)
PREVIOUS=ROOT/"SOURCE_PROBE"
BRIDGE=BASE/"SOURCE_BRIDGE_URL.txt"
VIDEO=OUT/"source_window_60s.mp4"
START=42.0
DURATION=60.0
SOURCE_ID="KSOxkhWs2Ic"

def run(cmd:list[str], timeout:int=250)->str:
    p=subprocess.run(cmd,check=False,capture_output=True,text=True,timeout=timeout)
    if p.returncode!=0:raise RuntimeError((p.stderr+p.stdout)[-1400:])
    return p.stdout

def probe(p:Path)->dict:
    return json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(p)]))

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        while b:=f.read(1<<20):h.update(b)
    return h.hexdigest()

def save(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def obtain_and_cut():
    if not BRIDGE.is_file() or not (PREVIOUS/"source_report.json").is_file():
        raise RuntimeError("Missing authorized user-supplied video bridge or original provenance")
    provenance=json.loads((PREVIOUS/"source_report.json").read_text(encoding="utf-8"))
    if provenance.get("source_url")!="https://www.youtube.com/watch?v="+SOURCE_ID:
        raise RuntimeError("Previous source proof does not match the requested video")
    url=BRIDGE.read_text(encoding="utf-8").strip()
    if not url.startswith("https://storage.googleapis.com/vidiq-user-videos/"):
        raise RuntimeError("Bridge URL is not the previously verified video provider")
    source=OUT/"verified_source.mp4"
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req,timeout=50) as src,source.open("wb") as dst:
            total=0
            while chunk:=src.read(1<<20):
                total+=len(chunk)
                if total>300_000_000:raise RuntimeError("Source exceeds safety cap")
                dst.write(chunk)
        if source.stat().st_size<500_000 or sha(source)!=provenance.get("source_sha256"):
            raise RuntimeError("Downloaded source SHA256 mismatch — no unverified edits")
        meta=probe(source)
        if not 430<float(meta["format"]["duration"])<510:
            raise RuntimeError("Unexpected original source video duration")
        run(["ffmpeg","-y","-v","error","-ss",str(START),"-i",str(source),
             "-t",str(DURATION),"-map","0:v:0","-map","0:a:0?",
             "-vf","fps=25,format=yuv420p",
             "-c:v","libx264","-crf","19","-preset","fast",
             "-c:a","aac","-b:a","160k","-ar","48000",
             "-movflags","+faststart",str(VIDEO)],timeout=300)
        info=probe(VIDEO)
        secs=float(info["format"]["duration"])
        v=next((x for x in info["streams"] if x["codec_type"]=="video"),None)
        if not 59.75<=secs<=60.25 or v is None:raise RuntimeError("60 s source extraction failed")
        save("source_provenance.json",{
            "source_url":provenance["source_url"],
            "source_sha256":sha(source),
            "previous_source_probe_run":40898616414,
            "original_provider":"user supplied existing vidiq import",
            "source_duration_s":float(meta["format"]["duration"]),
            "window_start_s":START,"window_end_s":START+DURATION,
            "duration_s":secs,"fps":25,
            "original_resolution":[v["width"],v["height"]],
            "source_window_sha256":sha(VIDEO),
            "rights":"private technical study only; publication or reuse requires rights",
            "gpu_allocated":False,
        })
        print("VERIFIED_60S_SOURCE_WINDOW",secs,"seconds",flush=True)
    finally:
        # Full eight-minute original is not needed after the exact 60 s segment.
        source.unlink(missing_ok=True)

def scenes():
    if not VIDEO.exists():raise RuntimeError("No real source window, no imagined storyboard")
    cap=cv2.VideoCapture(str(VIDEO))
    fps=float(cap.get(cv2.CAP_PROP_FPS))
    frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps<20 or frames<1400:raise RuntimeError("Video too short to classify")
    cascade=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
    step=max(1,round(fps/2)) # 2 samples per second
    metrics=[]
    prev=None
    face_count=0
    frame=0
    image_samples=[]
    while True:
        ok,shot=cap.read()
        if not ok:break
        if frame % step==0:
            sec=frame/fps
            img=cv2.resize(shot,(384,216),interpolation=cv2.INTER_AREA)
            gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            found=cascade.detectMultiScale(gray,scaleFactor=1.12,minNeighbors=5,minSize=(30,30))
            area=float(sum(w*h for x,y,w,h in found)/(384*216))
            present=area>.007
            change=float(np.mean(cv2.absdiff(gray,prev)>45)) if prev is not None else 0.0
            has_cut=change>.28
            m={"relative_s":round(sec,2),"source_s":round(START+sec,2),
               "face_heuristic":present,"face_area_ratio":round(area,4),
               "large_frame_change":has_cut,"changed_pixel_fraction":round(change,3)}
            metrics.append(m)
            prev=gray
            if int(round(sec*2))%6==0:
                image_samples.append((sec,img.copy(),m))
        frame+=1
    cap.release()
    if len(metrics)<90:raise RuntimeError("Insufficient decoded frames")
    cols=4;cellw=384;cellh=216
    rows=math.ceil(len(image_samples)/cols)
    sheet=np.zeros((rows*cellh,cols*cellw,3),dtype=np.uint8)
    for i,(sec,img,m) in enumerate(image_samples):
        marked=img.copy()
        txt=f"{int(START+sec):03d}s | {'FACE?' if m['face_heuristic'] else 'SCREEN?'}"
        cv2.rectangle(marked,(0,0),(290,27),(9,9,9),-1)
        cv2.putText(marked,txt,(10,20),cv2.FONT_HERSHEY_SIMPLEX,.56,(255,255,255),2)
        y=(i//cols)*cellh; x=(i%cols)*cellw
        sheet[y:y+cellh,x:x+cellw]=marked
    cv2.imwrite(str(OUT/"contact_60s_real_frames.jpg"),sheet,[cv2.IMWRITE_JPEG_QUALITY,88])
    # Do not convert heuristic face flags into production decisions automatically.
    # Cuts are to be manually reviewed against the actual contact sheet.
    cuts=[m for m in metrics if m["large_frame_change"]]
    seconds={}
    for t in range(60):
        matching=[m for m in metrics if t<=m["relative_s"]<t+1]
        if not matching:continue
        seconds[str(t)]={
            "face_heuristic":sum(bool(m["face_heuristic"]) for m in matching)>=len(matching)/2,
            "max_face_area":round(max(m["face_area_ratio"] for m in matching),4),
            "max_frame_change":round(max(m["changed_pixel_fraction"] for m in matching),3),
        }
    save("scene_analysis.json",{
        "source_window_s":[START,START+DURATION],
        "seconds":seconds,
        "candidate_shot_cuts_source_s":[m["source_s"] for m in cuts],
        "face_heuristic":"OpenCV Haar estimates presence only; never confirms identity",
        "screen_policy":"preserve original pixels/text and exact screen-event timing",
        "presenter_policy":"only transform reviewed face segments, avoid new hallucinated UI",
        "voice_policy":"match original phrase boundaries, pauses and emphasis; do not stretch an entire minute",
        "render_prohibited_until_shots_reviewed":True,
        "next_step":"review contact_60s_real_frames.jpg and tag exact face/screen segment boundaries",
    })
    print("SCENE_SCAN_COMPLETE",len(metrics),"samples",len(cuts),"possible cuts",flush=True)

if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "all"
    if mode=="all":obtain_and_cut();scenes()
    elif mode=="source":obtain_and_cut()
    elif mode=="scenes":scenes()
    else:raise SystemExit("modes: all, source, scenes")
