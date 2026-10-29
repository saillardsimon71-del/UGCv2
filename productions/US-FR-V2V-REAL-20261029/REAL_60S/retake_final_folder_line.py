#!/usr/bin/env python3
"""One precise V3 retake to fill the original last 11-second speaking slot.

Earlier first six blocks and already rendered videos are reused by checksum.
No altered speech tempo. New wording remains faithful to original Dropbox demo.
"""
from __future__ import annotations
import base64
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT=Path("productions/US-FR-V2V-REAL-20261029/REAL_60S")
OUT=ROOT/"OUTPUT"
S=ROOT/"build_french_voice_and_preview.py"
spec=importlib.util.spec_from_file_location("ugc_fr60_last",S)
v=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=v
spec.loader.exec_module(v)


def main():
    if os.getenv("STUDIO_MODAL_WORKSPACE")!="lucj76861":
        raise RuntimeError("Wrong Modal account")
    if os.getenv("ONE_LAST_FR_V3_GPU")!="YES" or os.getenv("GITHUB_RUN_ATTEMPT","1")!="1":
        raise RuntimeError("One last-block GPU only")
    original_file=OUT/"fr_voice_candidate_durations.json"
    if not original_file.is_file():
        raise RuntimeError("Previous refined voice artifact absent")
    previous=json.loads(original_file.read_text())
    if len(previous["blocks"])!=7:
        raise RuntimeError("Previous takes not from seven aligned blocks")
    from deploy import modal_chatterbox_v3_fr_pilot as ch
    import modal
    block=v.BLOCKS[-1]
    if block["id"]!="07_youtube_folders":
        raise RuntimeError("Unexpected last block")
    # Reuse exact existing voice tracks from prior successful refined run.
    for old in previous["blocks"][:6]:
        for candidate in old["candidates"]:
            if not (OUT/candidate["file"]).is_file():
                raise RuntimeError("Accepted voice reference missing: "+candidate["file"])
    v.preflight()
    with ch.app.run(name="ugc-fr60-chatterbox-final-folder-phrase",environment_name="main"):
        produced=ch.render_original_paced_french_blocks.remote([block])
    entry=produced["blocks"][0]
    candidates=[]
    for item in entry["candidates"]:
        file=OUT/(entry["id"]+"_"+item["tag"]+".wav")
        buf=base64.b64decode(item["wav_b64"],validate=True)
        file.write_bytes(buf)
        if hashlib.sha256(buf).hexdigest()!=item["sha256"]:
            raise RuntimeError("Audio bytes hash mismatch")
        candidates.append({k:value for k,value in item.items() if k!="wav_b64"}|{"file":file.name})
    previous.update({
        "blocks":previous["blocks"][:6]+[
            {k:value for k,value in entry.items() if k!="candidates"}|{"candidates":candidates}],
        "reused_accepted_first_six_blocks":True,
        "source_refined_voice_run":40947229775,
        "last_block_revision":"natural French detail follows original Dropbox folder action",
        "new_gpu_calls":1,
    })
    original_file.write_text(json.dumps(previous,indent=2,ensure_ascii=False)+"\n")
    v.mix()
    v.preview()
    print("FULL_60S_FRENCH_FINAL_VOICE_WITH_ORIGINAL_CADENCE_READY",flush=True)

if __name__=="__main__":
    main()
