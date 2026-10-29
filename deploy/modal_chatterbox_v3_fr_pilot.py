"""Isolated voice pilot: Chatterbox Multilingual V3, native French default voice.

This is NOT the old V2 worker. The official Resemble AI API must explicitly
set t3_model='v3'; previous UGCv2 worker did not. We do not invent or clone
an unrelated person's voice: the V3 checkpoint's built-in voice is used.
Two slightly different performance settings are auditioned; never stretch
slow TTS over the video length.
"""
from __future__ import annotations

import base64
import hashlib
import os
import tempfile
import time
from pathlib import Path

import modal

UPSTREAM_SHA = "5de7a54aa4e5e2baadb0182dde554908b48b85c2"
app = modal.App("ugcv2-chatterbox-v3-french-pilot")
VOICE_ROOT = Path("/mnt/ugcv2_chatterbox_v3_cache")
voice_volume = modal.Volume.from_name("ugc-chatterbox-v3-fr-models", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libsndfile1", "libgomp1")
    .run_commands(
        "git clone https://github.com/resemble-ai/chatterbox.git /opt/chatterbox-v3",
        f"cd /opt/chatterbox-v3 && git checkout --detach {UPSTREAM_SHA}",
        "python -m pip install --no-cache-dir /opt/chatterbox-v3",
    )
)


@app.function(
    image=image, gpu="L40S", cpu=4, memory=16384, timeout=1800,
    min_containers=0, max_containers=1, scaledown_window=2,
    volumes={str(VOICE_ROOT): voice_volume},
)
def render_french_v3_candidates(text: str) -> dict:
    if len(text.strip()) < 80 or len(text.strip()) > 350:
        raise ValueError("The French tutorial script must be 80-350 characters")
    if any(c in text for c in "\x00<>"):
        raise ValueError("No markup or control strings in voice script")
    os.environ["HF_HOME"] = str(VOICE_ROOT / "hf")
    os.environ["XDG_CACHE_HOME"] = str(VOICE_ROOT / "cache")
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["PYTHONUNBUFFERED"] = "1"
    start = time.perf_counter()
    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    # V3 selection is essential; from_pretrained without it silently uses V2.
    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda", t3_model="v3")
    settings = [
        {"label": "expressive_v3", "exaggeration": 0.72, "cfg_weight": 0.30, "temperature": 0.82},
        {"label": "conversational_v3", "exaggeration": 0.59, "cfg_weight": 0.38, "temperature": 0.77},
    ]
    outputs = []
    with tempfile.TemporaryDirectory(prefix="ugcv2-fr-v3-") as td:
        for ix, setting in enumerate(settings):
            torch.manual_seed(30129 + ix)
            wav = model.generate(
                text,
                language_id="fr",
                audio_prompt_path=None,
                exaggeration=setting["exaggeration"],
                cfg_weight=setting["cfg_weight"],
                temperature=setting["temperature"],
            )
            output = Path(td) / (setting["label"] + ".wav")
            torchaudio.save(str(output), wav.cpu(), model.sr)
            duration = float(wav.shape[-1] / model.sr)
            if not 5.0 < duration < 25.0:
                raise RuntimeError(f"Implausible voice duration {duration}")
            buf = output.read_bytes()
            outputs.append({
                "label": setting["label"],
                "audio_b64": base64.b64encode(buf).decode(),
                "duration_seconds": round(duration, 3),
                "sample_rate": model.sr,
                "sha256": hashlib.sha256(buf).hexdigest(),
                "parameters": setting,
            })
        voice_volume.commit()
    return {
        "engine": "Chatterbox Multilingual V3",
        "v3_explicit": True,
        "speaker": "builtin_fr_voice_no_external_cloning",
        "model_revision": UPSTREAM_SHA,
        "language": "fr",
        "script": text,
        "wall_seconds": round(time.perf_counter()-start, 2),
        "candidates": outputs,
    }


@app.function(
    image=image, gpu="L40S", cpu=6, memory=24000, timeout=2400,
    min_containers=0, max_containers=1, scaledown_window=2,
    volumes={str(VOICE_ROOT): voice_volume},
)
def render_original_paced_french_blocks(blocks: list[dict]) -> dict:
    """One model load, seven independently paced phrases, two auditions each.

    The existing English voice is never used as a speaker-cloning prompt.
    Source English provides ONLY utterance timestamps, not the person's timbre.
    Target block times are supplied by *actual* Whisper alignment, not guessed.
    """
    if not 1 <= len(blocks) <= 7:
        raise ValueError("Expected one through seven source-aligned speech blocks")
    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    os.environ["HF_HOME"] = str(VOICE_ROOT / "hf")
    os.environ["XDG_CACHE_HOME"] = str(VOICE_ROOT / "cache")
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    start=time.perf_counter()
    model=ChatterboxMultilingualTTS.from_pretrained(device="cuda",t3_model="v3")
    result=[]
    # Lower emotional exaggeration and stronger CFG than the previous very fast
    # voice, with a second option to tune selection to original spoken intervals.
    settings=[
        {"tag":"unhurried","exaggeration":0.43,"cfg_weight":0.63,"temperature":0.77},
        {"tag":"conversational","exaggeration":0.54,"cfg_weight":0.55,"temperature":0.80},
    ]
    with tempfile.TemporaryDirectory(prefix="fr-original-cadence-") as td:
        for index,block in enumerate(blocks):
            txt=block["fr_text"].strip()
            if not 30<=len(txt)<=310:
                raise ValueError(f"Block {index} length invalid")
            target=float(block["end_s"])-float(block["start_s"])
            if not 4.0<target<13.0:
                raise ValueError(f"Block {index} source timing invalid")
            candidates=[]
            for take_no,sett in enumerate(settings):
                torch.manual_seed(60100+index*10+take_no)
                wav=model.generate(
                    txt,language_id="fr",audio_prompt_path=None,
                    exaggeration=sett["exaggeration"],
                    cfg_weight=sett["cfg_weight"],temperature=sett["temperature"],
                )
                duration=float(wav.shape[-1]/model.sr)
                if not 2.5<duration<22:
                    raise RuntimeError(f"Chatterbox block {index} generated absurd duration: {duration}")
                path=Path(td)/f"{index:02}_{sett['tag']}.wav"
                torchaudio.save(str(path),wav.cpu(),model.sr)
                buf=path.read_bytes()
                candidates.append({
                    "tag":sett["tag"],"duration_s":round(duration,3),
                    "wav_b64":base64.b64encode(buf).decode(),
                    "sha256":hashlib.sha256(buf).hexdigest(),
                    "settings":sett,
                })
                print("V3_FR_BLOCK",index,sett["tag"],round(duration,3),
                      "source_window",round(target,3),flush=True)
            result.append({
                "id":block["id"],"start_s":block["start_s"],
                "end_s":block["end_s"],"original_window_s":target,
                "fr_text":txt,"candidates":candidates,
            })
        voice_volume.commit()
    return {
        "engine":"Chatterbox Multilingual V3", "v3_explicit":True,
        "model_revision":UPSTREAM_SHA,
        "voice_identity":"built-in generic voice, not original-presenter cloning",
        "original_timing_source":"faster-whisper word alignment 40944640728",
        "gpu":"L40S",
        "render_seconds":round(time.perf_counter()-start,2),
        "blocks":result,
    }
