#!/usr/bin/env python3
"""Isolated 8s French-lipsync experiment on an EXISTING, verified LTX V2V pilot.
No second V2V render. No upload or publication. Never claim QC from mere success.
"""
from __future__ import annotations
import argparse, base64, hashlib, io, json, os, subprocess, sys, zipfile
from pathlib import Path
import requests

ROOT=Path("productions/US-FR-V2V-REAL-20261029/LIPSYNC_8S")
ROOT.mkdir(parents=True,exist_ok=True)
REPO=os.environ.get("GITHUB_REPOSITORY","saillardsimon71-del/UGCv2")
TOKEN=os.environ.get("GITHUB_TOKEN","")
TEXT="Une fois le Zap configuré, il exécute la tâche à votre place. Dès qu’un nouveau fichier arrive dans Dropbox, tout se déclenche automatiquement."
S=8.0
START=2.0
def save(name,obj):
    (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def sh(*cmd,timeout=180):
    return subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=timeout).stdout
def duration(p):
    return float(sh("ffprobe","-v","error","-show_entries","format=duration","-of","default=nk=1:nw=1",str(p)).strip())
def inspect(p):
    raw=sh("ffprobe","-v","error","-show_entries","stream=codec_type,codec_name,width,height","-show_entries","format=duration,size","-of","json",str(p))
    return json.loads(raw)
def api(path,bytes_=False):
    r=requests.get("https://api.github.com"+path,headers={"Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"},timeout=75)
    r.raise_for_status()
    return r.content if bytes_ else r.json()
def find_original():
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN missing, cannot discover previously generated V2V")
    runs=api("/repos/"+REPO+"/actions/workflows/us-fr-v2v-real-15s.yml/runs?branch=production%2Fus-fr-v2v-real-video-pilot-20261029&per_page=30")["workflow_runs"]
    for run in runs:
        arts=api("/repos/"+REPO+"/actions/runs/"+str(run["id"])+"/artifacts")["artifacts"]
        for art in arts:
            if art.get("expired") or not art["name"].startswith("US-FR-REAL-V2V-15S-"):
                continue
            try:
                archive=zipfile.ZipFile(io.BytesIO(api("/repos/"+REPO+"/actions/artifacts/"+str(art["id"])+"/zip",True)))
                names=archive.namelist()
                finals=[n for n in names if n.endswith("fr-v2v-dubbed-15s.mp4")]
                if not finals:continue
                src=archive.read(finals[0])
                if len(src)<100_000:continue
                (ROOT/"pilot_original_15s.mp4").write_bytes(src)
                meta={"run_id":run["id"],"artifact_id":art["id"],"name":art["name"],"sha256":hashlib.sha256(src).hexdigest()}
                save("source_provenance.json",meta)
                return meta
            except Exception as exc:
                print("Skipping inaccessible artifact",art["id"],repr(exc)[:200],flush=True)
    raise RuntimeError("No authentic existing finished 15s V2V artifact found; refusing to fake or regenerate it")
def prepare():
    meta=find_original()
    orig=ROOT/"pilot_original_15s.mp4"
    if duration(orig)<START+S-0.1:
        raise RuntimeError("The V2V source is shorter than required")
    clip=ROOT/"baseline_french_8s.mp4"
    sh("ffmpeg","-y","-v","error","-ss",str(START),"-i",str(orig),"-t",str(S),
       "-map","0:v:0","-map","0:a:0","-vf","fps=24,format=yuv420p",
       "-c:v","libx264","-crf","19","-preset","fast","-c:a","aac","-ar","48000",
       "-movflags","+faststart",str(clip),timeout=180)
    sh("ffmpeg","-y","-v","error","-i",str(clip),"-vn","-ar","48000","-ac","1",
       str(ROOT/"baseline_audio.wav"))
    assert abs(duration(clip)-8)<.18
    save("baseline.json",{"source":meta,"seconds":duration(clip),"start_s":START,"note":"Existing V2V preserved without regeneration"})
    print("BASELINE_READY",meta,flush=True)
