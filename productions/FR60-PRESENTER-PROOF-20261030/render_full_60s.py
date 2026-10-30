#!/usr/bin/env python3
"""Actual one-minute identity-consistent French demo.
Reuses Work's approved single fictional actor/reference, LTX I2V and TBDub.
Five distinct 12s animations; no four-second master loops, no background
segmentation, no reuse of source face for generated media.
Source has third-party copyright: technical/private testing ONLY.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE=HERE/"FULL60_INPUT"/"UGCv2_FR_60s_TBDub_HYBRID_TEST.mp4"
PHOTO=HERE/"ASSETS"/"presenter-studio.png"
RUN=HERE/"FULL60_RUN"
RUN.mkdir(parents=True,exist_ok=True)
VOICE_SHA_SOURCE="346b8a25aa0722094f57e51aef3d41a97e1966f7ad1d04c4517c8fbbe5b7297d"
ACTOR_PHOTO_SHA="bd5ce8b0b67fd7cae6f197fc4608e7dff8b78882c162aba54c9e177d6e37bea3"
WORKSPACE="lucj76861"
FPS=25
SECONDS=12
N=5
FPS_FRAMES=300
PIP=(1428,0,492,444)
# Audit obtained by actual 1500-frame inspection in the approved Work branch.
SCENES=[
 ("screen",0.0,.68),("pip",.68,5.6),
 ("full",5.6,12.0),("title",12.0,14.24),
 ("pip",14.24,15.56),("screen",15.56,21.08),
 ("full",21.08,26.8),("screen",26.8,29.64),
 ("full",29.64,31.08),("pip",31.08,56.12),
 ("full",56.12,59.72),("pip",59.72,60.0)
]
PROMPT=(
 "A locked-off documentary tutorial camera shows the exact same fictional "
 "bald clean-shaven dark-skinned middle-aged man in the reference photograph, "
 "wearing the same blue shirt with a small lavalier microphone, in the exact "
 "same bright home office. He speaks naturally to the camera throughout, "
 "with small realistic mouth movements, subtle breathing and restrained "
 "head movements, one natural blink. Calm engaged tutorial delivery. "
 "His eyes remain open and directed into the lens. His head, shoulders, "
 "clothing, face shape, skin tone and age remain unchanged. The background, "
 "light, lens and camera framing stay perfectly stable. One continuous "
 "realistic shot, natural skin texture, clean clear mouth and eyes."
)

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        while chunk:=f.read(1<<20):h.update(chunk)
    return h.hexdigest()

def cmd(c,timeout=320):
    r=subprocess.run(list(map(str,c)),capture_output=True,text=True,timeout=timeout)
    if r.returncode:raise RuntimeError(" ".join(map(str,c[:6]))+"\n"+r.stderr[-3000:])
    return r.stdout

def meta(p):
    return json.loads(cmd(["ffprobe","-v","error","-show_format","-show_streams","-of","json",p]))

def save(p,record):
    p.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def check_workspace():
    if os.getenv("STUDIO_MODAL_WORKSPACE")!=WORKSPACE or not os.getenv("MODAL_TOKEN_ID") or not os.getenv("MODAL_TOKEN_SECRET"):
        raise RuntimeError("Missing verified lucj76861 workspace/token secrets")
    if os.getenv("GITHUB_RUN_ATTEMPT","1")!="1":
        raise RuntimeError("No unattended retry of GPU work")
    if os.getenv("ALLOW_FR60_NEW_ACTOR_GPU")!="YES":
        raise RuntimeError("Explicit authorization for full minute missing")

def validate_source():
    if not SOURCE.is_file() or not PHOTO.is_file():raise RuntimeError("Missing source artifact or validated photograph")
    if sha(SOURCE)!=VOICE_SHA_SOURCE:raise RuntimeError("Source does not match Work-approved French reference")
    if sha(PHOTO)!=ACTOR_PHOTO_SHA:raise RuntimeError("Actor photo differs from approved reference")
    m=meta(SOURCE)
    s=next(x for x in m["streams"] if x["codec_type"]=="video")
    if (s["width"],s["height"],s["r_frame_rate"])!=(1920,1080,"25/1") or abs(float(m["format"]["duration"])-60)>.1:
        raise RuntimeError("Expected original 1920x1080 25fps 60s")
    if not any(x["codec_type"]=="audio" for x in m["streams"]):raise RuntimeError("French audio missing")
    boundaries=[int(round(x*FPS)) for _,a,b in SCENES for x in (a,b)]
    if boundaries[0]!=0 or boundaries[-1]!=1500:raise RuntimeError("Timeline not complete")
    for i,(_,a,b) in enumerate(SCENES):
        if b<=a or (i>0 and abs(a-SCENES[i-1][2])>.0001):raise RuntimeError("Timeline gap")
    return m

def prepare():
    m=validate_source()
    if (RUN/"prepared.json").exists():raise RuntimeError("Already prepared; no duplicate run")
    for index in range(N):
        start=index*SECONDS
        common=["-y","-v","error","-ss",str(start),"-i",SOURCE,
                "-t",str(SECONDS)]
        cmd(["ffmpeg",*common,"-map","0:a:0","-ac","1","-ar","16000","-c:a","pcm_s16le",RUN/f"speech_{index}.wav"])
        if abs(float(meta(RUN/f"speech_{index}.wav")["format"]["duration"])-SECONDS)>.03:
            raise RuntimeError("Unaligned French audio chunk "+str(index))
    save(RUN/"prepared.json",{
        "reference_sha256":sha(SOURCE),"photo_sha256":sha(PHOTO),
        "seconds":60,"french_voice_retiming":False,"timeline":SCENES,
        "chunk_audio_sha256":[sha(RUN/f"speech_{i}.wav") for i in range(N)],
        "third_party_source_publication_authorized":False
    })
    print("PREPARED_5_X_12S_EXACT_FRENCH_AUDIO",flush=True)

def normalize_video(raw,out):
    # Content is rendered slightly beyond 12s by LTX 8k+1 frame grid.
    cmd(["ffmpeg","-y","-v","error","-i",raw,
         "-vf","fps=25,scale=1920:1080:force_original_aspect_ratio=increase,"
               "crop=1920:1080,setsar=1,"
               "tpad=stop_mode=clone:stop_duration=0.12,"
               "trim=duration=12,setpts=PTS-STARTPTS,format=yuv420p",
         "-frames:v","300","-an","-c:v","libx264","-preset","veryfast",
         "-crf","18","-pix_fmt","yuv420p",out],timeout=360)
    m=meta(out);v=next(x for x in m["streams"] if x["codec_type"]=="video")
    if abs(float(m["format"]["duration"])-12)>.04 or int(v["nb_frames"])!=300:
        raise RuntimeError("12s normalized clip must contain 300 frames")
    return m

def animate():
    check_workspace()
    if not (RUN/"prepared.json").is_file():raise RuntimeError("No preflight")
    import modal
    from deploy import modal_ltx_worker as ltx
    encoded=base64.b64encode(PHOTO.read_bytes()).decode("ascii")
    receipt=RUN/"animations.json"
    state={"status":"running","engine":"LTX-2.5","partitions":[],
           "single_approved_reference_sha256":sha(PHOTO),"generator_source_video":None}
    save(receipt,state)
    with ltx.app.run(name="ugcv2-fr60-newpresenter-five-distinct-12s",environment_name="main"):
        for i in range(N):
            payload={
                "prompt":PROMPT,"duration_s":12,"aspect_ratio":"16:9",
                "seed":2026103020+i,"audio_mode":"silent",
                "image_strength":1.0,"image_png_base64":encoded,
                "trace_id":f"fr60-full-approved-presenter-{i}-20261030"}
            ltx.validate(payload)
            print("LTX_12S_BEGIN",i,flush=True)
            result=ltx.render_clip.remote(payload)
            if result["metadata"].get("continuity_mode")!="image":raise RuntimeError("LTX did not use reference")
            raw=base64.b64decode(result["video_base64"],validate=True)
            file=RUN/f"ltx_{i}.mp4"
            file.write_bytes(raw)
            if "sha256" in result["metadata"] and sha(file)!=result["metadata"]["sha256"]:
                raise RuntimeError("LTX SHA mismatch")
            file_normal=RUN/f"actor_{i}.mp4"
            normalize_video(file,file_normal)
            state["partitions"].append({"index":i,"start_s":i*12,"end_s":(i+1)*12,
                  "ltx_sha256":sha(file),"actor_sha256":sha(file_normal),
                  "metadata":result["metadata"]})
            save(receipt,state)
            print("LTX_12S_COMPLETED",i,flush=True)
    state["status"]="all_five_animations_ready"
    save(receipt,state)

def dub():
    check_workspace()
    if not (RUN/"animations.json").exists():raise RuntimeError("No LTX receipts")
    anim=json.loads((RUN/"animations.json").read_text())
    if anim["status"]!="all_five_animations_ready" or len(anim["partitions"])!=5:
        raise RuntimeError("Cannot dub missing distinct LTX scenes")
    import modal
    from deploy import modal_tbdub_fr_worker as tbdub
    report={"status":"running","engine":"TBDub Student v1.1","partitions":[]}
    path=RUN/"dubbed.json"
    save(path,report)
    with tbdub.app.run(name="ugcv2-fr60-newpresenter-tbdub-5x12s",environment_name="main"):
        ready=tbdub.prepare_student_only.remote()
        if not ready.get("all_present"):raise RuntimeError("Student checkpoint missing")
        for i in range(N):
            video=RUN/f"actor_{i}.mp4"
            audio=RUN/f"speech_{i}.wav"
            if sha(video)!=anim["partitions"][i]["actor_sha256"]:
                raise RuntimeError("Actor SHA differs")
            print("TBDUB_12S_BEGIN",i,flush=True)
            result=tbdub.render_student_french_twelve_to_fifteen_seconds.remote(
                base64.b64encode(video.read_bytes()).decode(),
                base64.b64encode(audio.read_bytes()).decode())
            raw=base64.b64decode(result["video_base64"],validate=True)
            file=RUN/f"tbdub_{i}.mp4"
            file.write_bytes(raw)
            if sha(file)!=result["metadata"]["video_sha256"]:
                raise RuntimeError("Student result SHA differs")
            d=float(meta(file)["format"]["duration"])
            if abs(d-SECONDS)>.50:raise RuntimeError("TBDub 12s mismatch "+str(d))
            norm=RUN/f"dubbed_actor_{i}.mp4"
            normalize_video(file,norm)
            report["partitions"].append({
                "index":i,"start_s":i*12,"end_s":(i+1)*12,
                "student_sha256":sha(file),"normalized_sha256":sha(norm),
                "student_metadata":result["metadata"]})
            save(path,report)
            print("TBDUB_12S_COMPLETED",i,flush=True)
    report["status"]="all_five_dubbed_ready"
    save(path,report)

def times(k):
    return "+".join(f"between(t,{a:.2f},{b-.001:.3f})" for kind,a,b in SCENES if kind==k)

def assemble():
    validate_source()
    receipt=json.loads((RUN/"dubbed.json").read_text())
    if receipt["status"]!="all_five_dubbed_ready" or len(receipt["partitions"])!=N:
        raise RuntimeError("Cannot assemble unrendered 12s clips")
    actor_inputs=[]
    for i in range(N):
        clip=RUN/f"dubbed_actor_{i}.mp4"
        if sha(clip)!=receipt["partitions"][i]["normalized_sha256"]:
            raise RuntimeError("Mismatched actor master "+str(i))
        actor_inputs+=["-i",str(clip)]
    cat="".join(f"[{i+1}:v]" for i in range(N))+f"concat=n={N}:v=1:a=0,setsar=1,split=2[full][pipin]"
    full_intervals=times("full")+"+"+times("title")
    pip_intervals=times("pip")
    graph=";".join([
        cat,
        f"[0:v][full]overlay=0:0:format=auto:shortest=1:enable='{full_intervals}'[camera]",
        "[pipin]scale=492:444:force_original_aspect_ratio=increase,crop=492:444,setsar=1[pip]",
        f"[camera][pip]overlay=1428:0:format=auto:shortest=1:enable='{pip_intervals}'[composite]",
        # Rebuild a fully opaque title card: never retain a ghost of the source actor.
        # Keeps timing/text while the source's masked speaker cannot bleed through.
        "[composite]drawbox=x=0:y=0:w=iw:h=ih:color=white@0.92:t=fill:"
        "enable='between(t,12.000,14.239)',"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text=TRIGGER:fontcolor=black:fontsize=100:x=(w-text_w)/2:"
        "y=(h-text_h)/2:enable='between(t,12.000,14.239)'[final]"
    ])
    dest=RUN/"UGCv2_FR60_NOUVEL_ACTEUR_COMPLET_TEST.mp4"
    cmd(["ffmpeg","-y","-v","error","-i",SOURCE,*actor_inputs,
         "-filter_complex",graph,
         "-map","[final]","-map","0:a:0","-t","60",
         "-r","25","-c:v","libx264","-preset","veryfast","-crf","18",
         "-pix_fmt","yuv420p","-c:a","copy","-movflags","+faststart",dest],timeout=1500)
    m=meta(dest)
    v=next(x for x in m["streams"] if x["codec_type"]=="video")
    a=next(x for x in m["streams"] if x["codec_type"]=="audio")
    if (v["width"],v["height"],v["r_frame_rate"])!=(1920,1080,"25/1"):
        raise RuntimeError("Not a 1080p 25fps result")
    if abs(float(m["format"]["duration"])-60)>.08 or int(v["nb_frames"])!=1500:
        raise RuntimeError("60s final does not contain 1500 frames")
    if a["codec_name"]!="aac":raise RuntimeError("French audio missing")
    cmd(["ffmpeg","-v","error","-xerror","-i",dest,"-f","null","-"],timeout=420)
    for second in [2,7,12.5,14.7,18,22,27,30,35,42,48,55,58,59.9]:
        frame=RUN/(f"check_{str(second).replace('.','p')}.jpg")
        cmd(["ffmpeg","-y","-v","error","-ss",str(second),"-i",dest,
             "-frames:v","1","-q:v","3",frame],timeout=90)
    save(RUN/"final_status.json",{
        "stage":"REAL_60S_WITH_SAME_SYNTHETIC_ACTOR_GENERATED_REVIEW_REQUIRED",
        "video_sha256":sha(dest),"duration_s":float(m["format"]["duration"]),
        "size_bytes":dest.stat().st_size,"all_1500_frames_decoded":True,
        "reference_unchanged":sha(SOURCE)==VOICE_SHA_SOURCE,
        "french_audio_track":"bitstream copy of validated reference",
        "n_distinct_LTX_masters":N,"n_TBDub_12s_passes":N,
        "segmentation_used":False,"legacy_presenter_reused_for_generation":False,
        "pip_replaced_complete_rectangle":PIP,
        "timeline_source":SCENES,
        "title_section":"original text reconstructed on opaque overlay to remove source ghost",
        "visual_lipsync_quality":"HUMAN_REVIEW_REQUIRED",
        "publication_rights":"NOT VERIFIED",
    })
    print("FR60_NEW_ACTOR_REAL_MP4_60S_1500_FRAMES_DONE",dest,flush=True)

if __name__=="__main__":
    stage=sys.argv[1] if len(sys.argv)>1 else "prepare"
    {"prepare":prepare,"animate":animate,"dub":dub,"assemble":assemble}[stage]()
