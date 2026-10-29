#!/usr/bin/env python3
"""One cut, one image, one Modal I2V call. Never execute more than once."""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO))
from deploy.modal_ltx_worker import validate, build_graph

SRC = ROOT / "ASSETS/shot-02-firstframe.png"
EXPECTED_SHA = "4516129d092c691843c50fcdabc89640837c07bedb69547009f9d1fd5e6c6731"
OUT = ROOT / "EXPERIMENTS/i2v-output"
IMAGE = OUT / "onecut-opaque-first-frame.png"

PROMPT = (
    "One continuous premium photoreal glass-fruit ASMR macro shot, stationary top-down "
    "camera, wet polished black marble, exactly one deep sapphire-blue crystalline "
    "strawberry and one stainless-steel chef knife. Start EXACTLY from the reference "
    "image: the sharp knife edge is ALREADY TOUCHING the upper-right side of the "
    "intact strawberry. The strawberry has an opaque reflective blue glass shell, "
    "and the hidden core is not visible from outside. "
    "The knife immediately executes ONE deliberate firm uninterrupted diagonal "
    "slicing stroke DOWN AND LEFT through the middle of the fruit. "
    "The steel blade visibly enters the object, continues through its center, "
    "and completes the cut; the glass fractures in a thin controlled line "
    "ONLY where the cutting edge travels. The object must visibly RESIST "
    "the blade as it passes. By three seconds the cut has gone fully through. "
    "The EXACT SAME original strawberry then opens into precisely TWO matching "
    "half-pieces separated by a narrow gap. Fresh flat cut surfaces tilt upward "
    "to reveal a brilliant miniature cyan-and-violet spiral galaxy embedded "
    "inside the crystal, sparkling stars and pearl-like points of light. "
    "The reveal happens ONLY AFTER the blade splits the shell. "
    "Both solid halves rest on the same marble, gravity settles them naturally, "
    "and the knife lifts slightly after the cut is completed. "
    "Five seconds total. No camera motion, no jump cuts, no reset, "
    "no invisible cuts, no second knife, no duplicated strawberries, "
    "no new objects, no extra slices, no hands, no molten glass, "
    "no fruit juice, no violent explosion, no floating fragments, no text. "
    "Keep original studio lighting, coherent shadows, crisp rigid materials, "
    "and one physically readable blade-to-fruit interaction."
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
    # Mask exclusively the verified silhouette of the crystal berry. Knife, leaves,
    # marble and lighting remain completely unchanged. No synthetic placeholder.
    polygon = [
        (287,455),(255,469),(209,506),(178,559),(171,623),(183,687),
        (217,768),(254,850),(303,940),(344,980),(385,995),(429,979),
        (478,916),(531,814),(576,698),(602,602),(593,546),(565,492),
        (519,463),(497,454),
    ]
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).polygon(polygon, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(4))
    a = np.asarray(im, dtype=np.float32)
    lum = a.max(axis=2)
    tint = np.empty_like(a)
    tint[:, :, 0] = 10 + 0.10 * lum
    tint[:, :, 1] = 29 + 0.19 * lum
    tint[:, :, 2] = 91 + 0.35 * lum
    alpha = (np.asarray(m, dtype=np.float32) / 255.0) * .96
    out = a * (1.0 - alpha[:, :, None]) + tint * alpha[:, :, None]
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(out, 0, 255).astype("uint8")).save(IMAGE, optimize=True)
    png = IMAGE.read_bytes()
    if not png.startswith(b"\x89PNG\r\n\x1a\n") or not 150_000 < len(png) < 8_000_000:
        raise RuntimeError("Unusable output image; abort.")
    payload = {"prompt": PROMPT, "duration_s": 5, "aspect_ratio": "9:16",
               "seed": 2026102927, "image_strength": 0.72,
               "audio_mode": "silent", "trace_id": "fruit-cosmic-i2v-onecut-20261029"}
    request = validate(dict(payload, image_png_base64=base64.b64encode(png).decode()))
    graph = build_graph(request, output_prefix="i2v/onecut", uploaded_image="onecut.png")
    if graph.get("31", {}).get("class_type") != "LTXVImgToVideoInplace" or \
            any(node.get("class_type") == "LoadVideo" for node in graph.values()):
        raise RuntimeError("I2V graph invalid (source video would change mode).")
    receipt = {"status": "prepared_cpu_only", "source_sha256": EXPECTED_SHA,
               "first_frame_sha256": hashlib.sha256(png).hexdigest(),
               "first_frame_bytes": len(png), "prompt": PROMPT, "payload": payload,
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "render"])
    parser.add_argument("--confirm-spend", default="non")
    args = parser.parse_args()
    if args.stage == "prepare":
        prepare()
    else:
        render(args.confirm_spend)
