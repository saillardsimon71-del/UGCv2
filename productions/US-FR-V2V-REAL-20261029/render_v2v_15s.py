#!/usr/bin/env python3
"""One 15-second real source-guided LTX-2.5 V2V transformation. No redeploy.
Creates *one* test MP4 from a 15-second video the user supplied by URL.
This does not modify UGCv2 or synthesize fake screen tutorials.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BASE=Path("productions/US-FR-V2V-REAL-20261029")
OUT=BASE/"OUTPUT"
REF=OUT/"reference-15s.mp4"
GUIDE=OUT/"guide-361-frames.mp4"
RAW=OUT/"fr-v2v-raw-15s.mp4"
FINAL=OUT/"fr-v2v-dubbed-15s.mp4"
REFERENCE_SHA="a7d0615ce1fde186c1e1bc169d378f6550c71b6111f92d376e088bce3cb98fc2"
SCRIPT_FR=(
    "Vous savez maintenant comment automatiser ChatGPT avec un déclencheur "
    "et quelques actions. Une fois le Zap configuré, il exécute cette tâche "
    "à votre place dès qu'un nouveau fichier arrive. Dans la prochaine vidéo, "
    "on découvrira d'autres automatisations pratiques."
)
PROMPT=(
    "Realistic medium close-up of a DIFFERENT French-speaking technology instructor, "
    "a newly created male presenter in his early thirties with medium brown curly hair, "
    "neatly trimmed full beard, medium complexion and round eyeglasses, wearing a "
    "dark teal casual blazer over a cream shirt. No white baseball cap, no black logo tee. "
    "He sits naturally at a wide wooden desk in a NEW BRIGHT modern minimalist "
    "French home-office with warm daylight, pale plaster walls, elegant bookshelves, "
    "green plants and a large window. He speaks directly to the camera and gestures "
    "with both hands in the same continuous positions and timings as the guide. "
    "One desk microphone on a small boom arm on the right, and a friendly, believable "
    "technology tutorial atmosphere. EXACTLY preserve the original source video's "
    "human performance: gesture timing, hand trajectories, body movement, expression "
    "changes, continuous medium shot, perspective and camera timing over the full "
    "fifteen seconds, but REFILM the actual scene with a wholly different actor, "
    "outfit, background, furniture and lighting. High realism, coherent face, "
    "natural anatomy, stable glasses, consistent hands and natural lip movement. "
    "No onscreen English text, no graphics, no subtitles, no jump cuts, no duplicated "
    "people, no flash, no abrupt appearance change, no distorted mouth, no frozen pose."
)
def sh(args,timeout=180):
    return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          check=True,text=True,timeout=timeout).stdout
def save(name,data):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def info(path,count=True):
    args=["ffprobe","-v","error"]
    if count: args+=["-count_frames"]
    args+=["-show_streams","-show_format","-of","json",str(path)]
    return json.loads(sh(args,timeout=90))
def verify_mp4(path,width,height,minframes):
    result=info(path)
    video=next(s for s in result["streams"] if s["codec_type"]=="video")
    if (int(video["width"]),int(video["height"]))!=(width,height):
        raise RuntimeError("Bad video output size")
    if int(video.get("nb_read_frames") or video.get("nb_frames") or 0)<minframes:
        raise RuntimeError("Bad video frame count")
    sh(["ffmpeg","-v","error","-xerror","-i",str(path),"-f","null","-"],timeout=150)
    return result
def prepare():
    if not REF.is_file():raise RuntimeError("Real source artifact not found; GPU blocked")
    if hashlib.sha256(REF.read_bytes()).hexdigest()!=REFERENCE_SHA:
        raise RuntimeError("Unexpected source video; GPU blocked")
    report=json.loads((OUT/"source_report.json").read_text())
    if report["source_url"]!="https://www.youtube.com/watch?v=KSOxkhWs2Ic" or abs(float(report["selected_start_s"])-460.24)>.15:
        raise RuntimeError("Wrong source or unapproved shot selection")
    verify_mp4(REF,1344,768,360)
    sh(["ffmpeg","-v","error","-y","-i",str(REF),
        "-vf","fps=24,tpad=stop_mode=clone:stop_duration=0.1,format=yuv420p",
        "-frames:v","361","-an","-c:v","libx264","-preset","veryfast","-crf","28",
        "-pix_fmt","yuv420p","-movflags","+faststart",str(GUIDE)],timeout=150)
    guide=verify_mp4(GUIDE,1344,768,361)
    if GUIDE.stat().st_size>22_000_000:
        raise RuntimeError("V2V guide too large")
    import modal
    from deploy import modal_ltx_worker as worker
    payload={"prompt":PROMPT,"duration_s":15,"aspect_ratio":"16:9",
             "seed":2026102966,"audio_mode":"silent",
             "video_mp4_base64":base64.b64encode(GUIDE.read_bytes()).decode(),
             "trace_id":"us-fr-15s-real-facecam-v2v-20261029"}
    request=worker.validate(payload)
    worker.probe_source_video(GUIDE,request)
    graph=worker.build_graph(request,output_prefix="usfr/15s/v2v",uploaded_video="driving.mp4")
    if graph.get("30",{}).get("class_type")!="VAEEncodeTiled" or graph.get("3",{}).get("class_type")!="LoadVideo":
        raise RuntimeError("V2V temporal source not actually used; GPU blocked")
    save("render_plan.json",{"status":"source_guide_verified_cpu",
        "source_url":report["source_url"],"source_window_start_s":report["selected_start_s"],
        "reference_sha256":REFERENCE_SHA,"guide_sha256":hashlib.sha256(GUIDE.read_bytes()).hexdigest(),
        "source_frames":360,"guide_frames":361,"duration_s":15,"aspect_ratio":"16:9",
        "prompt":PROMPT,"voice_fr_text":SCRIPT_FR,"one_gpu_call":True,
        "modal_workspace":"lucj76861","publish":False})
    print("Real source verified, genuine V2V graph and 361 frames validated, 0 GPU so far")

def french_audio():
    # Prefer Microsoft neural French voice; if unavailable, Piper local fallback.
    mp3=OUT/"french_voice.mp3"
    wav=OUT/"french_voice.wav"
    try:
        sh(["edge-tts","--voice","fr-FR-HenriNeural","--text",SCRIPT_FR,
            "--write-media",str(mp3)],timeout=85)
        if not mp3.is_file() or mp3.stat().st_size<5000:raise RuntimeError("Edge TTS empty")
        sh(["ffmpeg","-v","error","-y","-i",str(mp3),
            "-ar","48000","-ac","2",str(wav)],timeout=75)
        backend="edge_tts_fr_henri"
    except Exception as edge_error:
        model=OUT/"fr_FR-siwis-medium.onnx"
        url="https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx"
        import urllib.request
        for suffix,link in [("",url),(".json",url+".json")]:
            target=Path(str(model)+suffix)
            with urllib.request.urlopen(link,timeout=90) as src,target.open("wb") as sink:
                while True:
                    chunk=src.read(1024*1024)
                    if not chunk:break
                    sink.write(chunk)
        run=subprocess.run(["piper","--model",str(model), "--output_file",str(wav)],
                           input=SCRIPT_FR+"\n",capture_output=True,text=True,timeout=120)
        if run.returncode or not wav.is_file():raise RuntimeError("Both French TTS choices failed before GPU")
        backend="piper_fr_siwis"
    voice=info(wav,count=False)
    if not any(s["codec_type"]=="audio" for s in voice["streams"]):
        raise RuntimeError("French voice has no real audio")
    dur=float(voice["format"]["duration"])
    if not 5.0<dur<30.0:raise RuntimeError(f"French voice impossible duration {dur}")
    save("voice_report.json",{"status":"real_fr_voice_generated_cpu",
         "backend":backend,"duration_s":dur,"source_script":SCRIPT_FR,
         "voice_sha256":hashlib.sha256(wav.read_bytes()).hexdigest(),
         "quality":"LISTENING_REVIEW_REQUIRED"})
    print(f"Real French voice generated {dur:.2f}s with {backend} (CPU only)")

def render(confirm):
    if confirm!="oui" or os.getenv("GITHUB_RUN_ATTEMPT","1")!="1":
        raise RuntimeError("Only one authorized GPU call on first run")
    if not (OUT/"voice_report.json").exists() or not (OUT/"render_plan.json").exists():
        raise RuntimeError("CPU preflight and actual French voice required")
    plan=json.loads((OUT/"render_plan.json").read_text())
    if hashlib.sha256(GUIDE.read_bytes()).hexdigest()!=plan["guide_sha256"]:
        raise RuntimeError("Unverified V2V guide")
    if RAW.exists() or (OUT/"render_receipt.json").exists():
        raise RuntimeError("No duplicate GPU attempts")
    import modal
    from deploy import modal_ltx_worker as worker
    ws=modal.Workspace.from_context().hydrate().name
    if ws!="lucj76861":raise RuntimeError("Wrong Modal workspace; GPU blocked")
    payload={"prompt":PROMPT,"duration_s":15,"aspect_ratio":"16:9","seed":2026102966,
             "audio_mode":"silent","trace_id":"us-fr-15s-real-facecam-v2v-20261029",
             "video_mp4_base64":base64.b64encode(GUIDE.read_bytes()).decode()}
    worker.validate(payload)
    receipt={"status":"starting_one_gpu_attempt","workspace":ws,"source_sha256":plan["guide_sha256"],
             "attempts_allowed":1,"real_cost_usd":None,"publish":False}
    save("render_receipt.json",receipt)
    call=None; complete=False
    with worker.app.run(name="ugcv2-us-fr-real-v2v-pilot",environment_name="main"):
        try:
            call=worker.render_clip.spawn(payload)
            receipt.update(status="running",call_id=call.object_id)
            save("render_receipt.json",receipt)
            result=call.get(timeout=1500)
            complete=True
        except BaseException as err:
            receipt.update(status="failed",error=str(err)[:1600])
            raise
        finally:
            if call is not None and not complete:
                try:call.cancel(terminate_containers=True)
                except Exception:pass
            save("render_receipt.json",receipt)
    RAW.write_bytes(base64.b64decode(result["video_base64"],validate=True))
    meta=result.get("metadata",{})
    if meta.get("continuity_mode")!="video" or (meta.get("source_video") or {}).get("sha256")!=plan["guide_sha256"]:
        receipt.update(status="FAILED_PROVENANCE",metadata=meta)
        save("render_receipt.json",receipt)
        raise RuntimeError("LTX result not proven source-guided")
    verify_mp4(RAW,1344,768,361)
    receipt.update(status="V2V_TECHNICALLY_VERIFIED_VISUAL_REVIEW_PENDING",
                   metadata=meta,raw_sha256=hashlib.sha256(RAW.read_bytes()).hexdigest())
    save("render_receipt.json",receipt)
    print("True 15s source-guided LTX V2V output generated, aesthetic/lipsync NOT automatically verified")

def finish():
    if not RAW.is_file():raise RuntimeError("Missing real V2V MP4")
    receipt=json.loads((OUT/"render_receipt.json").read_text())
    if receipt.get("status")!="V2V_TECHNICALLY_VERIFIED_VISUAL_REVIEW_PENDING":
        raise RuntimeError("No verified V2V")
    wav=OUT/"french_voice.wav"
    vdur=float(info(wav,count=False)["format"]["duration"])
    speed=vdur/15.04
    if not .5<=speed<=2:raise RuntimeError("Voice timing abnormal")
    sh(["ffmpeg","-v","error","-y","-i",str(RAW),"-i",str(wav),
        "-filter_complex",f"[1:a]aresample=48000,atempo={speed:.5f},"
                          "apad,atrim=duration=15.0417,loudnorm=I=-16:TP=-1.5:LRA=11[a]",
        "-map","0:v:0","-map","[a]","-c:v","copy","-c:a","aac",
        "-b:a","192k","-ar","48000","-ac","2",
        "-movflags","+faststart",str(FINAL)],timeout=160)
    result=verify_mp4(FINAL,1344,768,361)
    if not any(s["codec_type"]=="audio" for s in result["streams"]):
        raise RuntimeError("No French dub in export")
    sh(["ffmpeg","-y","-v","error","-i",str(FINAL),
        "-vf","fps=1,scale=224:128,tile=5x3","-frames:v","1",
        str(OUT/"final-contact.jpg")])
    save("delivery_report.json",{"status":"VIDEO_TECHNICALLY_RENDERED_HUMAN_VISUAL_AND_LIPSYNC_REVIEW_PENDING",
         "source_clip_sha256":REFERENCE_SHA,"fr_voice_seconds_original":vdur,
         "re_timing_speed":speed,"output":str(FINAL),
         "fps":24,"format":"1344x768","frame_count":361,
         "notice":"LTX 2.5 V2V does not guarantee precise presenter identity, translated lips, or UI text."})
    print("Real transformed French-dubbed 15-second video ready for review")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=["prepare","voice","render","finish"])
    p.add_argument("--confirm-spend",default="non")
    a=p.parse_args()
    {"prepare":prepare,"voice":french_audio,
     "render":lambda:render(a.confirm_spend),"finish":finish}[a.stage]()
