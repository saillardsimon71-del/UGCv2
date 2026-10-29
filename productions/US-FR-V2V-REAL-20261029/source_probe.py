#!/usr/bin/env python3
"""Read-only inspection of a YouTube reference. No LLM, no GPU, no publishing."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import cv2
import numpy as np

OUT=Path("productions/US-FR-V2V-REAL-20261029/OUTPUT")
URL="https://www.youtube.com/watch?v=KSOxkhWs2Ic"
def call(args,timeout=180):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout).stdout
def report(obj,name="source_report.json"):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    source=OUT/"download.mp4"
    cmd=[sys.executable,"-m","yt_dlp","--no-playlist","--no-warnings","--force-overwrites",
         "-f","best[height<=480][ext=mp4]/best[height<=480]/best",
         "--merge-output-format","mp4","-o",str(OUT/"download.%(ext)s"),URL]
    try:
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
        if result.returncode:
            raise RuntimeError("yt-dlp refused: "+(result.stderr+result.stdout)[-1600:])
        files=sorted(OUT.glob("download.*"),key=lambda p:p.stat().st_size,reverse=True)
        if not files: raise RuntimeError("No accessible source")
        src=files[0]
        if src!=source:
            call(["ffmpeg","-y","-v","error","-i",str(src),"-c:v","libx264","-preset","veryfast",
                  "-crf","25","-c:a","aac",str(source)],timeout=240)
            src.unlink()
        cap=cv2.VideoCapture(str(source))
        count=cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps=cap.get(cv2.CAP_PROP_FPS)
        duration=count/fps if fps else 0
        if not (430<duration<510): raise RuntimeError(f"Wrong source duration {duration}")
        detector=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
        times=list(range(2,int(duration)-4,8))
        samples=[]
        thumbs=[]
        for sec in times:
            cap.set(cv2.CAP_PROP_POS_MSEC,sec*1000)
            ok,frame=cap.read()
            if not ok:continue
            small=cv2.resize(frame,(384,216),interpolation=cv2.INTER_AREA)
            gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
            faces=detector.detectMultiScale(gray,scaleFactor=1.1,minNeighbors=5,minSize=(30,30))
            face_area=sum(w*h for x,y,w,h in faces)/(384*216)
            samples.append({"time_s":sec,"faces":len(faces),"face_area_fraction":round(float(face_area),4)})
            cv2.putText(small,f"{sec}s  faces={len(faces)}",(8,23),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,245,255),2)
            for x,y,w,h in faces:cv2.rectangle(small,(x,y),(x+w,y+h),(0,255,0),2)
            thumbs.append(small)
        cap.release()
        if len(thumbs)<25:raise RuntimeError("Too few real source frames decoded")
        cols=6
        rows=(len(thumbs)+cols-1)//cols
        contact=np.zeros((rows*216,cols*384,3),dtype=np.uint8)
        for i,frame in enumerate(thumbs):contact[(i//cols)*216:(i//cols+1)*216,(i%cols)*384:(i%cols+1)*384]=frame
        cv2.imwrite(str(OUT/"source_scan_contact.jpg"),contact,[cv2.IMWRITE_JPEG_QUALITY,87])
        # For a transformation benchmark prefer a 15-second interval with recognizable person,
        # if present. Otherwise mark SCREEN_ONLY; no false face-swap success.
        faces=[s for s in samples if s["faces"]>0 and s["face_area_fraction"]>.006]
        if faces:
            selected=max(faces,key=lambda s:s["face_area_fraction"])
            start=max(0,min(duration-15.2,selected["time_s"]-3))
            kind="POTENTIAL_HUMAN_ON_SCREEN_NEEDS_REVIEW"
        else:
            start=0.0
            kind="SCREEN_OR_UNCLASSIFIED_NO_RELIABLE_FACE"
        guide=OUT/"reference-15s.mp4"
        call(["ffmpeg","-y","-v","error","-ss",str(start),"-i",str(source),
              "-t","15","-vf","fps=24,scale=1344:768:force_original_aspect_ratio=increase,"
              "crop=1344:768,setsar=1,format=yuv420p","-an",
              "-c:v","libx264","-preset","veryfast","-crf","26",
              "-movflags","+faststart",str(guide)],timeout=180)
        info=json.loads(call(["ffprobe","-v","error","-count_frames","-show_streams",
                              "-show_format","-of","json",str(guide)]))
        stream=next(s for s in info["streams"] if s["codec_type"]=="video")
        if (stream["width"],stream["height"])!=(1344,768) or int(stream["nb_read_frames"])!=360:
            raise RuntimeError("Wrong 15sec output geometry or frames")
        if guide.stat().st_size>=20_000_000:raise RuntimeError("V2V guide too large")
        call(["ffmpeg","-v","error","-y","-i",str(guide),"-vf",
              "fps=1,scale=224:128,tile=5x3",
              "-frames:v","1",str(OUT/"selected_15s_contact.jpg")])
        obj={"status":"SOURCE_DOWNLOADED_AND_INSPECTED_NO_GPU","source_url":URL,
             "duration_s":round(duration,1),"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
             "selected_start_s":round(start,2),"scene_kind":kind,
             "face_detections":len(faces),"sampled_seconds":len(samples),
             "selected_guide_sha256":hashlib.sha256(guide.read_bytes()).hexdigest(),
             "guide_frames":int(stream["nb_read_frames"]),"guide_bytes":guide.stat().st_size,
             "publication":False,"gpu_call_started":False,"face_detector":"Haar heuristic, not identity",
             "warning":"Detection does not certify a presenter shot or any license/right."}
        report(obj)
        print(json.dumps(obj))
    except BaseException as e:
        report({"status":"BLOCKED_BEFORE_GPU","reason":str(e)[:2000]})
        raise
if __name__=="__main__":prepare()
