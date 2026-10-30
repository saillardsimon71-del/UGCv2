#!/usr/bin/env python3
"""One 20s, source-timed FR pilot; Work-proven 4s LTX + TBDub recipe.
No 12s generations, no 4s looping, no original actor in full/PiP shots.
This is a private technology test using a third-party source, not for publication.
"""
from __future__ import annotations
import base64, hashlib, json, os, subprocess, sys, wave
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PHOTO=ROOT/"productions/FR60-PRESENTER-PROOF-20261030/ASSETS/presenter-studio.png"
WORK_ANCHOR=ROOT/"productions/FR60-CONTINUITY-8S-20261030/ASSETS/anchor-native.png"
RECIPE=ROOT/"productions/FR60-CONTINUITY-8S-20261030/recipe.json"
SOURCE=HERE/"INPUT/UGCv2_FR_60s_TBDub_HYBRID_TEST.mp4"
OUT=HERE/"RESULT"
OUT.mkdir(exist_ok=True,parents=True)
SOURCE_SHA="346b8a25aa0722094f57e51aef3d41a97e1966f7ad1d04c4517c8fbbe5b7297d"
PHOTO_SHA="bd5ce8b0b67fd7cae6f197fc4608e7dff8b78882c162aba54c9e177d6e37bea3"
ANCHOR_SHA="0cf4ba4de58f5f7b95b7c139026f801e8bdf01b665dac0988b4be0160b5df4e7"
WORK_FIRST_NATIVE_SHA="8ed4ba8dd5822dfd33bd366699f87a75e7bc59a81fe60da2c833894f8fc47c1b"
WORK_SECOND_NATIVE_SHA="fc6460af2dfa82e5433442b215a0c611c0bbf33fa50eacb12ba9c0e911fb3084"
SEED=2026103017
CHUNKS=[7.60,11.60,21.08,25.08]    # 4.0 seconds each, no 12s
EXPECTED_WORKSPACE="lucj76861"
OUTPUT_NAME="UGCv2_FR20_CONTINUITE_TEST_GITHUB.mp4"
# 7.60..29.08 (21.48s) minus previous Work audio+frame cut of 1.48s = 20.00s.
ORIGINAL_BEGIN=7.60
ORIGINAL_END=29.08
REMOVED_FRAMES=(73,110)
REMOVED_PCM=(140160,211200)
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
    with Path(p).open("rb") as stream:
        while data:=stream.read(1<<20):h.update(data)
    return h.hexdigest()

def run(args,timeout=300):
    p=subprocess.run([str(x) for x in args],text=True,capture_output=True,timeout=timeout)
    if p.returncode:raise RuntimeError(f"Command error {p.returncode}: {p.stderr[-5000:]}")
    return p.stdout

def info(p):
    return json.loads(run(["ffprobe","-v","error","-show_format","-show_streams","-of","json",p]))

def record(filename,data):
    (OUT/filename).write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")

def validate():
    for p,s in [(SOURCE,SOURCE_SHA),(PHOTO,PHOTO_SHA),(WORK_ANCHOR,ANCHOR_SHA)]:
        if not p.exists() or sha(p)!=s:raise RuntimeError(f"Reference missing or changed: {p}")
    recipe=json.loads(RECIPE.read_text())
    if recipe["ltx_seed"]!=SEED or recipe["duration_request_s"]!=4 or recipe["prompt"]!=PROMPT:
        raise RuntimeError("4-second Work recipe changed")
    m=info(SOURCE)
    v=next(x for x in m["streams"] if x["codec_type"]=="video")
    assert (v["width"],v["height"],v["r_frame_rate"])==(1920,1080,"25/1")
    assert abs(float(m["format"]["duration"])-60)<.1
    return recipe

def gpu_guard():
    if not os.getenv("MODAL_TOKEN_ID") or not os.getenv("MODAL_TOKEN_SECRET"):
        raise RuntimeError("Missing GitHub Modal secrets")
    if os.getenv("STUDIO_MODAL_WORKSPACE")!=EXPECTED_WORKSPACE:
        raise RuntimeError("Unexpected Modal workspace")
    if os.getenv("ALLOW_FR20_GPU")!="YES" or os.getenv("GITHUB_RUN_ATTEMPT","1")!="1":
        raise RuntimeError("GPU not authorized / no retry")

