"""CPU-only faithful source speech transcription with word timestamps.

No synthetic voice and no GPU. Timestamps are *relative to 00:42 source*.
Do not fabricate transcript when model confidence is low.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel

ROOT=Path("productions/US-FR-V2V-REAL-20261029/REAL_60S/OUTPUT")
VIDEO=ROOT/"source_window_60s.mp4"
ROOT.mkdir(parents=True,exist_ok=True)
if not VIDEO.is_file() or VIDEO.stat().st_size<1_000_000:
    raise RuntimeError("Verified 60s source video absent")
WAV=ROOT/"original_english_60s.wav"
subprocess.run(["ffmpeg","-y","-v","error","-i",str(VIDEO),
                "-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",str(WAV)],
               timeout=180,check=True)
if WAV.stat().st_size<400_000:
    raise RuntimeError("No sufficient source speech audio")
model=WhisperModel("small.en",device="cpu",compute_type="int8",cpu_threads=4)
segments,info=model.transcribe(str(WAV),language="en",word_timestamps=True,
                               vad_filter=False,beam_size=5,condition_on_previous_text=True)
result=[]
for part in segments:
    words=[{"start":round(w.start,2),"end":round(w.end,2),"word":w.word}
           for w in (part.words or [])]
    result.append({"start":round(part.start,2),"end":round(part.end,2),
                   "text":part.text.strip(),"words":words,
                   "avg_logprob":part.avg_logprob,"no_speech_prob":part.no_speech_prob})
report={"source_start_s":42,"source_end_s":102,"duration_s":60,
        "detected_language":info.language,"language_probability":info.language_probability,
        "engine":"faster-whisper small.en CPU", "transcription_status":"ASR_NEEDS_REVIEW",
        "segments":result}
(ROOT/"timed_english_transcript.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
(ROOT/"timed_english_transcript.txt").write_text(
    "\n".join(f"[{z['start']:05.2f}-{z['end']:05.2f}] {z['text']}" for z in result)+"\n",
    encoding="utf8")
print("TRANSCRIPT_SEGMENTS",len(result),"LANGUAGE",info.language,flush=True)
for z in result: print(f"[{z['start']:05.2f}-{z['end']:05.2f}]",z['text'],flush=True)
