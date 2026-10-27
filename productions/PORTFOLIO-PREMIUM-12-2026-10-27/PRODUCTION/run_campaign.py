import argparse
import base64
import hashlib
import json
import math
import os
import random
import signal
import subprocess
import time
import wave
from array import array
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RATE = 0.00078888
PILOTS = {"03-skincare-sensoriel", "05-architectural-living"}


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command(args, timeout=600):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(result.stderr[-6000:])
    return result.stdout


def probe(path):
    return json.loads(command(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))


def load_plan(film):
    if not film or "/" in film or "\\" in film:
        raise ValueError("Identifiant de film invalide")
    folder = ROOT / film
    return folder, json.loads((folder / "PRODUCTION_PLAN.json").read_text(encoding="utf-8"))


def check(film=None):
    folders = [ROOT / film] if film else sorted(ROOT.glob("[0-9][0-9]-*"))
    checked = 0
    for folder in folders:
        _, plan = load_plan(folder.name)
        if plan["workspace"] != "lucj76861" or plan["max_concurrent_gpu"] != 1 or plan["attempts_per_shot"] != 1:
            raise ValueError("Compte ou garde-fous du plan invalides")
        for required in ("BRIEF.md", "CREATIVE_DIRECTION.md", "STORYBOARD.md", "QUALITY_CHECKLIST.md", "COST_ESTIMATE.json"):
            if not (folder / required).is_file():
                raise ValueError("Fichier requis manquant : " + str(folder / required))
        for shot in plan["shots"]:
            source = shot["source"]
            image_path = folder / source["firstframe"]
            if hashlib.sha256(image_path.read_bytes()).hexdigest() != source["firstframe_sha256"]:
                raise ValueError("Image initiale modifiée : " + str(image_path))
            with Image.open(image_path) as image:
                if image.format != "PNG" or image.size != (768, 1344):
                    raise ValueError("Image initiale incompatible LTX")
            if "pexels.com/photo/" not in source["page"]:
                raise ValueError("Source non Pexels")
            payload = json.loads((folder / shot["payload_file"]).read_text(encoding="utf-8"))
            if payload["prompt"] != shot["prompt"] or payload["audio_mode"] != "silent" or payload["aspect_ratio"] != "9:16":
                raise ValueError("Payload différent du storyboard")
            checked += 1
        info = probe(folder / "ASSETS/music.mp3")
        if float(info["format"]["duration"]) <= plan["music"]["start_s"] + plan["target_duration_s"]:
            raise ValueError("Piste musicale trop courte")
    report = {"at": now(), "films": len(folders), "source_frames": checked, "result": "pass", "gpu_called": False}
    save(ROOT / "PRODUCTION/PREFLIGHT.json", report)
    print(json.dumps(report), flush=True)


def authorize(plan, confirm):
    if confirm != "oui":
        raise ValueError("Calcul refusé : --confirm-spend oui manquant")
    if not plan["executable"]:
        raise ValueError("Calcul refusé : " + str(plan["hold_reason"]))
    if plan["film_id"] not in PILOTS:
        approval_path = ROOT / "PRODUCTION/HUMAN_PILOT_APPROVAL.json"
        if not approval_path.is_file():
            raise ValueError("Série refusée : validation humaine des vrais pilotes requise")
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        if not approval.get("human_approved") or plan["film_id"] not in approval.get("allowed_films", []):
            raise ValueError("Film hors lot explicitement validé")
    review = json.loads((ROOT / "PRODUCTION/INPUT_REVIEW.json").read_text(encoding="utf-8"))
    if plan["film_id"] not in review["approved_for_pilot"]:
        raise ValueError("Images initiales non inspectées pour cette production")
    budget = json.loads((ROOT / "PRODUCTION/BUDGET.json").read_text(encoding="utf-8"))
    if budget["workspace"] != "lucj76861" or budget["workspace_monthly_usage_limit_usd"] != 20 or not budget["limit_verified_after_reload"]:
        raise ValueError("Protection budgétaire non vérifiée")


