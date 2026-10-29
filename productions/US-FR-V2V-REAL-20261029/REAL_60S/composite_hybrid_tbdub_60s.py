#!/usr/bin/env python3
"""UGCv2: authentic 60s French tutorial, screen-preserving, selective lip sync.

INPUTS ARE PREVIOUS GITHUB ACTIONS ARTIFACTS ONLY:
- Original 60s screen and cut structure: 40942927735
- New actor identity: one FaceFusion face_swapper pass on that source
- New French voice: Chatterbox V3, English-original phrase timing (no global stretch)
- TBDub V1.1 Student, selectively for actual visible full-size talking heads

No fake text, no invented UI, no LTX rerender, no additional voice generation.
Private research, not licensed for public distribution.
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
BASE=Path("productions/US-FR-V2V-REAL-20261029/REAL_60S")
OUT=BASE/"HYBRID_FINAL"
FACE=BASE/"FACE_SWAP"/"faceswapped_video_no_audio_60s.mp4"
FRVOICE=BASE/"OUTPUT"/"fr_voice_original_cadence_60s.wav"
PREVIEW=BASE/"OUTPUT"/"fr_60s_visuals_preserved_dub_preview.mp4"
OUT.mkdir(parents=True,exist_ok=True)
SHOTS=[
    {"id":"cam_a","start_s":5.76,"end_s":12.00},
    {"id":"cam_b","start_s":21.12,"end_s":26.88},
    {"id":"cam_c_short","start_s":29.76,"end_s":31.20},
    {"id":"cam_d","start_s":56.56,"end_s":60.00},
]


def sh(cmd:list[str],timeout=240):
    result=subprocess.run(cmd,check=False,capture_output=True,text=True,timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr+result.stdout)[-3300:])
    return result.stdout


def probe(path:Path):
    return json.loads(sh(["ffprobe","-v","error","-show_streams","-show_format",
                          "-of","json",str(path)]))


def duration(path:Path)->float:
    return float(probe(path)["format"]["duration"])


def sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while chunk:=f.read(1<<20):h.update(chunk)
    return h.hexdigest()


def save(filename:str,obj):
    (OUT/filename).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def preflight():
    if not FACE.is_file() or not FRVOICE.is_file() or not PREVIEW.is_file():
        raise RuntimeError("Missing real face-swapped 60s or French V3 audio source artifact")
    f=json.loads((BASE/"FACE_SWAP"/"status.json").read_text())
    s=json.loads((BASE/"OUTPUT"/"status.json").read_text())
    voice=json.loads((BASE/"OUTPUT"/"fr_voice_selected_timeline.json").read_text())
    if f.get("stage")!="AUTHENTIC_60S_FACE_SWAP_MP4_CREATED_VISUAL_REVIEW_REQUIRED":
        raise RuntimeError("No successful 60s face replacement; do not simulate")
    if s.get("stage")!="REAL_60S_FR_VOICE_AND_ORIGINAL_VISUALS_READY":
        raise RuntimeError("60s French voice source not ready")
    if sha(FACE)!=f["video_sha256"] or sha(FRVOICE)!=s["voice_sha256"]:
        raise RuntimeError("Face track or audio hash differs from successful source artifact")
    if abs(duration(FACE)-60)>.2 or abs(duration(FRVOICE)-60)>.2:
        raise RuntimeError("Expected exactly 60s face and French voice")
    if len(voice.get("selected",[]))!=7:
        raise RuntimeError("Seven source-timed French phrases not verified")
    if not voice.get("all_blocks_no_time_stretch"):
        raise RuntimeError("Incorrect French dubbing speed policy")
    # Cut only the identified full-screen face shots; all remaining pixels remain
    # the same as the original 60s screen and FaceFusion source.
    for shot in SHOTS:
        d=round(shot["end_s"]-shot["start_s"],3)
        inp=OUT/(shot["id"]+"_source_face.mp4")
        audi=OUT/(shot["id"]+"_speech_fr_16k.wav")
        sh(["ffmpeg","-y","-v","error","-ss",str(shot["start_s"]),
            "-i",str(FACE),"-t",str(d),"-map","0:v:0",
            "-vf","fps=25,format=yuv420p","-an",
            "-c:v","libx264","-crf","18","-preset","fast",
            "-movflags","+faststart",str(inp)])
        sh(["ffmpeg","-y","-v","error","-ss",str(shot["start_s"]),
            "-i",str(FRVOICE),"-t",str(d),
            "-af",f"apad,atrim=duration={d}",
            "-ar","16000","-ac","1","-c:a","pcm_s16le",str(audi)])
        if abs(duration(inp)-d)>.12 or abs(duration(audi)-d)>.12:
            raise RuntimeError(f"{shot['id']} original and French speech timing mismatch")
    save("source_provenance.json",{
        "verified_full_source":40942927735,
        "verified_face_swap_artifact_sha256":sha(FACE),
        "original_paced_french_voice_sha256":sha(FRVOICE),
        "original_source_cuts":SHOTS,
        "number_of_targeted_face_shots":len(SHOTS),
        "all_other_screen_frames_untouched_by_generators":True,
        "original_V2V_engine_changed":False,
        "lip_sync_engine":"TBDub Student v1.1",
        "publication_permitted":False,
    })
    print("TBDUB_60S_ACTUAL_FACE_SHOTS_AND_FRENCH_AUDIO_PREPARED_CPU",flush=True)


def lips():
    if os.getenv("STUDIO_MODAL_WORKSPACE")!="lucj76861" or os.getenv("ALLOW_ONE_LIPS_GPU")!="YES":
        raise RuntimeError("Wrong GPU workspace or unauthorized GPU")
    if os.getenv("GITHUB_RUN_ATTEMPT","1")!="1":
        raise RuntimeError("No automatic GPU reruns")
    if not (OUT/"source_provenance.json").is_file():
        raise RuntimeError("No validated 60s full video and exact French audio")
    import modal
    from deploy import modal_tbdub_fr_worker as tbdub
    inputs=[]
    for shot in SHOTS:
        video=OUT/(shot["id"]+"_source_face.mp4")
        audio=OUT/(shot["id"]+"_speech_fr_16k.wav")
        inputs.append({
            "id":shot["id"],"start_s":shot["start_s"],
            "end_s":shot["end_s"],"duration_s":round(shot["end_s"]-shot["start_s"],3),
            "video_base64":base64.b64encode(video.read_bytes()).decode(),
            "audio_base64":base64.b64encode(audio.read_bytes()).decode(),
        })
    save("status.json",{"stage":"TBDUB_FR60_FOUR_SHOTS_STARTED","gpu":"L40S"})
    try:
        with tbdub.app.run(name="ugcv2-fr60-four-visible-face-shots",environment_name="main"):
            ready=tbdub.prepare_student_only.remote()
            if not ready.get("all_present"):
                raise RuntimeError("TBDub pretrained cached model incomplete")
            result=tbdub.dub_real_visible_face_shots.remote(inputs)
    except BaseException as exc:
        save("status.json",{"stage":"TBDUB_FR60_GPU_FAILED",
                            "error":str(exc)[-4200:]})
        raise
    metadata=[]
    for clip in result["results"]:
        name=clip["id"]
        record={k:v for k,v in clip.items() if k!="video_base64"}
        if clip["status"]=="real_tbdub_mp4":
            file=OUT/(name+"_tbdub_french.mp4")
            file.write_bytes(base64.b64decode(clip["video_base64"],validate=True))
            if sha(file)!=clip["sha256"]:
                raise RuntimeError(f"{name} generated MP4 SHA mismatch")
            record["filename"]=file.name
        metadata.append(record)
    save("tbdub_result.json",{
        "engine":result["engine"],
        "gpu_wall_seconds":result["gpu_wall_seconds"],
        "samples":metadata,
        "screens_changed":False,
        "human_visual_review_required":True,
    })
    if any(m["status"]!="real_tbdub_mp4" for m in metadata if m["id"]!="cam_c_short"):
        raise RuntimeError("One of three long face shots did not receive actual TBDub lip sync")
    print("TBDUB_FR60_VISIBLE_FACE_SHOTS_GENERATED",flush=True)


def assemble():
    rd=OUT/"tbdub_result.json"
    if not rd.is_file():raise RuntimeError("No real lip-synced face clips")
    clips=json.loads(rd.read_text())["samples"]
    done=[]
    for shot in SHOTS:
        rec=next((x for x in clips if x["id"]==shot["id"]),None)
        if not rec or rec["status"]!="real_tbdub_mp4":
            if shot["id"]!="cam_c_short":
                raise RuntimeError(f"No actual TBDub result for required {shot['id']}")
            continue
        # Reconcile only <0.5 seconds of potentially padded model output.
        # Do not change original whole minute or French spoken cadence.
        src=OUT/rec["filename"]
        d=round(shot["end_s"]-shot["start_s"],3)
        normalized=OUT/(shot["id"]+"_overlaid_25fps.mp4")
        sh(["ffmpeg","-y","-v","error","-i",str(src),
            "-vf",f"fps=25,scale=1920:1080:flags=lanczos,"
                  f"tpad=stop_mode=clone:stop_duration=0.6,trim=duration={d},"
                  f"setpts=PTS-STARTPTS,format=yuv420p",
            "-an","-t",str(d),"-c:v","libx264","-crf","18","-preset","fast",
            str(normalized)],timeout=240)
        if abs(duration(normalized)-d)>.12:
            raise RuntimeError(f"{shot['id']} failed exact video duration alignment")
        done.append((shot,normalized))
    if len(done)<3:raise RuntimeError("Insufficient actual lip-synced human shots")

    final=OUT/"UGCv2_FR_60s_TBDub_HYBRID_TEST.mp4"
    inputs=["-i",str(FACE)]
    for shot,p in done:inputs.extend(["-i",str(p)])
    inputs.extend(["-i",str(FRVOICE)])
    graph=[]
    prior="[0:v]"
    for i,(shot,p) in enumerate(done,1):
        start=shot["start_s"];end=shot["end_s"]
        clip=f"[seg{i}]";result=f"[m{i}]"
        graph.append(f"[{i}:v]setpts=PTS-STARTPTS+{start}/TB,format=yuv420p{clip}")
        graph.append(f"{prior}{clip}overlay=0:0:format=auto:eof_action=pass:"
                     f"repeatlast=0:enable='gte(t,{start})*lt(t,{end})'{result}")
        prior=result
    sh(["ffmpeg","-y","-v","error"]+inputs+[
        "-filter_complex",";".join(graph),
        "-map",prior,
        "-map",f"{len(done)+1}:a:0","-t","60",
        "-r","25","-c:v","libx264","-crf","18","-preset","fast",
        "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k",
        "-ar","48000","-movflags","+faststart",str(final)],timeout=900)
    sh(["ffmpeg","-v","error","-xerror","-i",str(final),
        "-f","null","-"],timeout=300)
    meta=probe(final)
    t=float(meta["format"]["duration"])
    video=next(x for x in meta["streams"] if x["codec_type"]=="video")
    audio=next(x for x in meta["streams"] if x["codec_type"]=="audio")
    if abs(t-60)>.15 or (video["width"],video["height"])!=(1920,1080):
        raise RuntimeError("Final video missing real 60s 1080p")
    # Separate compressed side-by-side 60s comparison for review.
    comp=OUT/"UGCv2_FR60_COMPARE_ORIGINAL_VS_HYBRID.mp4"
    sh(["ffmpeg","-y","-v","error","-i",str(PREVIEW),"-i",str(final),
        "-filter_complex",
        "[0:v]fps=25,scale=640:360[a];[1:v]fps=25,scale=640:360[b];"
        "[a][b]hstack=inputs=2[v]",
        "-map","[v]","-map","1:a:0",
        "-t","60","-c:v","libx264","-crf","22","-preset","fast",
        "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
        "-movflags","+faststart",str(comp)],timeout=720)
    for mark in (7,22,30,45,58):
        sh(["ffmpeg","-y","-v","error","-ss",str(mark),"-i",str(final),
            "-frames:v","1",str(OUT/f"hybrid_at_{mark:02}.jpg")],timeout=90)
    save("status.json",{
        "stage":"ACTUAL_60S_FR_HYBRID_MP4_GENERATED_HUMAN_REVIEW_REQUIRED",
        "final":final.name,"comparison":comp.name,
        "duration_s":t,"width":1920,"height":1080,
        "final_sha256":sha(final),
        "lip_synced_fullscreen_shots":[x[0]["id"] for x in done],
        "short_shot_lipsync_status":next(
            (x["status"] for x in clips if x["id"]=="cam_c_short"),"unknown"),
        "pip_lipsync":"not selectively rendered — check visual side-by-side",
        "french_voice":"same 60s original-aligned Chatterbox V3 audio",
        "screen_diagrams_and_original_ui":"not regenerated",
        "rights":"Private technical study only; republishing third party video needs permission",
        "quality":"human review mandatory",
    })
    print("REAL_60S_HYBRID_VIDEO_READY",final,flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=["preflight","lips","assemble"])
    stage=parser.parse_args().stage
    {"preflight":preflight,"lips":lips,"assemble":assemble}[stage]()