def prepare():
    recipe=validate()
    for i,start in enumerate(CHUNKS):
        run(["ffmpeg","-y","-nostdin","-v","error","-ss",start,"-i",SOURCE,"-t",4,
             "-map","0:a:0","-ac","1","-ar","16000","-c:a","pcm_s16le",OUT/f"speech{i}.wav"])
        if abs(float(info(OUT/f"speech{i}.wav")["format"]["duration"])-4)>.01:
            raise RuntimeError("Four-second audio mismatch")
    audio=OUT/"audio_21p48.wav"
    run(["ffmpeg","-y","-nostdin","-v","error","-ss",ORIGINAL_BEGIN,"-i",SOURCE,
         "-t","21.48","-map","0:a:0","-ac","2","-ar","48000","-c:a","pcm_s16le",audio])
    with wave.open(str(audio),"rb") as w:
        if w.getframerate()!=48000 or w.getnframes()!=1031040:
            raise RuntimeError("Unexpected source audio samples")
        w.setpos(REMOVED_PCM[0]);chunk=w.readframes(REMOVED_PCM[1]-REMOVED_PCM[0])
    import array,math
    samples=array.array('h');samples.frombytes(chunk)
    peak=max(abs(v) for v in samples)
    db=20*math.log10(max(peak/32768,1e-12))
    if db>-70:raise RuntimeError(f"Cut would remove speech peak={db:.1f}dB")
    record("plan.json",{
        "status":"PREPARED","original_french_sha":sha(SOURCE),"actor_photo_sha":sha(PHOTO),
        "validated_work_anchor_sha":sha(WORK_ANCHOR),"input_original_source_range":[7.6,29.08],
        "exact_silence_cut_original_local":[2.92,4.40],"removed_frames":37,
        "removed_audio_peak_dbfs":round(db,2),"expected_output_duration":20.0,
        "lipsync_clip_ranges":[[x,x+4] for x in CHUNKS],
        "scene_timeline":[
            ["full",7.60,12.00],["title",12.00,14.24],["pip",14.24,15.56],
            ["screen",15.56,21.08],["full",21.08,26.80],["screen",26.80,29.08]
        ],
        "approved_seed":SEED,"new_models":False,"ltx_12s":False,
        "human_quality_review":"REQUIRED",
    })
    print("FR20_PREPARED_CUT_AUDIO_VERIFIED",flush=True)

def normalize_video(src,dst):
    run(["ffmpeg","-y","-nostdin","-v","error","-i",src,
         "-vf","fps=25,scale=1920:1080:force_original_aspect_ratio=increase,"
               "crop=1920:1080,setsar=1,format=yuv420p",
         "-frames:v","100","-an","-c:v","libx264","-crf","16","-preset","fast",dst],
        timeout=360)
    m=info(dst);v=next(x for x in m["streams"] if x["codec_type"]=="video")
    if v["r_frame_rate"]!="25/1" or int(v["nb_frames"])!=100:raise RuntimeError("Not exact 4s video")

def last_native_frame(video,into):
    # LTX output is 97 frames at 24fps. Frame 95 is Work's native overlap anchor.
    run(["ffmpeg","-y","-nostdin","-v","error","-i",video,
         "-vf","select=eq(n\\,95)","-frames:v","1",into],timeout=60)
    if not Path(into).is_file():raise RuntimeError("Missing anchor image")
    return sha(into)

def animate():
    gpu_guard();recipe=validate()
    if not (OUT/"plan.json").is_file():raise RuntimeError("Run prepare first")
    from deploy import modal_ltx_worker as ltx
    ledger={"status":"RUNNING","model":"LTX-2.5","seed":SEED,
            "prompt_sha":hashlib.sha256(PROMPT.encode()).hexdigest(),
            "approved_first_native_sha":WORK_FIRST_NATIVE_SHA,
            "approved_second_native_sha":WORK_SECOND_NATIVE_SHA,
            "attempts":[]}
    record("ltx_receipts.json",ledger)
    with ltx.app.run(name="ugcv2-fr20-verified-four-second-takes",environment_name="main"):
        for i in range(4):
            if i==0:ref=PHOTO
            elif i==1:
                # Anchor from a validated Work image if native master really reproduced;
                # otherwise anchor to our ACTUAL previous output and disclose divergence.
                ref=WORK_ANCHOR if ledger["attempts"][0]["matches_validated_raw"] else OUT/"anchor0.png"
            else:ref=OUT/f"anchor{i-1}.png"
            image_bytes=ref.read_bytes()
            payload={"prompt":PROMPT,"duration_s":4,"aspect_ratio":"16:9",
                     "seed":SEED,"audio_mode":"silent","image_strength":1.0,
                     "image_png_base64":base64.b64encode(image_bytes).decode("ascii"),
                     "trace_id":f"fr20-github-continuity-20261030-{i}"}
            ltx.validate(payload)
            print("LTX_4S_START",i,flush=True)
            res=ltx.render_clip.remote(payload)
            if res["metadata"].get("continuity_mode")!="image":
                raise RuntimeError("Not an image-conditioned LTX video")
            raw=OUT/f"ltx_native_{i}.mp4"
            raw.write_bytes(base64.b64decode(res["video_base64"],validate=True))
            good=WORK_FIRST_NATIVE_SHA if i==0 else WORK_SECOND_NATIVE_SHA if i==1 else None
            normalized=OUT/f"actor_pre_tbdub_{i}.mp4"
            normalize_video(raw,normalized)
            last_native_frame(raw,OUT/f"anchor{i}.png")
            rec={"i":i,"start":CHUNKS[i],"duration":4.0,
                 "reference_image_sha":sha(ref),"native_sha":sha(raw),
                 "matches_validated_raw":sha(raw)==good if good else None,
                 "normalized_sha":sha(normalized),"metadata":res["metadata"]}
            ledger["attempts"].append(rec);record("ltx_receipts.json",ledger)
            print("LTX_4S_DONE",i,"MATCHES_WORK" if rec["matches_validated_raw"] else "NEW_HASH",flush=True)
    ledger["status"]="FOUR_REAL_4S_LTX_READY"
    record("ltx_receipts.json",ledger)

