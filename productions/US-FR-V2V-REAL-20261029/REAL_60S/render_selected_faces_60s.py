"""Replace only four visibly full-frame speaker shots in original 60s video.

Reuses the 4s-verified FaceFusion selector-one worker and the already-generated
artificial instructor portrait. Screen recordings/diagrams are never passed
to a generative model. PIP speaker remains original, flagged in delivery.
Output is silent full-length 60s video and a verifiable pixel-change report.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0,str(Path.cwd()))
ROOT=Path("productions/US-FR-V2V-REAL-20261029/REAL_60S")
INPUT=ROOT/"OUTPUT"/"source_window_60s.mp4"
PORTRAIT=ROOT/"FACE_SWAP"/"UGCv2_presenter_reference_5s.jpg"
OUTPUT=ROOT/"FACE_SWAP_SELECTIVE"
OUTPUT.mkdir(parents=True,exist_ok=True)
SHOTS=[("cam_a",5.76,12.00),("cam_b",21.12,26.88),
       ("cam_c_short",29.76,31.20),("cam_d",56.56,60.00)]

def sh(parts,timeout=240):
    p=subprocess.run(parts,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError(" ".join(parts[:5])+"\n"+(p.stdout+p.stderr)[-3000:])
    return p.stdout

def sha(file):
    h=hashlib.sha256()
    with open(file,"rb") as f:
        while x:=f.read(1<<20):h.update(x)
    return h.hexdigest()

def meta(file):
    return json.loads(sh(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(file)]))

def duration(file):
    return float(meta(file)["format"]["duration"])

def save(name,obj):
    (OUTPUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def prepare():
    if not INPUT.is_file() or not PORTRAIT.is_file():
        raise RuntimeError("Missing validated source or previously generated artificial actor")
    proof=json.loads((ROOT/"OUTPUT"/"source_provenance.json").read_text())
    if sha(INPUT)!=proof["source_window_sha256"] or abs(duration(INPUT)-60)>.2:
        raise RuntimeError("Source 60s provenance mismatch")
    if PORTRAIT.read_bytes()[:2]!=b"\xff\xd8":
        raise RuntimeError("Invalid generated actor reference JPEG")
    for label,start,end in SHOTS:
        dest=OUTPUT/(label+"_original.mp4")
        sh(["ffmpeg","-y","-v","error","-ss",str(start),"-i",str(INPUT),
            "-t",str(round(end-start,3)),"-map","0:v:0","-vf","fps=25,format=yuv420p",
            "-an","-c:v","libx264","-preset","veryfast","-crf","18",str(dest)])
        if abs(duration(dest)-(end-start))>.15:
            raise RuntimeError(f"Clip extraction inaccurate for {label}")
    save("source_provenance.json",{
        "original_60s_run":40942927735,
        "actor_reference_run":40899629965,
        "face_selector_4s_proof_run":40948918285,
        "source_sha256":sha(INPUT),"actor_sha256":sha(PORTRAIT),
        "selected_shots":SHOTS,"screen_clip_pixels_policy":"preserve original source",
        "PIP_actor":"not replaced in this first selective pilot",
        "gpu_calls_started":0,"not_for_publication":True,
    })
    print("FOUR_ACTUAL_FACE_SHOTS_EXTRACTED_CPU",flush=True)

def render():
    if os.getenv("STUDIO_MODAL_WORKSPACE")!="lucj76861" or os.getenv("ALLOW_FOUR_FACE_GPU")!="YES":
        raise RuntimeError("Missing GPU one-time authorization")
    if os.getenv("GITHUB_RUN_ATTEMPT","1")!="1":
        raise RuntimeError("No unattended GPU retry")
    if not (OUTPUT/"source_provenance.json").is_file():
        raise RuntimeError("Source provenance missing")
    import modal
    from deploy import modal_fr60_faceswap_selected as worker
    portrait=base64.b64encode(PORTRAIT.read_bytes()).decode()
    completed=[]
    save("render_status.json",{"step":"FACE_SELECTIVE_STARTED","number_of_shots":4})
    with worker.app.run(name="ugcv2-fr60-only-four-face-shots",environment_name="main"):
        for label,start,end in SHOTS:
            inp=OUTPUT/(label+"_original.mp4")
            if not inp.is_file():raise RuntimeError("Missing original "+label)
            r=worker.face_swap_explicit_one.remote(
                base64.b64encode(inp.read_bytes()).decode(),portrait)
            # IMPORTANT: verified worker contract is video_base64, NOT video_b64.
            raw=base64.b64decode(r["video_base64"],validate=True)
            file=OUTPUT/(label+"_newactor.mp4")
            file.write_bytes(raw)
            if sha(file)!=r["metadata"]["sha256"]:
                raise RuntimeError("FaceFusion SHA mismatch "+label)
            completed.append({"id":label,"start":start,"end":end,
                              "video_sha256":sha(file),"gpu_seconds":r["metadata"].get("wall_seconds")})
            save("face_render_receipt.json",{"status":"GPU_PARTIAL","completed":completed})
            print("FOUR_SHOT_FACE_RENDER",label,flush=True)
    save("face_render_receipt.json",{"status":"ALL_FOUR_GPU_SHOTS_DONE","completed":completed})

def pixel_check(original:Path,swapped:Path,label:str):
    a=cv2.VideoCapture(str(original));b=cv2.VideoCapture(str(swapped))
    d=min(duration(original),duration(swapped))
    measurements=[]
    for sec in (max(.25,d*.22),max(.5,d*.55),max(.8,d*.8)):
        for cap in (a,b):cap.set(cv2.CAP_PROP_POS_MSEC,sec*1000)
        ga,im=a.read();gb,changed=b.read()
        if not ga or not gb:continue
        if changed.shape!=im.shape:changed=cv2.resize(changed,(im.shape[1],im.shape[0]))
        # Use central face ROI for actual full-frame presenter shots.
        region=(slice(105,660),slice(590,1150))
        diff=np.abs(im[region].astype(np.int16)-changed[region].astype(np.int16))
        measurements.append({"relative_second":round(sec,2),
                             "roi_mae":round(float(diff.mean()),3),
                             "pixels_gt20":round(float(np.mean(diff>20)),5)})
    a.release();b.release()
    if not measurements or float(np.mean([m["roi_mae"] for m in measurements]))<4.3:
        raise RuntimeError("Identity did not change on "+label+"; no fake success")
    return measurements

def assemble():
    receipt=json.loads((OUTPUT/"face_render_receipt.json").read_text())
    if receipt.get("status")!="ALL_FOUR_GPU_SHOTS_DONE":
        raise RuntimeError("Not all four actual face shots rendered")
    ready=[]
    for label,start,end in SHOTS:
        original=OUTPUT/(label+"_original.mp4")
        changed=OUTPUT/(label+"_newactor.mp4")
        d=round(end-start,3)
        metrics=pixel_check(original,changed,label)
        normalized=OUTPUT/(label+"_normalized.mp4")
        sh(["ffmpeg","-y","-v","error","-i",str(changed),
            "-vf",f"fps=25,scale=1920:1080:flags=lanczos,"
                  f"tpad=stop_mode=clone:stop_duration=0.5,"
                  f"trim=duration={d},setpts=PTS-STARTPTS,format=yuv420p",
            "-an","-t",str(d),"-c:v","libx264","-preset","veryfast","-crf","18",
            str(normalized)],timeout=300)
        if abs(duration(normalized)-d)>.12:raise RuntimeError("Trim inaccurate "+label)
        ready.append((label,start,end,normalized,metrics))
    save("pixel_evidence.json",{"all_four_faces_changed":True,
                               "shots":{x[0]:x[-1] for x in ready}})
    inputs=["-i",str(INPUT)]
    for *_,file,measure in ready:inputs.extend(["-i",str(file)])
    graph=[]
    prior="[0:v]"
    for index,(label,start,end,file,metrics) in enumerate(ready,1):
        segment=f"[seg{index}]";result=f"[mix{index}]"
        graph.append(f"[{index}:v]setpts=PTS-STARTPTS+{start}/TB,format=yuv420p{segment}")
        graph.append(f"{prior}{segment}overlay=0:0:format=auto:eof_action=pass:repeatlast=0:"
                     f"enable='gte(t,{start})*lt(t,{end})'{result}")
        prior=result
    output=OUTPUT/"faceswapped_video_no_audio_60s.mp4"
    sh(["ffmpeg","-y","-v","error"]+inputs+[
        "-filter_complex",";".join(graph),"-map",prior,"-t","60",
        "-r","25","-an","-c:v","libx264","-preset","fast","-crf","18",
        "-pix_fmt","yuv420p","-movflags","+faststart",str(output)],timeout=900)
    sh(["ffmpeg","-v","error","-xerror","-i",str(output),"-f","null","-"],timeout=300)
    if abs(duration(output)-60)>.15:raise RuntimeError("Not a complete one-minute video")
    for sec in (7,23,30,45,58):
        sh(["ffmpeg","-y","-v","error","-ss",str(sec),"-i",str(output),
            "-frames:v","1",str(OUTPUT/f"face_at_{sec}.jpg")])
    save("status.json",{
        "stage":"AUTHENTIC_60S_FACE_SWAP_MP4_CREATED_VISUAL_REVIEW_REQUIRED",
        "video_sha256":sha(output),
        "video_duration_s":duration(output),
        "full_frame_faces_proven_changed":True,
        "number_of_shots":4,
        "screen_visuals":"preserved original",
        "PIP_presenter":"unmodified — additional selective work needed",
        "face_visual_quality":"HUMAN_REVIEW_REQUIRED",
        "new_actor":"selected original full-screen presenter shots",
        "source_unchanged":True,
    })
    print("FOUR_FACE_IDENTITY_CHANGED_PIXEL_VERIFIED_60S_SOURCE_VIDEO_READY",flush=True)

if __name__=="__main__":
    stage=sys.argv[1] if len(sys.argv)>1 else "prepare"
    {"prepare":prepare,"render":render,"assemble":assemble}[stage]()
