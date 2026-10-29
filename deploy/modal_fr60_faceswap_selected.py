"""Isolated FaceFusion reference actor test, explicit source face selector mode.

The old 60s run succeeded technically while changing no identity because
FaceFusion defaults to --face-selector-mode reference and the first screen
frame (Zapier UI with tiny PIP) is not a reliable reference face. Explicitly
choose one visible face per frame for this one-presenter source.

Do not touch original face worker or the V2V LTX engine. For now test only
4 seconds. Return FFmpeg output for mandatory pixel-diff quality gate.
"""
from __future__ import annotations
import base64
import hashlib
import subprocess
import tempfile
import time
from pathlib import Path
import modal
from deploy import modal_face_worker as existing

app=modal.App("ugc-fr60-face-selector-fixed-pilot")
image=existing.image
cache=existing.models_vol

@app.function(
    image=image,gpu="A10G",cpu=8,memory=32768,timeout=1800,
    min_containers=0,max_containers=1,scaledown_window=2,
    volumes={"/opt/facefusion/.assets/models":cache},
)
def face_swap_explicit_one(video_b64:str,ref_face_b64:str)->dict:
    started=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ugc-fr60-select-one-") as temp:
        root=Path(temp)
        source=root/"source.mp4"
        face=root/"actor_ref.jpg"
        out=root/"fixed.mp4"
        source.write_bytes(base64.b64decode(video_b64,validate=True))
        face.write_bytes(base64.b64decode(ref_face_b64,validate=True))
        if source.read_bytes()[4:8]!=b"ftyp" or face.read_bytes()[:2]!=b"\xff\xd8":
            raise ValueError("Original MP4 and actual previous artificial actor JPEG required")
        cmd=[
            "python","facefusion.py","headless-run",
            "--source-paths",str(face),
            "--target-path",str(source),
            "--output-path",str(out),
            "--processors","face_swapper","face_enhancer",
            "--face-selector-mode","one",
            "--face-selector-order","large-small",
            "--face-swapper-model","inswapper_128_fp16",
            "--face-enhancer-model","gfpgan_1.4",
            "--execution-providers","cuda",
            "--output-video-encoder","libx264",
            "--output-video-quality","90",
            "--output-audio-encoder","aac",
            "--log-level","info",
        ]
        run=subprocess.run(cmd,cwd="/opt/facefusion",capture_output=True,text=True,timeout=1600)
        if run.returncode!=0 or not out.is_file() or out.stat().st_size<100_000:
            raise RuntimeError("FaceFusion selection failed: "+(run.stdout+"\n"+run.stderr)[-4000:])
        result=out.read_bytes()
        cache.commit()
        return {
            "video_base64":base64.b64encode(result).decode(),
            "metadata":{
                "source":"actual verified source presenter",
                "face_selector_mode":"one",
                "face_selector_order":"large-small",
                "engine":"FaceFusion 3.5.1 face_swapper only plus face_enhancer",
                "gpu":"A10G",
                "duration_expected_s":None,
                "bytes":len(result),
                "sha256":hashlib.sha256(result).hexdigest(),
                "wall_seconds":round(time.perf_counter()-started,2),
                "log_tail":(run.stdout+"\n"+run.stderr)[-5000:],
                "no_EDTalk":True,
            },
        }
