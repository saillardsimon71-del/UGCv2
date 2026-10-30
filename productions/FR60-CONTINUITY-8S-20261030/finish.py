import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from run import BASE, CACHE, REF, RENDERS, ffmpeg, probe, protect_references, run, save, sha


def concatenate_preserving_A(second, name):
    first = REF / "EXPORTS/Clip_A_gros_plan.mp4"
    listing = CACHE / f"{name}.txt"
    listing.write_text(f"file '{first.as_posix()}'\nfile '{second.as_posix()}'\n", encoding="utf-8")
    dest = RENDERS / name
    ffmpeg("-f", "concat", "-safe", 0, "-i", listing,
           "-i", CACHE / "continuous-audio48k.wav", "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", dest)
    return dest


def compose(trial):
    protect_references()
    after = CACHE / f"trial-{trial}-after.mp4"
    before = CACHE / f"trial-{trial}-before.mp4"
    for path in [before, after]:
        metadata = probe(path)
        video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
        if abs(float(metadata["format"]["duration"]) - 4) > .04 or int(video["nb_frames"]) != 100:
            raise RuntimeError("Expected a genuine four-second, 100-frame take; no padding")
    pip_path = CACHE / f"trial-{trial}-pip.mkv"
    ffmpeg("-i", after, "-map", "0:v:0", "-an", "-vf",
           "scale=492:444:force_original_aspect_ratio=increase,crop=492:444,setsar=1",
           "-c:v", "ffv1", pip_path)
    actor = cv2.VideoCapture(str(after))
    pip = cv2.VideoCapture(str(pip_path))
    original = cv2.VideoCapture(str(CACHE / "original-next-4s.mkv"))
    lossless = CACHE / f"trial-{trial}-montage-lossless.mkv"
    if lossless.exists():
        raise FileExistsError(lossless)
    encoder = subprocess.Popen([
        "ffmpeg", "-nostdin", "-v", "error", "-n", "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", "1920x1080", "-r", "25", "-i", "pipe:0", "-an", "-c:v", "ffv1", str(lossless),
    ], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    regions = {"full": 0, "title": 0, "pip": 0, "domino": 0}
    try:
        for index in range(100):
            ok1, a = actor.read()
            ok2, source = original.read()
            ok3, camera = pip.read()
            if not ok1 or not ok2 or not ok3:
                raise RuntimeError("Missing source or generated frame")
            if index < 10:
                frame = a
                regions["full"] += 1
            elif index < 66:
                # Recover only the native animated black lettering. The pale
                # source actor/background never enter the new composition.
                glyph = np.zeros((1080, 1920), np.float32)
                glyph[280:800, 100:1820] = np.clip(
                    (170 - source[280:800, 100:1820].max(axis=2).astype(np.float32)) / 170, 0, 1,
                )
                frame = np.rint((a.astype(np.float32) * .28 + 255 * .72) *
                               (1 - glyph[:, :, None])).clip(0, 255).astype(np.uint8)
                regions["title"] += 1
            elif index < 99:
                # Same opaque camera rectangle and uniform cover crop as proof B.
                frame = source.copy()
                frame[:444, 1428:1920] = camera
                regions["pip"] += 1
            else:
                frame = source
                regions["domino"] += 1
            encoder.stdin.write(frame.tobytes())
        if actor.read()[0] or original.read()[0] or pip.read()[0]:
            raise RuntimeError("Unexpected frames beyond four seconds")
    finally:
        actor.release()
        pip.release()
        original.release()
        encoder.stdin.close()
    errors = encoder.stderr.read().decode(errors="replace")
    if encoder.wait(timeout=120):
        raise RuntimeError(errors[-2000:])
    options = ["-c:v", "libx264", "-crf", 17, "-preset", "fast", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart"]
    second = CACHE / f"trial-{trial}-montage-4s.mp4"
    ffmpeg("-i", lossless, "-i", CACHE / "new-audio48k.wav", "-map", "0:v:0", "-map", "1:a:0",
           *options, second)
    actor_second = CACHE / f"trial-{trial}-actor-delivery.mp4"
    ffmpeg("-i", after, "-i", CACHE / "new-audio48k.wav", "-map", "0:v:0", "-map", "1:a:0",
           "-vf", "fps=25,setsar=1", *options, actor_second)
    final = concatenate_preserving_A(second, "UGCv2_RACCORD_8s_titre_PiP.mp4")
    diagnostic = concatenate_preserving_A(actor_second, "UGCv2_RACCORD_8s_acteur_sans_titre.mp4")
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 21)
    header = Image.new("RGB", (1280, 40), (22, 28, 40))
    draw = ImageDraw.Draw(header)
    draw.text((20, 7), "AVANT TBDUB - nouvelle prise", font=font, fill="white")
    draw.text((660, 7), "APRES TBDUB - meme prise", font=font, fill="white")
    header_path = CACHE / "comparison-header.png"
    header.save(header_path)
    comparison = RENDERS / "UGCv2_AVANT_APRES_TBDub_4s.mp4"
    ffmpeg("-loop", 1, "-framerate", 25, "-i", header_path, "-i", before, "-i", after,
           "-i", CACHE / "new-audio48k.wav", "-filter_complex",
           "[1:v]fps=25,scale=640:360,setpts=PTS-STARTPTS[l];"
           "[2:v]fps=25,scale=640:360,setpts=PTS-STARTPTS[r];"
           "[l][r]hstack=inputs=2[pair];[0:v]format=yuv420p[h];[h][pair]vstack=inputs=2[v]",
           "-map", "[v]", "-map", "3:a:0", "-t", 4, *options, comparison)
    save("montage.json", {"trial": trial, "source_range_s": [7.6, 15.6], "new_take_regions_frames": regions,
                           "title": "native animated lettering isolated on new actor and 72% white veil",
                           "files": [{"name": p.name, "sha256": sha(p)} for p in [final, diagnostic, comparison]]})
    print("EIGHT_SECOND_MONTAGE_AND_DIAGNOSTIC_READY", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", type=int, choices=[1, 2], default=1)
    compose(parser.parse_args().trial)
