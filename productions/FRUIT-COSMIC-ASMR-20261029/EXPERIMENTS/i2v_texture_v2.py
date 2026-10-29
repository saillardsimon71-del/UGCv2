#!/usr/bin/env python3
"""One cut, one image, one Modal I2V call. Never execute more than once."""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import urllib.request
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO))
from deploy.modal_ltx_worker import validate, build_graph

SRC = ROOT / "ASSETS/shot-02-firstframe.png"
EXPECTED_SHA = "4516129d092c691843c50fcdabc89640837c07bedb69547009f9d1fd5e6c6731"
OUT = ROOT / "EXPERIMENTS/i2v-v2-output"
IMAGE = OUT / "onecut-textured-first-frame.png"
GLASS_WAV = OUT / "glass-break-gravity-sound-cc-by-4.wav"
GLASS_URL = "https://upload.wikimedia.org/wikipedia/commons/a/af/Glass_breaking_%28Gravity_Sound%29.wav"

PROMPT = (
    "EXTREME MACRO, PREMIUM ONE-TAKE PHOTOREALISTIC ASMR. "
    "5 seconds, 9:16, the ENTIRE VIDEO is ONE UNINTERRUPTED SHOT from the SAME "
    "locked overhead camera. One detailed deep-blue GLASS STRAWBERRY on wet black "
    "marble, one sharp steel knife touching its upper-right edge in the FIRST FRAME. "
    "The strawberry has a thick transparent blue-glass shell with sharp specular "
    "reflections and refracted caustics, deeply molded strawberry seed dimples, "
    "realistic tiny trapped air bubbles, microscopic scratches, delicate droplets, "
    "organic uneven surface and crisp glass facets. Never a smooth flat plastic shell. "
    "The faint blue violet galaxy is enclosed INSIDE the crystal and glows "
    "brightly only on the freshly exposed cut faces. "
    "The ONLY ACTION is a SLOW, SMOOTH, CONSTANT-VECTOR blade movement across "
    "and THROUGH the strawberry, maintaining blade-to-fruit contact for almost "
    "the entire five seconds. No stopping, no reversing, no lifting the knife "
    "mid-cut, no sudden acceleration, no different shot, no edit or new viewpoint. "
    "The same knife moves diagonally from upper right to lower left by "
    "continuous translation, crossing the full fruit. As the knife progresses, "
    "ONE thin clean fracture line extends ONLY behind the blade. The material "
    "yields with slight resistance and tiny precise brittle chips, never shatters. "
    "The two physically matching sides separate gently only as the blade "
    "reaches the far edge, near the very END of the shot, with the same texture, "
    "mass, reflections and background maintained frame to frame. "
    "No instant transformation into circular discs, no abrupt opening, no "
    "teleportation, no sudden reset, no time lapse, no second cut or action. "
    "ASMR SOUND: an intimate close-mic soft continuous crystalline scrape and "
    "fine gritty glass friction under the moving knife, one delicate sharp "
    "crystalline crack coincident with the fracture, a tiny resonant high "
    "glass ping as the halves touch the marble; quiet room tone. "
    "No music, no voices, no giant explosion, no cartoon effects. "
    "Real rigid metal knife, correct glass physics, razor-sharp surface details."
)