def voice():
    # Try a different, expressive French neural voice first. This is a controlled A/B,
    # NOT a claim that a particular voice sounds better without listening.
    out=ROOT/"french_candidate.mp3"
    import edge_tts, asyncio
    wav=ROOT/"french_candidate_raw.wav"
    failure=None
    try:
        async def generate():
            comm=edge_tts.Communicate(TEXT,voice="fr-FR-RemyMultilingualNeural",rate="-2%",pitch="-1Hz")
            await comm.save(str(out))
        asyncio.run(generate())
        sh("ffmpeg","-y","-v","error","-i",str(out),"-ar","48000","-ac","1",str(wav))
        d=duration(wav)
    except Exception as exc:
        failure=str(exc)[:250]
        d=0.0
    ratio=d/S
    if not .80<=ratio<=1.25:
        # Do not force absurd prosody; use current French dub instead.
        voice_source=ROOT/"baseline_audio.wav"
        used="original_fr_voice_fallback"
    else:
        voice_source=wav
        used="remy_multilingual_neural"
    outwav=ROOT/"final_french_voice.wav"
    if used=="original_fr_voice_fallback":
        sh("ffmpeg","-y","-v","error","-i",str(voice_source),"-t","8",
           "-ar","48000","-ac","1",str(outwav))
    else:
        sh("ffmpeg","-y","-v","error","-i",str(voice_source),
           "-af",f"atempo={ratio:.5f},apad,atrim=duration=8",
           "-ar","48000","-ac","1",str(outwav))
    save("voice_comparison.json",{"candidate":"fr-FR-RemyMultilingualNeural",
         "script":TEXT,"raw_duration_s":d,"selection":used,
         "final_duration_s":duration(outwav),"human_listening":"REQUIRED","candidate_error":failure,
         "warning":"Voix candidate and lip timing are not quality-verified by automated tests"})
    print("VOICE_READY",used,d,flush=True)
def lipsync():
    # Existing lip-sync worker, not LongCat: LongCat generates a new sequence and
    # would destroy the precisely preserved camera/actions of the V2V pilot.
    import modal
    from deploy import modal_lipsync_worker as worker
    vid=ROOT/"baseline_french_8s.mp4"
    wav=ROOT/"final_french_voice.wav"
    if not vid.exists() or not wav.exists():raise RuntimeError("Missing original or FR voice")
    if os.environ.get("STUDIO_MODAL_WORKSPACE")!="lucj76861":
        raise RuntimeError("Unapproved Modal workspace; GPU forbidden")
    # Check existing volume before building the large lip-sync image at all.
    # One 8-second test should not trigger 14+ GB of surprise downloads.
    state={"latentsync16_ready":False,"musetalk15_ready":False}
    try:
        v=modal.Volume.from_name("ugc-lipsync-models",create_if_missing=False)
        for label,folder,target in [
            ("latentsync16_ready","/latentsync","latentsync_unet.pt"),
            ("musetalk15_ready","/musetalk/musetalkV15","unet.pth")]:
            try:
                state[label]=any(e.path.rstrip("/").endswith(target) for e in v.listdir(folder))
            except Exception as exc:
                state[label+"_probe"]=str(exc)[:150]
    except Exception as exc:
        state["volume_probe"]=str(exc)[:200]
    save("model_doctor.json",state)
    model=("latentsync16" if state.get("latentsync16_ready") else
           "musetalk15" if state.get("musetalk15_ready") else None)
    if model is None:
        save("render_status.json",{"status":"BLOCKED_MODEL_WEIGHTS_NOT_READY",
            "gpu_calls":0,"model_doctor":state,
            "next":"Prepare existing lip-sync model weights before GPU rendering"})
        print("LIPSYNC_BLOCKED: weights missing, no image build or GPU",flush=True)
        return
    with worker.app.run(name="ugcv2-fr-lipsync-eight-second-test",environment_name="main"):
        if os.getenv("CONFIRM_ONE_LIPSYNC_GPU")!="YES":
            raise RuntimeError("One-GPU-call authorization missing")
        result=worker.render_lipsync.remote(
            base64.b64encode(vid.read_bytes()).decode(),
            base64.b64encode(wav.read_bytes()).decode(),
            {"model":model,"steps":20,"guidance_scale":1.5}
        )
        candidate=ROOT/"fr_lipsync_8s.mp4"
        candidate.write_bytes(base64.b64decode(result["video_b64"],validate=True))
        info=inspect(candidate)
        if not any(s["codec_type"]=="video" for s in info["streams"]):
            raise RuntimeError("Lip-syncer returned no video stream")
        if not 7.7<float(info["format"]["duration"])<8.4:
            raise RuntimeError("Lip-syncer returned inconsistent duration")
        # Do not trust the engine's audio mux; explicitly mux the exact lip driving voice.
        tmp=ROOT/"lipsync_muxed.mp4"
        sh("ffmpeg","-y","-v","error","-i",str(candidate),
           "-i",str(wav),"-map","0:v:0","-map","1:a:0",
           "-c:v","copy","-c:a","aac","-b:a","192k","-t","8",
           "-movflags","+faststart",str(tmp))
        tmp.replace(candidate)
        sh("ffmpeg","-v","error","-xerror","-i",str(candidate),"-f","null","-",timeout=180)
        save("render_status.json",{"status":"TECHNICALLY_RENDERED_VISUAL_REVIEW_REQUIRED",
             "model":model,"metadata":result.get("metadata",{}),"video":str(candidate),
             "quality_claim":"None. Human review of lips/face/natural voice required."})
        print("LIPSYNC_VIDEO_RENDERED",model,flush=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("phase",choices=["prepare","voice","lipsync"])
    a=p.parse_args()
    {"prepare":prepare,"voice":voice,"lipsync":lipsync}[a.phase]()
if __name__=="__main__":main()
