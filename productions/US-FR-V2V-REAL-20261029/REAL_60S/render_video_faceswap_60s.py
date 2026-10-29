#!/usr/bin/env python3
"""Private 60s mixed-scene identity replacement using UGCv2's face worker.

Use the same artificial presenter from the approved 15s LTX V2V as reference.
The face swapper acts only where source footage already has a face; it does not
invent screen pixels, and does not use the broken EDTalk lip_syncer. TBDub
French lip synchronization is a separate, gated operation.

The reference video comes from GitHub run 40899629965, the exact 60s source
from 40942927735. No YouTube re-download or LTX V2V re-render.
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
BASE=Path("productions/US-FR-V2V-REAL-20261029/REAL_60S")
OUT=BASE/"FACE_SWAP"
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=BASE/"OUTPUT"/"source_window_60s.mp4"
REF=BASE/"EXISTING_V2V_15S"/"fr-v2v-raw-15s.mp4"
FACE=OUT/"UGCv2_presenter_reference_5s.jpg"
RAW=OUT/"faceswapped_raw_60s.mp4"
MUTED=OUT/"faceswapped_video_no_audio_60s.mp4"

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        while b:=f.read(1048576):h.update(b)
    return h.hexdigest()

def sh(cmd:list[str],timeout=180)->str:
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    if r.returncode:raise RuntimeError((r.stdout+r.stderr)[-4500:])
    return r.stdout

def probe(p:Path)->dict:
    return json.loads(sh(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(p)]))

def save(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def preflight():
    if not SOURCE.is_file() or not REF.is_file():
        raise RuntimeError("Missing authentic 60s source or approved 15s V2V actor reference")
    data=json.loads((BASE/"OUTPUT"/"source_provenance.json").read_text())
    if sha(SOURCE)!=data["source_window_sha256"]:
        raise RuntimeError("Original video SHA mismatch")
    refmeta=json.loads((BASE/"EXISTING_V2V_15S"/"render_receipt.json").read_text())
    if refmeta.get("status")!="V2V_TECHNICALLY_VERIFIED_VISUAL_REVIEW_PENDING":
        raise RuntimeError("Reference artificial actor was not a successful source-guided V2V")
    if sha(REF)!=refmeta.get("raw_sha256"):
        raise RuntimeError("Artificial presenter reference SHA mismatch")
    frames=probe(SOURCE)
    dur=float(frames["format"]["duration"])
    if not 59.8<dur<60.2:raise RuntimeError("Wrong 60s source")
    sh(["ffmpeg","-y","-v","error","-ss","5.0","-i",str(REF),
        "-frames:v","1","-q:v","3",str(FACE)])
    if FACE.stat().st_size<10_000:
        raise RuntimeError("Reference face not extracted")
    save("source_and_identity_provenance.json",{
        "original_60s_source_run":40942927735,
        "original_source_sha256":sha(SOURCE),
        "new_artificial_actor_from_V2V_run":40899629965,
        "approved_actor_reference_video_sha256":sha(REF),
        "face_jpeg_sha256":sha(FACE),
        "policy":"Private face replacement for technical evaluation only",
        "source_screen_pixels_policy":"Preserve all text and screen interaction pixels",
        "lip_sync_policy":"No EDTalk, TBDub French separately",
        "gpu_calls_to_date":0,
    })
    print("FACE_SWAP_ORIGINAL_AND_GENERATED_ACTOR_VERIFIED",flush=True)

def run():
    if os.getenv("STUDIO_MODAL_WORKSPACE")!="lucj76861" or os.getenv("SINGLE_FACE_GPU")!="YES":
        raise RuntimeError("Wrong GPU workspace or no one-time approval")
    if os.getenv("GITHUB_RUN_ATTEMPT","1")!="1":
        raise RuntimeError("GPU retries not authorized")
    if not (OUT/"source_and_identity_provenance.json").is_file():
        raise RuntimeError("CPU validation needed")
    import modal
    from deploy import modal_face_worker as worker
    save("status.json",{"stage":"FACEFUSION_ONE_GPU_STARTED","source":"true 60s","engine":"face_swapper"})
    try:
        with worker.app.run(name="ugc-60s-face-identity-pilot",environment_name="main"):
            result=worker.render_faceswap.remote(
                base64.b64encode(SOURCE.read_bytes()).decode(),
                base64.b64encode(FACE.read_bytes()).decode(),
                {"swapper":"inswapper_128_fp16","enhancer":"gfpgan_1.4"},
            )
        RAW.write_bytes(base64.b64decode(result["video_b64"],validate=True))
        save("face_swap_metadata.json",result["metadata"])
    except BaseException as exc:
        save("status.json",{"stage":"FACE_SWAP_GPU_FAILED",
                            "error":str(exc)[-5000:]})
        raise
    print("REAL_60S_FACE_SWAP_RENDERED",flush=True)

def inspect():
    if not RAW.is_file() or RAW.stat().st_size<1_000_000:
        raise RuntimeError("No actual face swap result")
    result=probe(RAW)
    fmt=result["format"]
    seconds=float(fmt["duration"])
    v=next((x for x in result["streams"] if x["codec_type"]=="video"),None)
    if not v or abs(seconds-60)>.35:
        raise RuntimeError(f"Invalid FaceFusion output duration {seconds}")
    # The face processor might change size; rescale only if necessary to the
    # verified source geometry without touching screen overlays separately.
    sh(["ffmpeg","-y","-v","error","-i",str(RAW),
        "-map","0:v:0","-an","-vf","fps=25,scale=1920:1080:flags=lanczos",
        "-c:v","libx264","-crf","18","-preset","fast",
        "-pix_fmt","yuv420p","-movflags","+faststart",str(MUTED)],timeout=480)
    sh(["ffmpeg","-v","error","-xerror","-i",str(MUTED),
        "-f","null","-"],timeout=300)
    if not 59.8<float(probe(MUTED)["format"]["duration"])<60.2:
        raise RuntimeError("Face-swap track not 60 seconds")
    for mark in (2,10,23,30,46,58):
        sh(["ffmpeg","-y","-v","error","-ss",str(mark),"-i",str(MUTED),
            "-frames:v","1",str(OUT/f"face_{mark:02d}s.jpg")],timeout=180)
    save("status.json",{
        "stage":"AUTHENTIC_60S_FACE_SWAP_MP4_CREATED_VISUAL_REVIEW_REQUIRED",
        "source_unchanged":True,
        "face_visual_quality":"NOT_HUMAN_VERIFIED",
        "face_video":str(MUTED),
        "video_sha256":sha(MUTED),
        "target_resolution":"1920x1080",
        "duration_s":float(probe(MUTED)["format"]["duration"]),
        "next":"TBDub lipsynchronization on actual face segments, then mux French mix",
    })
    print("FACE_SWAP_60S_VISUAL_QC_FILES_READY",flush=True)

if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "preflight"
    {"preflight":preflight,"run":run,"inspect":inspect}[mode]()