def dub():
    gpu_guard();validate()
    ltx=json.loads((OUT/"ltx_receipts.json").read_text())
    if ltx["status"]!="FOUR_REAL_4S_LTX_READY":raise RuntimeError("Missing 4 LTX clips")
    from deploy import modal_tbdub_fr_worker as tb
    receipt={"status":"RUNNING","engine":"TBDub Student v1.1",
             "mode":"official four second function","attempts":[]}
    record("tbdub_receipts.json",receipt)
    with tb.app.run(name="ugcv2-fr20-four-original-student-4s",environment_name="main"):
        for i in range(4):
            video=OUT/f"actor_pre_tbdub_{i}.mp4"
            if sha(video)!=ltx["attempts"][i]["normalized_sha"]:raise RuntimeError("LTX video changed")
            face_input=base64.b64encode(video.read_bytes()).decode()
            audio_input=base64.b64encode((OUT/f"speech{i}.wav").read_bytes()).decode()
            preflight=tb.preflight.remote(face_input,audio_input)
            if preflight.get("status")!="CPU_FACE_PREFLIGHT_PASSED":
                raise RuntimeError(f"Face preflight rejected clip {i}")
            print("TBDUB_4S_START",i,flush=True)
            res=tb.render_student_four_seconds.remote(face_input,audio_input)
            file=OUT/f"tbdub_raw_{i}.mp4"
            file.write_bytes(base64.b64decode(res["video_base64"],validate=True))
            if sha(file)!=res["metadata"]["video_sha256"]:
                raise RuntimeError("TBDub checksum mismatch")
            duration=float(info(file)["format"]["duration"])
            if abs(duration-4)>.08:raise RuntimeError("TBDub 4s drift")
            outfile=OUT/f"actor_dubbed_{i}.mp4"
            run(["ffmpeg","-y","-nostdin","-v","error","-i",file,
                 "-map","0:v:0","-an","-vf","fps=25,setsar=1,format=yuv420p",
                 "-frames:v","100","-c:v","libx264","-crf","16","-preset","fast",outfile])
            if int(next(s for s in info(outfile)["streams"] if s["codec_type"]=="video")["nb_frames"])!=100:
                raise RuntimeError("TBDub not 100 frames")
            receipt["attempts"].append({
                "index":i,"source_audio_sha":sha(OUT/f"speech{i}.wav"),
                "raw_sha":sha(file),"normalized_sha":sha(outfile),
                "tbdub_metadata":res["metadata"]})
            record("tbdub_receipts.json",receipt)
            print("TBDUB_4S_DONE",i,flush=True)
    receipt["status"]="FOUR_REAL_4S_TBDUB_READY"
    record("tbdub_receipts.json",receipt)