def save(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def prepare():
    if not SRC.is_file():
        raise RuntimeError("No real first-frame image in GitHub; abort before GPU.")
    b = SRC.read_bytes()
    if hashlib.sha256(b).hexdigest() != EXPECTED_SHA:
        raise RuntimeError("Source PNG changed; abort before GPU.")
    im = Image.open(SRC).convert("RGB")
    if im.size != (768, 1344):
        raise RuntimeError("Wrong original image dimensions.")
    # Preserve ALL original glass seed dimples, specular highlights, and
    # microtexture. The old pilot painted 96% of the fruit with a flat blue
    # fill: that was the measurable cause of its plastic-like surface.
    # Darken only the luminous galaxy CENTER, with a feathered radial mask.
    yy, xx = np.mgrid[:im.height, :im.width]
    radius_sq = ((xx - 387.0) / 135.0) ** 2 + ((yy - 697.0) / 168.0) ** 2
    feather = (0.75 * np.exp(-1.3 * radius_sq))[:, :, None]
    pixels = np.asarray(im, dtype=np.float32)
    shade = np.array([7.0, 13.0, 36.0], dtype=np.float32)[None, None, :]
    output_pixels = pixels * (1.0 - feather * 0.68) + shade * (feather * 0.68)
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(output_pixels, 0, 255).astype("uint8")).save(IMAGE, optimize=True)
    png = IMAGE.read_bytes()
    if not png.startswith(b"\x89PNG\r\n\x1a\n") or not 150_000 < len(png) < 8_000_000:
        raise RuntimeError("Unusable output image; abort.")
    payload = {"prompt": PROMPT, "duration_s": 5, "aspect_ratio": "9:16",
               "seed": 2026102963, "image_strength": 0.78,
               "audio_mode": "native", "trace_id": "fruit-cosmic-i2v-texture-v2-20261029"}
    request = validate(dict(payload, image_png_base64=base64.b64encode(png).decode()))
    graph = build_graph(request, output_prefix="i2v/onecut", uploaded_image="onecut.png")
    if graph.get("31", {}).get("class_type") != "LTXVImgToVideoInplace" or \
            any(node.get("class_type") == "LoadVideo" for node in graph.values()):
        raise RuntimeError("I2V graph invalid (source video would change mode).")
    # Real CC-BY field recording; fail BEFORE GPU if sound cannot be fetched.
    # Credit is preserved in the production README and sound report.
    request = urllib.request.Request(GLASS_URL, headers={"User-Agent":"UGCv2AudioQualityCheck/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            sample_bytes = response.read(1_500_000)
        if not (30000 < len(sample_bytes) < 1_500_000) or not sample_bytes.startswith(b"RIFF"):
            raise RuntimeError("Glass foley did not decode as a real WAV")
        GLASS_WAV.write_bytes(sample_bytes)
        subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                        "-of", "json", str(GLASS_WAV)], capture_output=True, check=True, timeout=40)
    except Exception as exc:
        raise RuntimeError("CC-BY real-glass sound sample unavailable; NO GPU to avoid silent poor-ASMR test") from exc
    receipt = {"status": "prepared_cpu_only", "source_sha256": EXPECTED_SHA,
               "first_frame_sha256": hashlib.sha256(png).hexdigest(),
               "first_frame_bytes": len(png), "prompt": PROMPT, "payload": payload,
               "foley_sha256": hashlib.sha256(sample_bytes).hexdigest(), "foley_source": GLASS_URL,
               "models": "existing LTX-2.5 distilled INT8 on Modal, no redeploy",
               "workspace": "lucj76861", "gpu_attempts_allowed": 1,
               "video_generation_approved": True, "visual_review": "pending"}
    save("plan.json", receipt)
    print("One I2V first frame prepared, precise prompt and LTX graph CPU validated.")

def render(confirm):
    if confirm != "oui" or os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
        raise RuntimeError("Only the first authorized GitHub run may spend GPU.")
    if not IMAGE.is_file():
        raise RuntimeError("Missing first frame.")
    if (OUT / "render_receipt.json").exists() or (OUT / "onecut-raw-5s.mp4").exists():
        raise RuntimeError("Previous attempt exists, retry prohibited.")
    plan = json.loads((OUT / "plan.json").read_text())
    png = IMAGE.read_bytes()
    if hashlib.sha256(png).hexdigest() != plan["first_frame_sha256"]:
        raise RuntimeError("Tampered reference image.")
    import modal
    workspace = modal.Workspace.from_context().hydrate().name
    if workspace != "lucj76861":
        raise RuntimeError("Wrong Modal workspace; abort before GPU.")
    function = modal.Function.from_name("pvs-ltx", "render_clip", environment_name="main").hydrate()
    if function.object_id != "fu-Bs1p74vExLZMqQv9n3CHZP":
        raise RuntimeError("Remote LTX function changed, not authorized to run.")
    stats = function.get_current_stats()
    if stats.num_running_inputs or stats.backlog:
        raise RuntimeError("GPU busy, don't overlap jobs.")
    payload = dict(plan["payload"], image_png_base64=base64.b64encode(png).decode())
    validate(payload)
    receipt = {"status": "starting", "attempt": 1, "workspace":workspace,
               "input_image_sha256":plan["first_frame_sha256"],
               "gpu_cost_actual_usd":None, "creative_review":"pending"}
    save("render_receipt.json", receipt)
    call = None
    completed = False
    started = time.monotonic()
    try:
        call = function.spawn(payload)
        receipt.update(status="running", call_id=call.object_id)
        save("render_receipt.json", receipt)
        result = call.get(timeout=480)
        completed = True
        raw = base64.b64decode(result["video_base64"], validate=True)
        video = OUT / "onecut-raw-5s.mp4"
        video.write_bytes(raw)
        metadata = result["metadata"]
        if metadata.get("continuity_mode") != "image":
            raise RuntimeError("Actual image conditioning not attested.")
        args = ["ffprobe", "-v", "error", "-count_frames", "-show_streams",
                "-show_format", "-of", "json", str(video)]
        info = json.loads(subprocess.run(args, capture_output=True, text=True,
                          check=True, timeout=90).stdout)
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        if v["width"] != 768 or v["height"] != 1344 or abs(float(info["format"]["duration"])-121/24)>.2:
            raise RuntimeError("Unexpected video dimensions/duration")
        subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(video),
                        "-f", "null", "-"], capture_output=True, check=True, timeout=120)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video),
                        "-vf", "fps=1,scale=192:336,tile=5x1",
                        "-frames:v", "1", str(OUT / "result-contact-sheet.jpg")],
                       capture_output=True, check=True, timeout=120)
        receipt.update(status="real_i2v_technical_pass_visual_review_required",
                       metadata=metadata, output_sha256=hashlib.sha256(raw).hexdigest(),
                       observed_client_seconds=round(time.monotonic()-started,2),
                       output_frames=v.get("nb_read_frames"),
                       creative_review="NOT_AUTOMATED")
        print("Real 5-second I2V generated. Physical cut quality NOT automatically certified.")
    except BaseException as error:
        receipt.update(status="failed", error=str(error)[:1600],
                       observed_client_seconds=round(time.monotonic()-started,2))
        raise
    finally:
        if call is not None and not completed:
            try:
                call.cancel(terminate_containers=True)
                receipt["cancellation_requested"] = True
            except Exception as cancel_error:
                receipt["cancellation_error"] = str(cancel_error)
        save("render_receipt.json", receipt)


