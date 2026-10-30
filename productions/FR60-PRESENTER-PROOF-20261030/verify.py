import hashlib
import json
import math
import subprocess
import wave
from pathlib import Path

import cv2
import numpy as np

BASE = Path(__file__).resolve().parent
CACHE = BASE / "CACHE"
EXPORTS = BASE / "EXPORTS"


def frame_hashes(path, crop):
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-an", "-vf", crop,
         "-pix_fmt", "yuv420p", "-f", "framemd5", "-"],
        check=True, capture_output=True, text=True, timeout=120,
    )
    return [s.rsplit(",", 1)[1].strip() for s in result.stdout.splitlines()
            if s and not s.startswith("#")]


report = {"lossless_screen_regions": [], "encoded_screen": {}, "audio": {}}
for crop in ["crop=1428:1080:0:0", "crop=492:636:1428:444"]:
    original = frame_hashes(CACHE / "B-original.mkv", crop)
    composite = frame_hashes(CACHE / "B-composite-lossless.mkv", crop)
    assert len(original) == 100 and original == composite, crop
    report["lossless_screen_regions"].append({"region": crop, "frames": 100,
                                               "all_original_pixel_hashes_equal": True})

generated_camera = frame_hashes(
    CACHE / "B-actor.mkv",
    "scale=492:444:force_original_aspect_ratio=increase,crop=492:444,setsar=1",
)
composited_camera = frame_hashes(CACHE / "B-composite-lossless.mkv", "crop=492:444:1428:0")
assert len(generated_camera) == 100 and generated_camera == composited_camera
report["pip_coverage"] = {"frames": 100, "entire_rectangle_matches_generated_actor": True}

source = cv2.VideoCapture(str(CACHE / "B-original.mkv"))
final = cv2.VideoCapture(str(EXPORTS / "Clip_B_PiP.mp4"))
mask = np.ones((1080, 1920), dtype=bool)
mask[:446, 1426:] = False
errors = []
for i in range(100):
    ok1, a = source.read()
    ok2, b = final.read()
    assert ok1 and ok2
    difference = a[mask].astype(np.float32) - b[mask].astype(np.float32)
    errors.append(float(np.mean(difference * difference)))
assert not source.read()[0] and not final.read()[0]
source.release()
final.release()
report["encoded_screen"] = {"frames": 100, "psnr_db": 10 * math.log10(255**2 / np.mean(errors)),
                             "max_frame_mse": max(errors), "boundary_margin_px": 2}

for name, filename in [("A", "Clip_A_gros_plan.mp4"), ("B", "Clip_B_PiP.mp4")]:
    with wave.open(str(CACHE / f"{name}-audio.wav")) as stream:
        assert stream.getframerate() == 48000 and stream.getnframes() == 192000
        expected = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").reshape(-1, 2)
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(EXPORTS / filename), "-map", "0:a:0",
         "-ar", "48000", "-ac", "2", "-f", "s16le", "-"],
        check=True, capture_output=True, timeout=60,
    ).stdout
    actual = np.frombuffer(raw, dtype="<i2").reshape(-1, 2)
    assert len(actual) >= len(expected)
    a = expected.astype(np.float64)
    b = actual[:len(a)].astype(np.float64)
    correlation = float(np.corrcoef(a.ravel(), b.ravel())[0, 1])
    assert correlation > .98
    report["audio"][name] = {"expected_samples": len(a), "decoded_aac_samples": len(actual),
                              "zero_offset_correlation": correlation,
                              "input_pcm_sha256": hashlib.sha256(expected.tobytes()).hexdigest(),
                              "audio_retiming": False}

report["identity_evidence"] = {
    "A_and_B_share_exact_animation_master":
        json.loads((BASE / "lips-A.json").read_text())["master_sha256"] ==
        json.loads((BASE / "lips-B.json").read_text())["master_sha256"],
    "interpretation": "Shared provenance and full rectangle replacement; identity quality requires visual review",
}
assert report["identity_evidence"]["A_and_B_share_exact_animation_master"]
(BASE / "preservation-verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
