#!/usr/bin/env python3
"""CPU-only English word-aligned transcription of the verified 60-second source.

Research only. Do not use captions invented from the timeline. Segment timings
are derived from the actual source audio with faster-whisper, CPU int8 small.en.
The file is not sent to any external transcription API.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

ROOT=Path("productions/US-FR-V2V-REAL-20261029/REAL_60S/OUTPUT")
SOURCE=ROOT/"source_window_60s.mp4"
TARGET=ROOT/"source_english_16k.wav"

def sh(parts):
    subprocess.run(parts,check=True,capture_output=True,timeout=240)

def main():
    import numpy as np
    import soundfile as sf
    from faster_whisper import WhisperModel

    if not SOURCE.is_file() or SOURCE.stat().st_size<1_000_000:
        raise RuntimeError("Verified source 60s artifact unavailable")
    sh(["ffmpeg","-y","-v","error","-i",str(SOURCE),
        "-map","0:a:0","-ar","16000","-ac","1",
        "-c:a","pcm_s16le",str(TARGET)])
    wav,sr=sf.read(str(TARGET),dtype="float32")
    if sr!=16000 or not 59.5<len(wav)/sr<60.5:
        raise RuntimeError("Invalid original speech audio duration")
    rms=[]
    for n in range(600):
        chunk=wav[int(n*.1*sr):int((n+1)*.1*sr)]
        rms.append(round(float(np.sqrt(np.mean(chunk*chunk))) if len(chunk) else 0.0,5))
    model=WhisperModel("small.en",device="cpu",compute_type="int8",cpu_threads=4,num_workers=1)
    chunks,info=model.transcribe(
        str(TARGET),language="en",task="transcribe",word_timestamps=True,
        vad_filter=False,beam_size=3,condition_on_previous_text=True,
        initial_prompt="This is a tutorial about Zapier, Zap, trigger, actions, and Dropbox.",
    )
    transcript=[]
    for seg in chunks:
        transcript.append({
            "start_s":round(seg.start,3),
            "end_s":round(seg.end,3),
            "absolute_start_s":round(42+seg.start,3),
            "text":seg.text.strip(),
            "avg_logprob":round(seg.avg_logprob,3),
            "words":[{"word":w.word,"start_s":round(w.start,3),"end_s":round(w.end,3)}
                     for w in (seg.words or [])],
        })
    if not transcript:
        raise RuntimeError("No transcription from actual source")
    (ROOT/"english_transcript_word_timings.json").write_text(
        json.dumps({"source":"real source window 00:42-01:42",
            "engine":"faster-whisper small.en CPU int8",
            "language":"en","language_probability":round(info.language_probability,3),
            "segments":transcript,
            "rms_100ms":rms,
            "notice":"Computer transcription: review proper nouns, punctuation and microtiming by listening."
        },indent=2,ensure_ascii=False)+"\n")
    (ROOT/"english_transcript_readable.txt").write_text(
        "\n".join(f"{x['start_s']:05.2f}–{x['end_s']:05.2f}  {x['text']}"
                  for x in transcript)+"\n",encoding="utf8")
    print("REAL_60S_TRANSCRIBED",len(transcript),"segments")
    for s in transcript: print(f"{s['start_s']:.1f}-{s['end_s']:.1f}",s["text"])

if __name__=="__main__":
    main()