def render(film, shot_id, confirm):
    folder, plan = load_plan(film)
    authorize(plan, confirm)
    check(film)
    shot = next(s for s in plan["shots"] if s["shot_id"] == shot_id)
    if shot["app"] != "pvs-ltx" or shot["function"] != "render_clip":
        raise ValueError("Ce lanceur réutilise seulement le worker LTX déjà déployé ; avatars suspendus")
    receipt_path = folder / "REPORTS" / f"shot-{shot_id}-receipt.json"
    if receipt_path.exists() or (folder / shot["render_path"]).exists():
        raise ValueError("Tentative existante : aucune régénération automatique autorisée")
    import modal

    if modal.Workspace.from_context().hydrate().name != "lucj76861":
        raise ValueError("Workspace inattendu, arrêt avant calcul")
    function = modal.Function.from_name("pvs-ltx", "render_clip", environment_name="main").hydrate()
    stats = function.get_current_stats()
    if stats.num_running_inputs or stats.backlog:
        raise ValueError("Une fonction LTX est déjà active ; ne pas ajouter de concurrence")
    payload = json.loads((folder / shot["payload_file"]).read_text(encoding="utf-8"))
    png = (folder / shot["source"]["firstframe"]).read_bytes()
    payload["image_png_base64"] = base64.b64encode(png).decode("ascii")
    receipt = {"film": film, "shot": shot_id, "status": "starting", "started_at": now(), "workspace": "lucj76861",
               "app": "pvs-ltx", "function": "render_clip", "source_sha256": hashlib.sha256(png).hexdigest(),
               "submitted_parameters": {k:v for k,v in payload.items() if k != "image_png_base64"},
               "github_run_id": os.environ.get("GITHUB_RUN_ID"), "actual_billed_usd": None, "attempt": 1}
    save(receipt_path, receipt)
    call = None
    completed = False
    started = time.monotonic()

    def interrupted(signum, frame):
        raise KeyboardInterrupt("Annulation demandée")

    signal.signal(signal.SIGTERM, interrupted)
    try:
        call = function.spawn(payload)
        receipt.update(status="running", call_id=call.object_id)
        save(receipt_path, receipt)
        print(json.dumps({"film": film, "shot": shot_id, "call_id": call.object_id, "status": "running"}), flush=True)
        deadline = started + plan["client_deadline_per_shot_s"]
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Délai client atteint ; annulation, aucun nouvel essai")
            try:
                result = call.get(timeout=min(20, remaining))
                completed = True
                break
            except modal.exception.TimeoutError:
                print(f"{film}/{shot_id} : {round(time.monotonic()-started)} s d'attente", flush=True)
        raw = base64.b64decode(result["video_base64"], validate=True)
        path = folder / shot["render_path"]
        path.write_bytes(raw)
        metadata = result["metadata"]
        receipt.update(status="generated_pending_qc", completed_at=now(), client_wall_s=round(time.monotonic()-started, 3),
                       output_sha256=hashlib.sha256(raw).hexdigest(), output_bytes=len(raw), metadata=metadata,
                       partial_compute_estimate_usd=round(float(metadata.get("generation_seconds", 0))*RATE, 4),
                       cost_note="Estimation partielle des secondes retournées ; démarrage antérieur, dépassements RAM et facture non attestés")
        save(receipt_path, receipt)
        info = probe(path)
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        if video["width"] != 768 or video["height"] != 1344 or abs(float(info["format"]["duration"])-121/24) > .12:
            raise ValueError("Dimensions ou durée du vrai rendu inattendues")
        if metadata.get("continuity_mode") != "image":
            raise ValueError("Conditionnement image non attesté : ne pas substituer une simulation")
        command(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"])
        tags = info.get("format", {}).get("tags", {})
        embedded = "\n".join(str(v) for v in tags.values())
        receipt.update(status="technically_checked_visual_review_pending", output_probe=info,
                       image_conditioning_nodes_embedded="LTXVImgToVideoInplace" in embedded,
                       input_chain_note="SHA du PNG envoyé + reçu d'appel + continuity_mode=image ; comparer visuellement le premier photogramme, le worker ne retourne pas de SHA de l'image lue")
        save(receipt_path, receipt)
        command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(path), "-vf", "fps=4,scale=144:252,tile=7x3", "-frames:v", "1", str(folder / "REPORTS" / f"shot-{shot_id}-contact.jpg")])
        print(json.dumps({"saved": str(path), "status": receipt["status"], "partial_estimate_usd": receipt["partial_compute_estimate_usd"]}), flush=True)
    except BaseException as error:
        receipt.update(status="failed", error_type=type(error).__name__, error=str(error)[:2000], failed_at=now())
        raise
    finally:
        if call is not None and not completed:
            try:
                call.cancel(terminate_containers=True)
                receipt["cancellation_requested_at"] = now()
            except Exception as error:
                receipt["cancellation_error"] = str(error)[:1000]
        save(receipt_path, receipt)


