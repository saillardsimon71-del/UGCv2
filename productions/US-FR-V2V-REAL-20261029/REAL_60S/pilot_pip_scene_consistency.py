#!/usr/bin/env python3
"""CPU-only actor/background consistency pilot on the validated 60s French hybrid.

Does not touch UGCv2's original generators. The replacement inset uses frames
of the already face-swapped, already lip-synced artificial presenter; its lip
motion is NOT re-dubbed for the PiP phrases in this conservative first pass.
The voice and all UI pixels outside the known PiP rectangle are preserved.
Private technical comparison; original tutorial publishing rights NOT granted.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import cv2
import numpy as np
import mediapipe as mp

ROOT=Path("productions/US-FR-V2V-REAL-20261029/REAL_60S")
INPUT=ROOT/"SCENE_INPUT"
OUT=ROOT/"PIP_NEW_SET_CPU"
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=INPUT/"UGCv2_FR_60s_TBDub_HYBRID_TEST.mp4"
ACTOR=INPUT/"cam_a_tbdub_french.mp4"
PHOTO=INPUT/"office_photo_12700377.jpeg"
FPS=25
SIZE=(1920,1080)
PIP=(1228,0,692,380)
FULL=[(5.76,12.0),(21.12,26.88),(29.76,31.20),(56.56,60.0)]
INSET=[(0.88,5.76),(31.96,56.56)]

def digest(file):
    h=hashlib.sha256()
    with open(file,"rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def command(args,timeout=150):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError(" ".join(args[:5])+": "+p.stderr[-1000:])
    return p.stdout

def probe(file):
    return json.loads(command(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(file)]))

def intersects(t,regions):
    return any(a<=t<b for a,b in regions)

def cover(image,width,height):
    ih,iw=image.shape[:2]
    if min(ih,iw)<=0:raise RuntimeError("Invalid background")
    ratio=max(width/iw,height/ih)
    scaled=cv2.resize(image,(round(iw*ratio),round(ih*ratio)),interpolation=cv2.INTER_AREA)
    h,w=scaled.shape[:2]; left=(w-width)//2;top=(h-height)//2
    return scaled[top:top+height,left:left+width].copy()

def new_background():
    bg=cv2.imread(str(PHOTO),cv2.IMREAD_COLOR)
    if bg is None or min(bg.shape[:2])<480:raise RuntimeError("Missing verified high-res Pexels photograph")
    bg=cover(bg,*SIZE)
    bg=cv2.GaussianBlur(bg,(15,15),0)
    # Slightly warmer, darker for the existing presenter lighting.
    bg=cv2.convertScaleAbs(bg,alpha=0.72,beta=5)
    return bg

def mask_for(image,segmenter):
    h,w=image.shape[:2]
    scaled=cv2.resize(image,(480,270),interpolation=cv2.INTER_AREA)
    rgb=cv2.cvtColor(scaled,cv2.COLOR_BGR2RGB)
    s=segmenter.process(rgb)
    if s.segmentation_mask is None:raise RuntimeError("Selfie segmentation returned no mask")
    raw=s.segmentation_mask
    if not np.isfinite(raw).all():raise RuntimeError("Non-finite human alpha")
    coverage=float(np.mean(raw>.5))
    # A transition frame may contain no actor; keep the approved frame rather than pretending the mask exists.
    if coverage<.02:return np.zeros((h,w),np.float32),coverage
    if coverage>.90:raise RuntimeError(f"Unreliable human segmentation: {coverage:.3f}")
    matte=np.clip((raw-.22)/.52,0,1)
    matte=cv2.GaussianBlur(matte,(7,7),0)
    return cv2.resize(matte,(w,h),interpolation=cv2.INTER_LINEAR).astype(np.float32),coverage

def outfit_distinction(person,alpha):
    """Recolour the source white cap to navy, keeping shape/lighting and identity."""
    h,w=person.shape[:2]
    upper=int(h*.30)
    hsv=cv2.cvtColor(person[:upper],cv2.COLOR_BGR2HSV)
    # Bright, desaturated headwear only, not skin and not scene background.
    x0=int(w*.31); x1=int(w*.71)
    white=((hsv[:,:,1]<66)&(hsv[:,:,2]>132)).astype(np.float32)
    keep=np.zeros((upper,w),np.float32);keep[:,x0:x1]=1
    white*=keep
    white*=alpha[:upper]
    white=cv2.GaussianBlur(white,(7,7),0)
    # Charcoal blue cap, preserve fabric shading.
    replacement=np.empty_like(person[:upper])
    value=(hsv[:,:,2].astype(np.float32)*.21+17).clip(0,255).astype(np.uint8)
    replacement[:]=(41,29,18)
    replacement[:,:,0]=np.clip(value.astype(np.int16)+15,0,255).astype(np.uint8)
    person=person.copy()
    person[:upper]=(person[:upper].astype(np.float32)*(1-white[:,:,None])+
                     replacement.astype(np.float32)*white[:,:,None]).astype(np.uint8)
    return person

def actor_on_set(frame,bg,segmenter):
    alpha,coverage=mask_for(frame,segmenter)
    if coverage<.02:return frame.copy(),0.0
    actor=outfit_distinction(frame,alpha)
    composite=(actor.astype(np.float32)*alpha[:,:,None]+
               bg.astype(np.float32)*(1-alpha[:,:,None])).clip(0,255).astype(np.uint8)
    return composite,coverage

def pip_loop(background):
    reader=cv2.VideoCapture(str(ACTOR))
    if not reader.isOpened():raise RuntimeError("No previously proven artificial actor footage")
    frames=[];coverage=[]
    with mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1) as segmenter:
        while len(frames)<160:
            ok,frame=reader.read()
            if not ok:break
            if frame.shape[:2]!=(1080,1920):frame=cv2.resize(frame,SIZE)
            foreground,cov=actor_on_set(frame,background,segmenter)
            resized=cv2.resize(foreground,(PIP[2],PIP[3]),interpolation=cv2.INTER_AREA)
            frames.append(resized);coverage.append(cov)
    reader.release()
    if len(frames)<110:raise RuntimeError("Artificial presenter source unexpectedly short")
    return frames,coverage

def run():
    for path in (SOURCE,ACTOR,PHOTO):
        if not path.is_file():raise RuntimeError("Missing "+str(path))
    meta=probe(SOURCE)
    stream=next(x for x in meta["streams"] if x["codec_type"]=="video")
    if (stream["width"],stream["height"])!=SIZE or abs(float(meta["format"]["duration"])-60)>.2:
        raise RuntimeError("Not the validated 60s 1080p source")
    if not any(x["codec_type"]=="audio" for x in meta["streams"]):
        raise RuntimeError("Missing previously approved Chatterbox French audio")
    bg=new_background()
    cv2.imwrite(str(OUT/"office_set_background.jpg"),bg,[cv2.IMWRITE_JPEG_QUALITY,92])
    actor_frames,actor_cov=pip_loop(bg)
    cap=cv2.VideoCapture(str(SOURCE))
    if not cap.isOpened():raise RuntimeError("Cannot decode approved final 60s MP4")
    dest=OUT/"UGCv2_FR60_NEW_FACE_ALL_PIP_NEW_SET_PILOT.mp4"
    encoder=subprocess.Popen(["ffmpeg","-y","-hide_banner","-loglevel","error",
        "-f","rawvideo","-pix_fmt","bgr24","-s","1920x1080","-r",str(FPS),
        "-i","pipe:0","-i",str(SOURCE),"-map","0:v:0","-map","1:a:0",
        "-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p",
        "-c:a","copy","-t","60","-movflags","+faststart",str(dest)],
        stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    records=[];n=0;fail=None
    with mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1) as segmenter:
        try:
            while n<1500:
                ok,frame=cap.read()
                if not ok:raise RuntimeError(f"Source ended unexpectedly at frame {n}")
                t=n/FPS
                result=frame
                mode="screens"
                if intersects(t,FULL):
                    result,cov=actor_on_set(frame,bg,segmenter)
                    mode="full_presenter"
                elif intersects(t,INSET):
                    # Replace ONLY the existing camera overlay. All UI remains.
                    result=frame.copy()
                    x,y,w,h=PIP
                    # Distribute the entire prepared actor loop over the two blocks.
                    offset=0 if t<6 else 11
                    idx=(round((t-offset)*FPS))%len(actor_frames)
                    result[y:y+h,x:x+w]=actor_frames[idx]
                    mode="pip_new_actor"
                if n in (50,175,250,575,750,825,950,1125,1375,1450):
                    roi=result[PIP[1]:PIP[1]+PIP[3],PIP[0]:PIP[0]+PIP[2]]
                    baseline=frame[PIP[1]:PIP[1]+PIP[3],PIP[0]:PIP[0]+PIP[2]]
                    mae=float(np.mean(np.abs(roi.astype(np.int16)-baseline.astype(np.int16))))
                    records.append({"second":t,"mode":mode,"pip_mae_vs_source":round(mae,2)})
                    cv2.imwrite(str(OUT/f"new_set_at_{int(t)}.jpg"),result,
                                [cv2.IMWRITE_JPEG_QUALITY,87])
                encoder.stdin.write(result.tobytes())
                if n%250==0:print("COMPOSITE_PROGRESS",n,"of 1500",flush=True)
                n+=1
        except BaseException as e:fail=e
    cap.release()
    if encoder.stdin:encoder.stdin.close()
    if encoder.stderr:
        stderr=encoder.stderr.read().decode(errors="replace")[-2400:]
    else:stderr=""
    rc=encoder.wait()
    if fail:raise fail
    if rc:raise RuntimeError("ffmpeg encode failed: "+stderr)
    if n!=1500:raise RuntimeError(f"Short render: {n} frames")
    vmeta=probe(dest)
    if abs(float(vmeta["format"]["duration"])-60)>.2:raise RuntimeError("Incomplete full minute")
    for sec in [2,23,38,45,55,58]:
        r=min(records,key=lambda x:abs(x["second"]-sec))
        if abs(r["second"]-sec)<=2.1 and r["mode"]!="screens" and r["pip_mae_vs_source"]<5:
            raise RuntimeError(f"Actor or background is visually unchanged: {r}")
    command(["ffmpeg","-v","error","-xerror","-i",str(dest),"-f","null","-"],timeout=300)
    report={
        "stage":"CPU_COMPOSITE_REAL_MP4_NEEDS_HUMAN_VISUAL_REVIEW",
        "duration":float(vmeta["format"]["duration"]),"fps":FPS,
        "sha256":digest(dest),"original_60s_sha256":digest(SOURCE),
        "reused_validated_artifact_run":40957764927,
        "new_photo_url":"https://www.pexels.com/photo/the-interior-of-a-home-office-12700377/",
        "source_preserved":"French original aligned voice and demo/screen pixels outside PiP",
        "full_presenter_segments":FULL,"original_pip_replaced_in":INSET,
        "pip_original_face_visibility":"Expected absent in designated inset rectangles",
        "speaker_reference":"existing cam_a previously face-swapped TBDub frame stream",
        "inset_audio_sync":"NOT VALIDATED: reused mouth motion not newly aligned to its voice",
        "new_set":"photographic Pexels office, blurred/darkened; segmenter is person-only",
        "outfit":"bright cap recolored to dark blue where the person matte supports it",
        "caveats":["PiP may show repeated gestures","Microphone may be partially removed by person-only segmentation","Original trigger overlay may show old background faintly","No independent identity verification","Not for public distribution"],
        "pixel_checks":records,"pip_foreground_coverage_mean":round(float(np.mean(actor_cov)),3),
        "human_review_required":True,"GPU_calls":0
    }
    (OUT/"pilot_status.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print("REAL_CPU_PIP_SET_VIDEO_DONE",dest,flush=True)

if __name__=="__main__":run()
