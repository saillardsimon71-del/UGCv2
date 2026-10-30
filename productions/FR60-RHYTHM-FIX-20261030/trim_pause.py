import hashlib
import json
import subprocess
import wave
from pathlib import Path

import cv2
import numpy as np

BASE = Path(__file__).resolve().parent
PREVIOUS = BASE.parent / "FR60-CONTINUITY-8S-20261030"
SOURCE = PREVIOUS / "RENDERS/UGCv2_RACCORD_8s_titre_PiP.mp4"
AUDIO = PREVIOUS / "CACHE/continuous-audio48k.wav"
OUT = BASE / "RENDERS/UGCv2_RACCORD_RYTHME_V2_6p52s.mp4"
SOURCE_SHA = "54cd82d57512445ad2ea4c09dc8938abad4a85a05c93c0eb483ec08587c4bc98"
CUT_FRAMES = (73, 110)
CUT_SAMPLES = (140160, 211200)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(args):
    return subprocess.run(list(map(str, args)), check=True, capture_output=True,
                          text=True, encoding="utf-8", timeout=180)


assert sha(SOURCE) == SOURCE_SHA
assert not OUT.exists()
OUT.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(AUDIO)) as stream:
    assert stream.getframerate() == 48000 and stream.getnchannels() == 2
    pcm = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").reshape(-1, 2)
removed = pcm[CUT_SAMPLES[0]:CUT_SAMPLES[1]]
removed_peak_dbfs = float(20 * np.log10(max(float(np.abs(removed.astype(float)).max()) / 32768, 1e-12)))
assert removed_peak_dbfs < -70, "Cut intersects audible sound"
graph = (
    "[0:v]trim=end_frame=73,setpts=PTS-STARTPTS[v0];"
    "[0:v]trim=start_frame=110,setpts=PTS-STARTPTS[v1];"
    "[v0][v1]concat=n=2:v=1:a=0[v];"
    "[1:a]atrim=end_sample=140160,asetpts=PTS-STARTPTS[a0];"
    "[1:a]atrim=start_sample=211200,asetpts=PTS-STARTPTS[a1];"
    "[a0][a1]concat=n=2:v=0:a=1[a]"
)
run(["ffmpeg", "-nostdin", "-v", "error", "-n", "-i", SOURCE, "-i", AUDIO,
     "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
     "-c:v", "libx264", "-crf", 16, "-preset", "fast", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "192k", "-ar", 48000, "-movflags", "+faststart", OUT])
run(["ffmpeg", "-v", "error", "-xerror", "-i", OUT, "-f", "null", "-"])
media = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                        "-of", "json", OUT]).stdout)
video = next(s for s in media["streams"] if s["codec_type"] == "video")
assert int(video["nb_frames"]) == 163
assert abs(float(media["format"]["duration"]) - 6.52) < .03
assert video["r_frame_rate"] == "25/1"
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(OUT), "-map", "0:a:0",
                      "-ar", "48000", "-ac", "2", "-f", "s16le", "-"],
                     check=True, capture_output=True).stdout
actual = np.frombuffer(raw, dtype="<i2").reshape(-1, 2)
expected = np.concatenate([pcm[:CUT_SAMPLES[0]], pcm[CUT_SAMPLES[1]:]])
assert len(expected) == 312960
correlation = float(np.corrcoef(actual[:len(expected)].ravel(), expected.ravel())[0, 1])
assert correlation > .999
old = cv2.VideoCapture(str(SOURCE))
new = cv2.VideoCapture(str(OUT))
errors = []
for output_index in range(163):
    source_index = output_index if output_index < 73 else output_index + 37
    old.set(cv2.CAP_PROP_POS_FRAMES, source_index)
    ok1, a = old.read()
    ok2, b = new.read()
    assert ok1 and ok2
    difference = a.astype(np.float32) - b.astype(np.float32)
    errors.append(float(np.mean(difference * difference)))
old.release()
new.release()
assert sha(SOURCE) == SOURCE_SHA
report = {
    "source_sha256": SOURCE_SHA, "source_duration_s": 8,
    "removed_interval_s": [2.92, 4.4], "removed_frames": 37, "removed_seconds": 1.48,
    "removed_pcm_peak_dbfs": removed_peak_dbfs,
    "detected_pause_before_s": [2.701646, 4.623563], "pause_after_s": .441917,
    "output_duration_s": float(media["format"]["duration"]), "output_frames": 163,
    "audio_zero_offset_correlation": correlation,
    "retained_frames_psnr_db": float(10 * np.log10(255**2 / np.mean(errors))),
    "all_title_frames_preserved": True, "title_start_output_s": 2.92,
    "pip_start_output_s": (166 - 37) / 25, "domino_start_output_s": (199 - 37) / 25,
    "audio_speed_changed": False, "new_gpu_calls": 0, "source_file_unchanged": True,
    "output_sha256": sha(OUT),
}
(BASE / "edit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
