#!/usr/bin/env python3
"""Produce a real 60-second private French-language preview with genuine UI pixels.

English source word timestamps from GitHub run 40944640728, actual screen video
from 40942927735, voice from Chatterbox Multilingual V3. No video GPUs here.
Do NOT speed up voice with atempo: use rewritten short translation and original
utterance start/end timing. Abort if no naturally fitting take exists.
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

sys.path.insert(0,str(Path.cwd()))
import numpy as np
import soundfile as sf

OUT=Path("productions/US-FR-V2V-REAL-20261029/REAL_60S/OUTPUT")
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=OUT/"source_window_60s.mp4"
ALIGN=OUT/"english_transcript_word_timings.json"
AUDIO=OUT/"fr_voice_original_cadence_60s.wav"
PREVIEW=OUT/"fr_60s_visuals_preserved_dub_preview.mp4"

BLOCKS=[
 {"id":"01_power","start_s":0.00,"end_s":6.04,
  "fr_text":"Ce qu'on peut faire avec Zapier, c'est vraiment puissant. Regardez : je clique ici sur Créer un Zap, et je lance..."},
 {"id":"02_always_on","start_s":6.04,"end_s":11.92,
  "fr_text":"une nouvelle automatisation qui fonctionne jour et nuit, et se déclenche dès que l'événement arrive."},
 {"id":"03_domino_trigger","start_s":12.12,"end_s":20.90,
  "fr_text":"Le premier concept à comprendre, c'est le déclencheur. Imaginez une rangée de dominos. Le déclencheur, c'est le premier domino. En tombant, il met tous les autres en mouvement."},
 {"id":"04_drop_a_file","start_s":21.18,"end_s":30.86,
  "fr_text":"Pour notre exemple, je choisis un de mes déclencheurs préférés, car il est vraiment universel. Chaque fois que je glisse un nouveau fichier dans un dossier de mon ordinateur, l'automatisation démarre aussitôt."},
 {"id":"05_dropbox_drive","start_s":31.18,"end_s":39.28,
  "fr_text":"Dans mon cas, je prends Dropbox, parce que je l'utilise au quotidien. Mais Google Drive marcherait aussi, comme les cinq mille autres applications qui se connectent à Zapier."},
 {"id":"06_local_folders","start_s":39.38,"end_s":48.30,
  "fr_text":"Dropbox est installé sur mon ordinateur, alors tous mes dossiers sont là, en local. J'ouvre AutoHub AI Advantage : c'est dans ce dossier que je gère plusieurs de mes automatisations."},
 {"id":"07_youtube_folders","start_s":48.42,"end_s":59.62,
  "fr_text":"Ici, je clique sur Nouveau dossier. Je vais l'appeler Test YouTube. C'est très simple : à l'intérieur, je crée deux sous-dossiers. Le premier s'appelle Zone de dépôt des e-mails, parce que c'est là qu'on va déposer tous les e-mails."},
]


def sh(cmd:list[str],timeout=180)->str:
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError((p.stdout+p.stderr)[-3000:])
    return p.stdout

def probe(p:Path)->dict:
    return json.loads(sh(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(p)]))

def report(name:str,data:dict):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def digest(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        while block:=f.read(1<<20):h.update(block)
    return h.hexdigest()

def preflight():
    if not SOURCE.is_file() or not ALIGN.is_file():
        raise RuntimeError("Verified 60s source or timed English transcript unavailable")
    source=json.loads((OUT/"source_provenance.json").read_text())
    if source["source_window_sha256"]!=digest(SOURCE) or source["window_start_s"]!=42:
        raise RuntimeError("60s source provenance mismatch")
    seconds=float(probe(SOURCE)["format"]["duration"])
    if abs(seconds-60)>.2:raise RuntimeError("Unexpected source duration")
    transcript=json.loads(ALIGN.read_text())
    original=transcript.get("segments",[])
    if not original or "trigger" not in " ".join(s["text"].lower() for s in original):
        raise RuntimeError("English transcription doesn't match trigger scene")
    if len(BLOCKS)!=7 or any(
        b["start_s"]>=b["end_s"] or b["end_s"]>60 or
        (i and b["start_s"] < BLOCKS[i-1]["end_s"])
        for i,b in enumerate(BLOCKS)):
        raise RuntimeError("Invalid source-synchronized French phrase windows")
    report("fr_voice_script_timed.json",{
        "source_window_s":[42,102],
        "original_transcript_artifact":40944640728,
        "translation":"French adapted to image actions and original utterance starts",
        "blocks":BLOCKS,
        "no_global_time_stretch":True,
        "no_presenter_voice_clone":True,
    })
    print("CPU_ORIGINAL_VIDEO_AND_ENGLISH_WORD_TIMINGS_VERIFIED",flush=True)

def voice():
    if os.environ.get("STUDIO_MODAL_WORKSPACE")!="lucj76861" or os.getenv("CONFIRM_V3_SINGLE_GPU")!="YES":
        raise RuntimeError("Modal GPU not authorized for single V3 session")
    if os.getenv("GITHUB_RUN_ATTEMPT","1")!="1":raise RuntimeError("Retry GPU blocked")
    if not (OUT/"fr_voice_script_timed.json").is_file():raise RuntimeError("CPU source proof absent")
    import modal
    from deploy import modal_chatterbox_v3_fr_pilot as worker
    try:
        with worker.app.run(name="ugc-60s-v3-seven-fr-blocks",environment_name="main"):
            output=worker.render_original_paced_french_blocks.remote(BLOCKS)
    except BaseException as exc:
        report("status.json",{"stage":"VOICE_GPU_FAILED","error":str(exc)[-3200:]})
        raise
    info=[]
    for block in output["blocks"]:
        candidates=[]
        for take in block["candidates"]:
            name=block["id"]+"_"+take["tag"]+".wav"
            p=OUT/name
            p.write_bytes(base64.b64decode(take["wav_b64"],validate=True))
            if digest(p)!=take["sha256"]:raise RuntimeError("Chatterbox audio checksum mismatch")
            candidates.append({k:v for k,v in take.items() if k!="wav_b64"}|{"file":name})
        info.append({k:v for k,v in block.items() if k!="candidates"}|{"candidates":candidates})
    report("fr_voice_candidate_durations.json",{
        "engine":output["engine"],"v3_explicit":output["v3_explicit"],
        "model_revision":output["model_revision"],
        "voice_identity":output["voice_identity"],"blocks":info,
        "gpu":output["gpu"],"gpu_seconds":output["render_seconds"],
        "status":"AUDIO_GENERATED_NOT_YET_QUALITY_REVIEWED",
    })
    print("REAL_FRENCH_V3_VOICE_BLOCKS_GENERATED",len(info),flush=True)

def mix():
    file=OUT/"fr_voice_candidate_durations.json"
    if not file.is_file():raise RuntimeError("French voice candidates not produced")
    data=json.loads(file.read_text())
    slots=data["blocks"]
    sr=48000
    samples=np.zeros(int(sr*60),dtype=np.float32)
    selected=[]
    for block in slots:
        target=float(block["end_s"])-float(block["start_s"])
        candidates=block["candidates"]
        eligible=[x for x in candidates if x["duration_s"]<=target-0.08]
        if not eligible:
            report("status.json",{
                "stage":"VOICE_TIMING_REWRITE_REQUIRED_NO_VIDEO_GPU",
                "bad_block":block["id"],"target_duration_s":target,
                "candidate_duration_s":[x["duration_s"] for x in candidates],
            })
            raise RuntimeError(f"Block {block['id']} too long; shorten French text instead of speeding voice")
        # Choose the unhurried/closest full take. Avoid a robotically fast take
        # followed by a very long silent gap.
        best=min(eligible,key=lambda x:(abs(target-.30-x["duration_s"]),x["tag"]!="unhurried"))
        if best["duration_s"]<target*.62:
            report("status.json",{
                "stage":"VOICE_TOO_FAST_REWRITE_REQUIRED_NO_VIDEO_GPU",
                "bad_block":block["id"],"target_duration_s":target,
                "selected_duration_s":best["duration_s"],
            })
            raise RuntimeError("Block insufficiently filled; use more French words or different voice settings")
        buf=OUT/best["file"]
        conv=OUT/(block["id"]+"_chosen_48k.wav")
        sh(["ffmpeg","-y","-v","error","-i",str(buf),"-ar",str(sr),"-ac","1",
            "-c:a","pcm_f32le",str(conv)])
        wave,read_sr=sf.read(str(conv),dtype="float32")
        if read_sr!=sr:raise RuntimeError("Sample rate mismatch")
        start=int(round(float(block["start_s"])*sr))
        end=min(len(samples),start+len(wave))
        audible=wave[:end-start]
        fade=min(420,len(audible)//5)
        if fade>0:
            audible[:fade]*=np.linspace(0,1,fade)
            audible[-fade:]*=np.linspace(1,0,fade)
        samples[start:end]+=audible
        selected.append({
            "id":block["id"],"start_s":block["start_s"],"end_s":block["end_s"],
            "source_speech_window_s":round(target,3),
            "natural_fr_speech_duration_s":round(len(wave)/sr,3),
            "end_pause_s":round(target-len(wave)/sr,3),
            "take":best["tag"],"file":best["file"],
            "fr_text":block["fr_text"],"audio_sha256":digest(buf),
        })
        print("FR_VOICE_BLOCK",block["id"],best["tag"],
              "duration",round(len(wave)/sr,3),"slot",round(target,3),flush=True)
    peak=float(np.max(np.abs(samples)))
    if peak<.005:raise RuntimeError("No real speech in French track")
    if peak>.95:samples*=.95/peak
    sf.write(str(AUDIO),samples,sr,subtype="PCM_16")
    if abs(float(probe(AUDIO)["format"]["duration"])-60)>.03:raise RuntimeError("French track not 60sec")
    report("fr_voice_selected_timeline.json",{
        "duration_s":60,
        "selected":selected,"voice_engine":"Chatterbox Multilingual V3",
        "all_blocks_no_time_stretch":True,
        "english_original_speech_cadence_source_run":40944640728,
        "human_listening_review_required":True,
    })
    (OUT/"fr_transcript_60s.txt").write_text("\n".join(
        f"[{b['start_s']:05.2f}–{b['end_s']:05.2f}] {b['fr_text']}"
        for b in selected)+"\n",encoding="utf-8")
    def fmt(sec:float)->str:
        m=int(sec//60);s=int(sec%60);ms=int(round((sec%1)*1000))
        return f"00:{m:02}:{s:02},{ms:03}"
    srt=[]
    for i,b in enumerate(selected,1):
        srt.extend([str(i),fmt(b["start_s"])+" --> "+fmt(b["end_s"]),b["fr_text"],""])
    (OUT/"fr_subtitles_60s.srt").write_text("\n".join(srt),encoding="utf-8")
    print("FRENCH_VOICE_60S_PRESERVED_ORIGINAL_PHRASE_STARTS",flush=True)

def preview():
    if not AUDIO.is_file():raise RuntimeError("No actual 60s French voice track")
    # Reuse 1920x1080 source pictures verbatim. No re-gen, no dropping UI text.
    sh(["ffmpeg","-y","-v","error","-i",str(SOURCE),"-i",str(AUDIO),
        "-map","0:v:0","-map","1:a:0","-c:v","copy",
        "-c:a","aac","-b:a","192k","-ar","48000","-t","60",
        "-movflags","+faststart",str(PREVIEW)],timeout=180)
    sh(["ffmpeg","-v","error","-xerror","-i",str(PREVIEW),
        "-f","null","-"],timeout=180)
    info=probe(PREVIEW)
    v=next(x for x in info["streams"] if x["codec_type"]=="video")
    a=next(x for x in info["streams"] if x["codec_type"]=="audio")
    if (v["width"],v["height"])!=(1920,1080) or abs(float(info["format"]["duration"])-60)>.2:
        raise RuntimeError("French dubbed private preview geometry/duration mismatch")
    report("status.json",{
        "stage":"REAL_60S_FR_VOICE_AND_ORIGINAL_VISUALS_READY",
        "preview":str(PREVIEW),
        "voice_sha256":digest(AUDIO),"preview_sha256":digest(PREVIEW),
        "duration":float(info["format"]["duration"]),
        "resolution":"1920x1080",
        "visuals":"source frames preserved, original presenter not yet replaced",
        "next_stage":"selectively replace presenter and PIP, TBDub only when mouth visible",
        "publish":False,"rights":"private technical experiment only",
    })
    print("FR_60S_NARRATION_PREVIEW_READY",PREVIEW,flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=["preflight","voice","mix","preview"])
    a=p.parse_args()
    {"preflight":preflight,"voice":voice,"mix":mix,"preview":preview}[a.stage]()