def cancel(film):
    import modal

    if modal.Workspace.from_context().hydrate().name != "lucj76861":
        raise ValueError("Workspace inattendu")
    folder, _ = load_plan(film)
    for path in (folder / "REPORTS").glob("shot-*-receipt.json"):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if receipt.get("call_id") and receipt["status"] in ("starting", "running", "failed"):
            modal.FunctionCall.from_id(receipt["call_id"]).cancel(terminate_containers=True)
            receipt["cancellation_requested_at"] = now()
            save(path, receipt)
            print("Annulation demandée : " + receipt["call_id"], flush=True)


def sound_design(film, duration, path):
    rate = 48000
    samples = [0.0] * round(duration * rate)
    energetic = film.startswith(("01-", "07-", "08-"))
    glass = film.startswith(("02-", "03-", "04-", "12-"))
    events = [(.15, "impact" if energetic else "glass" if glass else "air", .13 if energetic else .045),
              (4.85, "air", .045), (5.12, "impact" if energetic else "glass" if glass else "air", .08 if energetic else .03),
              (9.85, "air", .04), (10.12, "glass" if glass else "air", .035), (14.92, "air", .05)]
    rng = random.Random(20261027)
    for start, kind, gain in events:
        event_duration = .45 if kind == "air" else .30
        low = 0.0
        for i in range(round(event_duration * rate)):
            t = i/rate
            noise = rng.uniform(-1, 1)
            low = .82*low + .18*noise
            if kind == "glass":
                value = (math.sin(2*math.pi*(1450*t-900*t*t))+.3*math.sin(2*math.pi*2850*t))*math.exp(-t*29)*min(t*1000, 1)
            elif kind == "impact":
                value = (.8*math.sin(2*math.pi*(92*t-65*t*t))+.5*low)*math.exp(-t*19)*min(t*1800, 1)
            else:
                value = (noise-low)*math.sin(math.pi*t/event_duration)**3*.55
            position = round(start*rate)+i
            if position < len(samples):
                samples[position] += gain*value
    pcm = array("h")
    for value in samples:
        level = round(max(-.99, min(.99, value))*32767)
        pcm.extend([level, level])
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())