def mix_audio():
    raw = OUT / "onecut-raw-5s.mp4"
    if not raw.exists():
        raise RuntimeError("No rendered video: no audio mix.")
    receipt = json.loads((OUT / "render_receipt.json").read_text())
    if receipt.get("status") != "real_i2v_native_audio_technical_pass_visual_review_required":
        raise RuntimeError("Video not technically verified.")
    plan = json.loads((OUT / "plan.json").read_text())
    if hashlib.sha256(GLASS_WAV.read_bytes()).hexdigest() != plan["foley_sha256"]:
        raise RuntimeError("Foley sound changed")
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(raw)],
        capture_output=True, text=True, check=True, timeout=40).stdout)
    has_native = any(stream["codec_type"] == "audio" for stream in info["streams"])
    # The native track is a real part of the LTX multimodal output; include it
    # rather than replacing it with silent synthetic impulses. Real glass source
    # from Gravity Sound adds a small, controlled tactile accent at the edge.
    bed = ("[0:a]aformat=sample_rates=48000:channel_layouts=stereo,"
           "volume=1.5,alimiter=limit=0.88[bed];") if has_native else (
           "anullsrc=r=48000:cl=stereo,atrim=duration=5[bed];")
    filters = (bed +
        "[1:a]aresample=48000,aformat=channel_layouts=stereo,"
        "atrim=start=0:duration=1.2,afade=t=in:st=0:d=0.02,"
        "volume=0.18,adelay=2400|2400[crack];"
        "[bed][crack]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.93[a]")
    final = OUT / "onecut-asmr-mix-5s.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", str(raw),
        "-i", str(GLASS_WAV), "-filter_complex", filters,
        "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
        "-b:a", "256k", "-ar", "48000", "-ac", "2", "-t", "5",
        "-movflags", "+faststart", str(final)],
        capture_output=True, check=True, timeout=120)
    verified = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(final)],
        capture_output=True, text=True, check=True, timeout=60).stdout)
    if not any(s["codec_type"] == "audio" for s in verified["streams"]):
        raise RuntimeError("ASMR export has no audio.")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(final),
                    "-f", "null", "-"], capture_output=True, check=True, timeout=90)
    save("audio_report.json", {
        "native_audio_present": has_native,
        "real_recording": GLASS_URL,
        "credit": "Glass breaking by Gravity Sound, via Wikimedia Commons, CC BY 4.0",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "modifications": "softened, delayed 2.4 seconds, mixed with native LTX audio",
        "source_sha256": plan["foley_sha256"],
        "approximate_crack_time_s": 2.4,
        "sync_quality": "PENDING FRAME-ACCURATE HUMAN REVIEW",
        "export": str(final), "status": "real_source_audio_export_technical_pass",
    })
    print("Native I2V sound + CC-BY real glass accent mixed. Creative audio review still required.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "render", "mix-audio"])
    parser.add_argument("--confirm-spend", default="non")
    args = parser.parse_args()
    if args.stage == "prepare":
        prepare()
    elif args.stage == "render":
        render(args.confirm_spend)
    else:
        mix_audio()
