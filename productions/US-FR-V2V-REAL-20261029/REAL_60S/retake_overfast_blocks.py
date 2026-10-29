#!/usr/bin/env python3
"""Re-synthesize ONLY five too-short French phrases, preserving accepted blocks.

Input full source and alignment are unchanged; previous Chatterbox V3 7x2
auditions are reused from run 40945609860, not recomputed. New wording closer
to source content fixes unnatural multi-second pauses without time stretching.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import os
import sys
import hashlib
from pathlib import Path

ROOT=Path("productions/US-FR-V2V-REAL-20261029/REAL_60S")
OUT=ROOT/"OUTPUT"
SCRIPT=ROOT/"build_french_voice_and_preview.py"
spec=importlib.util.spec_from_file_location("ugc_fr60_voice",SCRIPT)
v=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=v
spec.loader.exec_module(v)
RETAKE_BLOCKS=v.BLOCKS[2:]


def main():
    import modal
    from deploy import modal_chatterbox_v3_fr_pilot as worker
    if os.environ.get("STUDIO_MODAL_WORKSPACE")!="lucj76861":
        raise RuntimeError("Wrong Modal workspace")
    if os.getenv("ONE_VOICE_RETAKE_GPU")!="YES" or os.getenv("GITHUB_RUN_ATTEMPT","1")!="1":
        raise RuntimeError("Retake permitted once only")
    meta=OUT/"fr_voice_candidate_durations.json"
    if not meta.is_file():
        raise RuntimeError("Old 7x2 V3 candidate metadata artifact required")
    original=json.loads(meta.read_text())
    if len(original["blocks"])!=7:
        raise RuntimeError("Previous candidate count mismatch")
    if [b["id"] for b in original["blocks"]] != [b["id"] for b in v.BLOCKS]:
        raise RuntimeError("Mismatch in block IDs")
    for block in original["blocks"][:2]:
        for item in block["candidates"]:
            if not (OUT/item["file"]).is_file():
                raise RuntimeError("Existing accepted WAV missing: "+item["file"])
    v.preflight()
    with worker.app.run(name="ugc-fr60-v3-fix-last-five-utterances",environment_name="main"):
        result=worker.render_original_paced_french_blocks.remote(RETAKE_BLOCKS)
    updated=original["blocks"][:2]
    for rec in result["blocks"]:
        candidates=[]
        for take in rec["candidates"]:
            name=rec["id"]+"_"+take["tag"]+".wav"
            p=OUT/name
            p.write_bytes(base64.b64decode(take["wav_b64"],validate=True))
            if hashlib.sha256(p.read_bytes()).hexdigest()!=take["sha256"]:
                raise RuntimeError("Voice take hash mismatch: "+name)
            candidates.append({k:v for k,v in take.items() if k!="wav_b64"}|{"file":name})
        updated.append({k:v for k,v in rec.items() if k!="candidates"}|{"candidates":candidates})
    original.update({
        "blocks":updated,
        "revision":"last five phrases revised to match original talking cadence",
        "original_successful_7_block_run":40945609860,
        "new_gpu_calls":1,
        "voice_timbre":"same Chatterbox Multilingual V3 builtin model",
        "no_time_stretch":True,
    })
    meta.write_text(json.dumps(original,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("V3_FINAL_FIVE_PHRASES_RETAKEN",len(updated),flush=True)
    v.mix()
    v.preview()

if __name__=="__main__":
    main()
