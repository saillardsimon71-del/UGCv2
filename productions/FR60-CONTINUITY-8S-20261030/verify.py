import json
import math
import subprocess
import wave

import cv2
import numpy as np

from run import BASE, CACHE, REF, RENDERS, probe, protect_references, run, save, sha


def frame_hashes(path, count=None):
    args = ["ffmpeg", "-v", "error", "-i", path, "-map", "0:v:0", "-an"]
    if count:
        args += ["-frames:v", count]
    result = run([*args, "-pix_fmt", "yuv420p", "-f", "framemd5", "-"])
    return [s.rsplit(",", 1)[1].strip() for s in result.splitlines() if s and not s.startswith("#")]


def background_transform(path1, time1, path2, time2):
    frames = []
    for path, time in [(path1, time1), (path2, time2)]:
        cap = cv2.VideoCapture(str(path))
        cap.set(cv2.CAP_PROP_POS_MSEC, time * 1000)
        ok, frame = cap.read()
        cap.release()
        if not ok:
            raise RuntimeError("Missing measurement frame")
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    mask = np.full(frames[0].shape, 255, np.uint8)
    mask[:, 500:1450] = 0
    mask[750:] = 0
    orb = cv2.ORB_create(nfeatures=5000)
    k1, d1 = orb.detectAndCompute(frames[0], mask)
    k2, d2 = orb.detectAndCompute(frames[1], mask)
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2)
    matches = [m for m in matches if m.distance < 35]
    a = np.float32([k1[m.queryIdx].pt for m in matches])
    b = np.float32([k2[m.trainIdx].pt for m in matches])
    matrix, inliers = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=3)
    if matrix is None:
        raise RuntimeError("Cannot measure background transform")
    return {"scale": float(np.hypot(matrix[0, 0], matrix[0, 1])),
            "translation_px": matrix[:, 2].tolist(), "inliers": int(inliers.sum())}


protect_references()
original = REF / "EXPORTS/Clip_A_gros_plan.mp4"
expected = frame_hashes(original)
assert len(expected) == 100
report = {"reference_A_unchanged": True, "reference_B_unchanged": True, "files": []}
for filename in ["UGCv2_RACCORD_8s_titre_PiP.mp4", "UGCv2_RACCORD_8s_acteur_sans_titre.mp4"]:
    path = RENDERS / filename
    media = probe(path)
    video = next(s for s in media["streams"] if s["codec_type"] == "video")
    assert int(video["nb_frames"]) == 200
    assert abs(float(media["format"]["duration"]) - 8) < .05
    assert (video["width"], video["height"], video["r_frame_rate"]) == (1920, 1080, "25/1")
    assert frame_hashes(path, 100) == expected
    run(["ffmpeg", "-v", "error", "-xerror", "-i", path, "-f", "null", "-"])
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0",
                          "-ar", "48000", "-ac", "2", "-f", "s16le", "-"],
                         check=True, capture_output=True).stdout
    actual = np.frombuffer(raw, dtype="<i2").reshape(-1, 2)
    with wave.open(str(CACHE / "continuous-audio48k.wav")) as stream:
        assert stream.getnframes() == 384000
        reference = np.frombuffer(stream.readframes(384000), dtype="<i2").reshape(-1, 2)
    assert len(actual) >= len(reference)
    correlation = float(np.corrcoef(actual[:len(reference)].ravel(), reference.ravel())[0, 1])
    assert correlation > .999
    report["files"].append({"filename": filename, "sha256": sha(path), "duration_s": 8,
                            "frames": 200, "first_100_frames_exactly_match_A": True,
                            "audio_zero_offset_correlation": correlation, "full_decode": "passed"})

before = CACHE / "trial-1-before.mp4"
after = CACHE / "trial-1-after.mp4"
report["background_new_take"] = background_transform(before, 0, before, 3.96)
report["background_at_seam_before_TBDub"] = background_transform(original, 3.96, before, 0)
report["background_at_seam_after_TBDub"] = background_transform(original, 3.96, after, 0)
old_face = json.loads((REF / "lips-A.json").read_text())["preprocessing"]["frame_diagnostics"][-1]
new_face = json.loads((BASE / "preflight-trial-1.json").read_text())["face_report"]["frame_diagnostics"][0]
report["face_detection_at_seam"] = {"reference_last": old_face, "new_first": new_face}
report["new_generation_counts"] = {"ltx": len(list(BASE.glob("ltx-trial-*.json"))),
                                    "tbdub": len(list(BASE.glob("tbdub-trial-*.json")))}
assert report["new_generation_counts"]["ltx"] <= 2 and report["new_generation_counts"]["tbdub"] <= 2
report["perceptual_review"] = "separate visual comparison; these checks do not certify human likeness or phonetic lip sync"
save("verification.json", report)
print(json.dumps(report, indent=2))