def assemble():
    validate()
    d=json.loads((OUT/"tbdub_receipts.json").read_text())
    if d["status"]!="FOUR_REAL_4S_TBDUB_READY":raise RuntimeError("No full 4x4s lipsync")
    actors=[]
    for i in range(4):
        x=OUT/f"actor_dubbed_{i}.mp4"
        if sha(x)!=d["attempts"][i]["normalized_sha"]:raise RuntimeError("Dubbed actor mismatch")
        actors+=["-i",x]
    # Source time is precisely 7.60..29.08, offset ~0. All new actor PTS
    # shifted to real timeline. No source actor survives in exposed camera.
    # The TRIGGER title is recreated over the new presenter with a pale veil;
    # no partial source-background alpha blending/segmentation.
    graph=";".join([
        "[0:v]trim=start=7.6:end=29.08,setpts=PTS-STARTPTS,format=yuv420p[base]",
        "[1:v]setpts=PTS-STARTPTS[a0]",
        "[2:v]setpts=PTS-STARTPTS+4/TB,split=2[a1][a1pip]",
        "[3:v]setpts=PTS-STARTPTS+13.48/TB[a2]",
        "[4:v]setpts=PTS-STARTPTS+17.48/TB[a3]",
        "[base][a0]overlay=0:0:eof_action=pass:repeatlast=0:enable='between(t,0,3.999)'[x0]",
        "[x0][a1]overlay=0:0:eof_action=pass:repeatlast=0:enable='between(t,4,6.639)'[x1]",
        "[a1pip]scale=492:444:force_original_aspect_ratio=increase,crop=492:444,setsar=1[pip]",
        "[x1][pip]overlay=1428:0:eof_action=pass:repeatlast=0:enable='between(t,6.64,7.959)'[x2]",
        "[x2][a2]overlay=0:0:eof_action=pass:repeatlast=0:enable='between(t,13.48,17.479)'[x3]",
        "[x3][a3]overlay=0:0:eof_action=pass:repeatlast=0:enable='between(t,17.48,19.199)'[x4]",
        "[x4]drawbox=x=0:y=0:w=iw:h=ih:color=white@0.72:t=fill:"
        "enable='between(t,4.4,6.639)',"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text=TRIGGER:fontcolor=black:fontsize=100:x=(w-text_w)/2:"
        "y=(h-text_h)/2:enable='between(t,4.4,6.639)',split=2[pre][post]",
        "[pre]trim=end_frame=73,setpts=PTS-STARTPTS[before]",
        "[post]trim=start_frame=110,setpts=PTS-STARTPTS[after]",
        "[before][after]concat=n=2:v=1:a=0,format=yuv420p[v]",
        "[5:a]asplit=2[apre][apost]",
        "[apre]atrim=end_sample=140160,asetpts=PTS-STARTPTS[abefore]",
        "[apost]atrim=start_sample=211200,asetpts=PTS-STARTPTS[aafter]",
        "[abefore][aafter]concat=n=2:v=0:a=1[a]"
    ])
    final=OUT/OUTPUT_NAME
    run(["ffmpeg","-y","-nostdin","-v","error","-i",SOURCE,*actors,
         "-i",OUT/"audio_21p48.wav","-filter_complex",graph,
         "-map","[v]","-map","[a]","-r","25","-frames:v","500",
         "-c:v","libx264","-crf","17","-preset","veryfast","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","192k","-ar","48000","-movflags","+faststart",final],
        timeout=1800)
    m=info(final)
    v=next(s for s in m["streams"] if s["codec_type"]=="video")
    audio=next(s for s in m["streams"] if s["codec_type"]=="audio")
    if (v["width"],v["height"],v["r_frame_rate"])!=(1920,1080,"25/1") or int(v["nb_frames"])!=500:
        raise RuntimeError("Bad video: 500 frames 1080p25 expected")
    if abs(float(m["format"]["duration"])-20)>.05 or audio["codec_name"]!="aac":
        raise RuntimeError("Expected exactly 20s H264/AAC")
    run(["ffmpeg","-v","error","-xerror","-i",final,"-f","null","-"],timeout=450)
    for timestamp in [0.5,2.75,2.98,4.1,5.1,5.35,6.6,8.5,12.9,14.8,17.1,18.8,19.9]:
        run(["ffmpeg","-y","-nostdin","-v","error","-ss",timestamp,"-i",final,
             "-frames:v","1","-q:v","3",OUT/f"review_{str(timestamp).replace('.','p')}.jpg"],timeout=70)
    # Audio original bit-depth was decoded once; the only removal is the
    # old Work silence frames 73..109 and matching PCM. No speech retiming.
    record("final_verification.json",{
        "status":"READY_FOR_HUMAN_REVIEW_NOT_AUTOMATICALLY_APPROVED",
        "file":OUTPUT_NAME,"sha256":sha(final),"size_bytes":final.stat().st_size,
        "duration_s":float(m["format"]["duration"]),"video_frames":int(v["nb_frames"]),
        "full_decode":True,"audio_source_unchanged_except_verified_silent_cut":True,
        "four_independent_4s_i2v":True,"four_independent_4s_tbdub":True,
        "ltx_reference_exact_match":json.loads((OUT/"ltx_receipts.json").read_text())["attempts"][0]["matches_validated_raw"],
        "global_stability_and_naturalness":"NEEDS_HUMAN_REVIEW",
        "no_ltx_12s":True,"no_background_segmentation":True,
        "original_source_publication_rights":False,
    })
    print("FR20_MP4_READY_FOR_REVIEW",final,flush=True)

if __name__=="__main__":
    if len(sys.argv)!=2 or sys.argv[1] not in ("prepare","animate","dub","assemble"):
        raise SystemExit("Usage: python render_20s.py prepare|animate|dub|assemble")
    {"prepare":prepare,"animate":animate,"dub":dub,"assemble":assemble}[sys.argv[1]]()