def assemble(film):
    folder, plan = load_plan(film)
    if not plan["executable"]:
        raise ValueError("Film suspendu")
    prepared = folder / "REPORTS/EDIT"
    prepared.mkdir(exist_ok=True)
    paths = []
    for shot in plan["shots"]:
        src = folder / shot["render_path"]
        receipt = json.loads((folder / "REPORTS" / f"shot-{shot['shot_id']}-receipt.json").read_text(encoding="utf-8"))
        if receipt["status"] != "technically_checked_visual_review_pending" or hashlib.sha256(src.read_bytes()).hexdigest() != receipt["output_sha256"]:
            raise ValueError("Prise manquante ou non vérifiée ; aucune image fixe de remplacement")
        dst = prepared / f"shot-{shot['shot_id']}.mp4"
        command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-t", "5", "-vf", "fps=24,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "17", str(dst)])
        paths.append(dst)
    card = prepared / "endcard.mp4"
    command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(folder / "ASSETS/endcard.png"), "-t", "2.5", "-r", "24", "-vf", "setsar=1,format=yuv420p", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "17", str(card)])
    if film.startswith("08-"):
        timeline = [(0,0,1.5), (1,0,1), (0,1.5,1.25), (2,0,1.25), (1,1,1.5),
                    (2,1.25,1.75), (0,2.75,2.25), (1,2.5,2.5), (2,3,2)]
        recut = []
        for index, (source_index, start, duration) in enumerate(timeline):
            target = prepared / f"energy-{index:02d}.mp4"
            command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-i", str(paths[source_index]), "-t", str(duration), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", str(target)])
            recut.append(target)
        paths = recut
    paths.append(card)
    listing = prepared / "concat.txt"
    listing.write_text("".join("file '"+p.resolve().as_posix()+"'\n" for p in paths), encoding="utf-8")
    picture = prepared / "picture.mp4"
    command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(picture)])
    if plan["edit_structure"]:
        from graphics import AssStyle, Event, build_ass

        events = [Event(start=e["at"], end=e["until"], text=e["text"], style="AdCopy") for e in plan["edit_structure"]]
        overlay = build_ass(events, prepared / "ad-copy.ass", styles=[AssStyle(name="AdCopy", size=54, alignment=8, margin_v=165, outline=2.5)])
        escaped = str(overlay.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
        with_copy = prepared / "picture-with-copy.mp4"
        command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(picture), "-vf", f"subtitles=filename='{escaped}'", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", str(with_copy)])
        picture = with_copy
    effects = prepared / "sound-design.wav"
    sound_design(film, 17.5, effects)
    final, web = folder / plan["output"]["master"], folder / plan["output"]["web"]
    command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(picture), "-ss", str(plan["music"]["start_s"]), "-i", str(folder / "ASSETS/music.mp3"), "-i", str(effects),
             "-filter_complex", "[1:a]atrim=0:17.5,asetpts=PTS-STARTPTS,afade=t=in:d=0.15,afade=t=out:st=16.85:d=0.65,volume=0.8[m];[m][2:a]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9[a]",
             "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-t", "17.5", "-movflags", "+faststart", str(final)])
    command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(final), "-vf", "scale=720:1280:flags=lanczos", "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(web)])
    reports = []
    for path, dimensions in ((final, (1080,1920)), (web, (720,1280))):
        info = probe(path)
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
        if (video["width"],video["height"]) != dimensions or video["pix_fmt"] != "yuv420p" or video["codec_name"] != "h264" or audio["codec_name"] != "aac":
            raise ValueError("Format d'export incorrect")
        if abs(float(info["format"]["duration"])-17.5) > .1 or int(video["nb_frames"]) != 420 or audio["sample_rate"] != "48000":
            raise ValueError("Durée, cadence ou audio incorrects")
        command(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"])
        reports.append({"path": str(path.relative_to(ROOT)), "probe": info, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "full_decode": "pass"})
    command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "11", "-i", str(final), "-frames:v", "1", str(folder / "EXPORTS/THUMBNAIL.jpg")])
    command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(final), "-vf", "fps=2,scale=144:256,tile=7x5", "-frames:v", "1", str(folder / "REPORTS/FINAL-CONTACT.jpg")])
    meter = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(final), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
    (folder / "REPORTS/AUDIO-METER.txt").write_text(meter.stderr[-1800:], encoding="utf-8")
    save(folder / "REPORTS/TECHNICAL_REPORT.json", {"at": now(), "exports": reports, "native_render": "768x1344/24fps, 121 frames each", "master": "crop and upscale to 1080x1920, not native 1080p generation", "audio": "licensed music and original sound design; native LTX track excluded", "creative_verdict": "pending real-video review and human listening"})
    save(folder / "REPORTS/STATUS.json", {"film": film, "status": "real_final_mp4_technical_checks_passed", "quality": None,
         "actual_billed_usd": None, "final_mp4": str(final.relative_to(ROOT)), "review": "visual_and_critical_audio_review_pending", "publish": False,
         "github_run_id": os.environ.get("GITHUB_RUN_ID"), "defects": [], "warning": "Automatic checks do not validate artistic quality"})
    (folder / "EXPORTS/CREDITS.txt").write_text((folder / "ASSETS/CREDITS.txt").read_text(encoding="utf-8"), encoding="utf-8")
    print("MP4 réels et contrôles techniques enregistrés : " + str(final), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["check", "render", "assemble", "cancel"])
    parser.add_argument("--film")
    parser.add_argument("--shot", choices=["01", "02", "03"])
    parser.add_argument("--confirm-spend", default="non")
    args = parser.parse_args()
    if args.phase == "check":
        check(args.film)
    elif args.phase == "render":
        render(args.film, args.shot, args.confirm_spend)
    elif args.phase == "assemble":
        assemble(args.film)
    else:
        cancel(args.film)
