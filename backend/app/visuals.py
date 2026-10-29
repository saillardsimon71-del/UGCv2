from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import graphics, media

TEMPLATES = {"hook", "workflow", "interface", "chart", "recap"}
BASE_FIELDS = {"id", "template", "duration_s", "title", "eyebrow", "narration", "camera"}
FIELDS = {
    "hook": {"messages", "count"},
    "workflow": {"nodes", "note"},
    "interface": {"request", "category", "draft", "city"},
    "chart": {"bars", "unit", "note"},
    "recap": {"items", "note"},
}
BG, PANEL, EDGE = "#101E25", "#1A2C34", "#34464D"
WHITE, MUTED, MINT, AMBER = "#F5F3E9", "#B5C6CB", "#9DE7CB", "#F4C581"


def validate_storyboard(data):
    if set(data) - {"schema", "source_url", "width", "height", "fps", "transition_s", "scenes"}:
        raise ValueError("Storyboard : champs inconnus ou média externe interdit")
    if data.get("schema") != "ugcv2.visual.v1":
        raise ValueError("Schéma visuel non pris en charge")
    if (data.get("width"), data.get("height"), data.get("fps")) != (1920, 1080, 30):
        raise ValueError("Le profil v1 est 1920x1080 à 30 fps")
    transition = data.get("transition_s", 0.35)
    if type(transition) not in (int, float) or not math.isfinite(transition) or not 0 <= transition <= 0.8:
        raise ValueError("Transition invalide")
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 60:
        raise ValueError("Entre 1 et 60 scènes requises")
    ids = []
    for scene in scenes:
        if not isinstance(scene, dict) or not isinstance(scene.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", scene["id"]):
            raise ValueError("Identifiant de scène invalide")
        ids.append(scene["id"])
        if scene.get("camera", "none") not in {"none", "push_in", "pan"}:
            raise ValueError("Mouvement de caméra inconnu")
        kind = scene.get("template")
        if kind not in TEMPLATES or set(scene) - BASE_FIELDS - FIELDS[kind]:
            raise ValueError("Template inconnu ou champ interdit (aucune exécution simulée)")
        duration = scene.get("duration_s")
        if type(duration) not in (int, float) or not math.isfinite(duration) or not max(0.9, transition * 2) <= duration <= 60:
            raise ValueError("Durée de scène invalide")
        if not isinstance(scene.get("title"), str) or not 1 <= len(scene["title"]) <= 85:
            raise ValueError("Titre requis, 85 caractères maximum")
        for key, limit in [("eyebrow", 36), ("narration", 1500), ("request", 210),
                           ("draft", 210), ("category", 32), ("city", 32), ("note", 110), ("unit", 90)]:
            if key in scene and (not isinstance(scene[key], str) or len(scene[key]) > limit):
                raise ValueError(f"Texte trop long ou invalide : {key}")
        if kind in {"workflow", "recap", "hook"}:
            key, maximum = {"workflow": ("nodes", 4), "recap": ("items", 3), "hook": ("messages", 3)}[kind]
            values = scene.get(key, [])
            if not isinstance(values, list) or not 1 <= len(values) <= maximum or any(not isinstance(v, str) or len(v) > 38 for v in values):
                raise ValueError(f"Liste invalide : {key}")
        if kind == "hook" and (type(scene.get("count", 7)) is not int or not 1 <= scene.get("count", 7) <= 99):
            raise ValueError("Compteur hors limites")
        if kind == "interface" and not all(scene.get(key) for key in ("request", "category", "draft")):
            raise ValueError("Interface : demande, catégorie et brouillon requis")
        if kind == "chart":
            bars = scene.get("bars", [])
            if not isinstance(bars, list) or not 1 <= len(bars) <= 4:
                raise ValueError("Graphique : 1 à 4 barres requises")
            for bar in bars:
                if set(bar) != {"label", "value"} or not isinstance(bar["label"], str) or len(bar["label"]) > 25:
                    raise ValueError("Barre invalide")
                value = bar["value"]
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1000000:
                    raise ValueError("Valeur de graphique invalide")
    if len(set(ids)) != len(ids):
        raise ValueError("Identifiants de scène dupliqués")
    # Layout validation uses actual font metrics before any expensive encoding.
    renderer = VisualRenderer(data)
    for scene in scenes:
        renderer.frame(scene, scene["duration_s"] + 1, scene["duration_s"])
    return data


def ease(value):
    value = max(0.0, min(1.0, value))
    return 1 - (1 - value) ** 3


class VisualRenderer:
    def __init__(self, storyboard):
        self.width, self.height = storyboard["width"], storyboard["height"]
        candidates = [os.environ.get("STUDIO_VISUAL_FONT", ""),
                      "C:/Windows/Fonts/segoeui.ttf",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        self.font_path = next((p for p in candidates if p and Path(p).is_file()), None)
        if not self.font_path:
            raise ValueError("Police absente : définir STUDIO_VISUAL_FONT vers un fichier TTF")
        bold = str(Path(self.font_path).with_name("segoeuib.ttf")) if "segoeui" in self.font_path else self.font_path.replace(".ttf", "-Bold.ttf")
        self.bold_path = bold if Path(bold).exists() else self.font_path
        self.fonts = {}
        self.base = Image.new("RGB", (self.width, self.height), BG)
        draw = ImageDraw.Draw(self.base)
        for x in range(80, self.width, 80):
            draw.line((x, 180, x, 900), fill="#172A32")
        for y in range(180, 920, 80):
            draw.line((80, y, 1840, y), fill="#172A32")
        draw.line((80, 160, 1840, 160), fill=EDGE, width=2)

    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = ImageFont.truetype(self.bold_path if bold else self.font_path, size)
        return self.fonts[key]

    def text(self, draw, xy, value, size=32, color=WHITE, bold=False, max_width=None):
        font = self.font(size, bold)
        if max_width and draw.textlength(value, font=font) > max_width:
            raise ValueError(f"Texte hors cadre : {value}")
        draw.text(xy, value, font=font, fill=color, anchor="lt")

    def paragraph(self, draw, xy, value, width, size=34, color=WHITE, lines=4):
        words, rows, current = value.split(), [], ""
        for word in words:
            candidate = (current + " " + word).strip()
            if draw.textlength(candidate, font=self.font(size)) <= width:
                current = candidate
            else:
                if not current:
                    raise ValueError(f"Mot hors cadre : {word}")
                rows.append(current)
                current = word
        if current:
            rows.append(current)
        if len(rows) > lines or any(draw.textlength(row, font=self.font(size)) > width for row in rows):
            raise ValueError(f"Paragraphe hors cadre : {value}")
        for index, row in enumerate(rows):
            self.text(draw, (xy[0], xy[1] + index * size * 1.35), row, size, color)

    def card(self, draw, box, fill=PANEL, outline=EDGE):
        draw.rounded_rectangle(box, radius=24, fill=fill, outline=outline, width=2)

    def icon(self, draw, center, kind, color=MINT):
        x, y = center
        if kind == "mail":
            draw.rounded_rectangle((x - 23, y - 16, x + 23, y + 16), radius=5, outline=color, width=3)
            draw.line([(x - 21, y - 13), (x, y + 2), (x + 21, y - 13)], fill=color, width=3)
        elif kind == "person":
            draw.ellipse((x - 9, y - 23, x + 9, y - 5), outline=color, width=3)
            draw.arc((x - 22, y - 4, x + 22, y + 30), 180, 360, fill=color, width=3)
        elif kind == "spark":
            draw.polygon([(x, y - 25), (x + 7, y - 7), (x + 25, y),
                          (x + 7, y + 7), (x, y + 25), (x - 7, y + 7),
                          (x - 25, y), (x - 7, y - 7)], outline=color, width=3)
        else:
            for dy in (-15, 0, 15):
                draw.line((x - 22, y + dy, x + 22, y + dy), fill=color, width=3)

    def frame(self, scene, t, duration, index=0, count=1):
        image = self.base.copy()
        draw = ImageDraw.Draw(image)
        self.text(draw, (80, 72), "ATELIER / AUTOMATISATION", 27, MINT, True)
        self.text(draw, (80, 113), "LE TUTORIEL FRANÇAIS", 18, MUTED)
        self.card(draw, (1260, 54, 1840, 126), fill="#263B3D", outline="#4A6D64")
        self.text(draw, (1283, 77), "ILLUSTRATION - DONNÉES FICTIVES", 25, MINT, True, 540)
        self.text(draw, (80, 202), f"{index + 1:02d} / {scene.get('eyebrow', 'LE PRINCIPE')}", 24, AMBER, True)
        title_y = 258 + int(16 * (1 - ease(t / 0.7)))
        if scene["template"] != "hook":
            self.text(draw, (80, title_y), scene["title"], 62, WHITE, True, 1750)
        getattr(self, scene["template"])(draw, scene, t, duration)
        self.text(draw, (80, 925), "EXEMPLE PÉDAGOGIQUE / AUCUN ENVOI AU CLIENT", 21, MUTED)
        draw.rounded_rectangle((80, 1062, 1840, 1068), radius=3, fill=EDGE)
        progress = (index + min(1, max(0, t / duration))) / count
        draw.rounded_rectangle((80, 1062, 80 + max(6, int(1760 * progress)), 1068), radius=3, fill=MINT)
        return image

    def hook(self, draw, scene, t, duration):
        self.paragraph(draw, (80, 290), scene["title"], 800, 86, lines=3)
        self.text(draw, (84, 636), "Comprendre. Trier. Préparer.", 34, MUTED)
        self.text(draw, (84, 702), "La décision reste humaine.", 34, MINT, True)
        for i, label in enumerate(scene["messages"]):
            p = ease((t - 0.25 - i * 0.25) / 0.7)
            x, y = 1080 + int((1 - p) * 800), 430 + i * 126
            self.card(draw, (x, y, x + 710, y + 100))
            self.icon(draw, (x + 50, y + 50), "mail")
            self.text(draw, (x + 97, y + 33), label, 30, WHITE, max_width=590)
        self.text(draw, (1080, 264), f"{scene.get('count', 7):02d}", 132, MINT, True)
        self.text(draw, (1280, 325), "nouvelles demandes", 32, MUTED)

    def workflow(self, draw, scene, t, duration):
        nodes = scene["nodes"]
        gap, node_width = 50, (1760 - (len(nodes) - 1) * 50) // len(nodes)
        active = min(len(nodes) - 1, int(max(0, t - 1) / max(1, (duration - 2) / len(nodes))))
        for i, label in enumerate(nodes):
            x = 80 + i * (node_width + gap)
            y = 466 + int(25 * (1 - ease((t - i * 0.2) / 0.8)))
            highlighted = i == active
            self.card(draw, (x, y, x + node_width, y + 220), outline=MINT if highlighted else EDGE)
            self.icon(draw, (x + 54, y + 56), ["mail", "data", "spark", "person"][i])
            self.text(draw, (x + 30, y + 120), label, 32, WHITE, True, node_width - 50)
            self.text(draw, (x + 30, y + 171), f"ÉTAPE {i + 1:02d}", 20, MINT if highlighted else MUTED)
            if i < len(nodes) - 1:
                yy = y + 110
                draw.line((x + node_width + 5, yy, x + node_width + gap - 5, yy), fill=MINT, width=3)
                phase = ((t * 0.5) - i * 0.2) % 1
                xx = x + node_width + 5 + int(phase * (gap - 10))
                draw.ellipse((xx - 5, yy - 5, xx + 5, yy + 5), fill=WHITE)
        self.paragraph(draw, (80, 785), scene.get("note", "Un déclencheur manuel. Une proposition de l'IA. Un contrôle humain."), 1720, 34, MUTED, 2)

    def interface(self, draw, scene, t, duration):
        self.card(draw, (80, 385, 1840, 868))
        draw.rounded_rectangle((80, 385, 1840, 447), radius=24, fill="#283E47")
        self.text(draw, (111, 405), "ATELIER SEINE / ASSISTANT DE TRI", 23, MUTED)
        self.text(draw, (1460, 405), "MAQUETTE ANIMÉE", 22, AMBER, True)
        draw.line((910, 470, 910, 839), fill=EDGE, width=2)
        self.text(draw, (118, 482), "01 / DEMANDE FICTIVE", 23, MINT, True)
        self.paragraph(draw, (118, 537), scene["request"], 735, 35, lines=4)
        self.text(draw, (118, 767), scene.get("city", "Rouen") + " / exemple inventé", 26, MUTED)
        self.text(draw, (952, 482), "02 / BROUILLON ILLUSTRATIF", 23, MINT, True)
        p = ease((t - 1) / 1.2)
        category = scene["category"]
        self.card(draw, (952, 531, 1766, 590), fill="#2B433F", outline="#456A5D")
        self.text(draw, (972, 547), category, 26, MINT, True)
        # Reveal a complete paragraph through a mask; no fake API response is claimed.
        words = scene["draft"].split()
        visible = " ".join(words[:int(len(words) * p)])
        self.paragraph(draw, (952, 618), visible, 770, 31, lines=3)
        self.card(draw, (952, 786, 1766, 841), fill="#493C2B", outline="#8A704B")
        self.text(draw, (976, 800), "VALIDATION HUMAINE REQUISE", 25, AMBER, True)

    def chart(self, draw, scene, t, duration):
        bars = scene["bars"]
        maximum = max([b["value"] for b in bars] + [1])
        self.text(draw, (80, 384), scene.get("unit", "ÉCHELLE ILLUSTRATIVE / SANS MESURE RÉELLE"), 23, AMBER)
        for i, bar in enumerate(bars):
            y = 464 + i * 88
            self.text(draw, (80, y + 13), bar["label"], 30, WHITE, max_width=410)
            draw.rounded_rectangle((550, y, 1740, y + 54), radius=12, fill=PANEL)
            length = int(1100 * bar["value"] / maximum * ease((t - i * 0.3) / 1.4))
            if length:
                draw.rounded_rectangle((550, y, 550 + length, y + 54), radius=12, fill=MINT if i < len(bars) - 1 else AMBER)
        self.paragraph(draw, (80, 834), scene.get("note", "Schéma explicatif, pas un résultat commercial."), 1720, 30, MUTED, 2)

    def recap(self, draw, scene, t, duration):
        for i, label in enumerate(scene["items"]):
            x, y = 80 + i * 600, 459 + int(35 * (1 - ease((t - i * 0.22) / 0.8)))
            self.card(draw, (x, y, x + 560, y + 230), outline=MINT if i == 2 else EDGE)
            self.text(draw, (x + 30, y + 28), f"0{i + 1}", 56, MINT, True)
            self.text(draw, (x + 30, y + 137), label, 38, WHITE, True, 500)
        self.paragraph(draw, (80, 785), scene.get("note", "Aucun prix, aucun délai et aucun envoi sans contrôle."), 1720, 34, MUTED, 2)


def scene_timing(data, voice_durations):
    timings, cursor = [], 0.0
    for scene, voice in zip(data["scenes"], voice_durations, strict=True):
        voice_window = voice + 0.4 + max(0.4, data.get("transition_s", 0.35))
        duration = math.ceil(round(max(scene["duration_s"], voice_window) * data["fps"], 8)) / data["fps"]
        timings.append({"id": scene["id"], "start_s": round(cursor, 4),
                        "duration_s": round(duration, 4), "voice_start_s": 0.4,
                        "voice_duration_s": round(voice, 4)})
        cursor += duration - data.get("transition_s", 0.35)
    return timings, round(cursor + data.get("transition_s", 0.35), 4)


def local_narration(data, out_dir, mode="auto"):
    if mode == "none":
        return [None] * len(data["scenes"]), {"status": "disabled", "provider": "none"}
    signature = hashlib.sha256(json.dumps([s.get("narration", "") for s in data["scenes"]],
                                          ensure_ascii=False).encode()).hexdigest()
    cache_manifest = out_dir / "voice" / "manifest.json"
    if cache_manifest.exists():
        metadata = json.loads(cache_manifest.read_text(encoding="utf-8-sig"))
        if metadata.get("narration_sha256") == signature:
            paths = [out_dir / "voice" / Path(p).name if p else None for p in metadata["files"]]
            if all(path is None or path.is_file() for path in paths):
                return paths, {**metadata, "status": "cached"}
    if mode == "cached":
        raise ValueError("Cache voix absent ou différent de la narration du storyboard")
    if platform.system() != "Windows":
        if mode == "required":
            raise RuntimeError("La voix locale System.Speech exige Windows")
        return [None] * len(data["scenes"]), {"status": "unavailable", "reason": "System.Speech requires Windows"}
    script = Path(__file__).resolve().parents[2] / "scripts" / "visual_voice.ps1"
    manifest = out_dir / "voice_input.json"
    media.write_json(manifest, data)
    process = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(script),
                              "-InputJson", str(manifest), "-OutputDirectory", str(out_dir / "voice")],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if process.returncode:
        raise RuntimeError("Voix locale échouée : " + process.stderr[-1500:])
    metadata = json.loads(cache_manifest.read_text(encoding="utf-8-sig"))
    if metadata["status"] == "unavailable":
        if mode == "required":
            raise RuntimeError("Aucune voix française locale disponible")
        return [None] * len(data["scenes"]), metadata
    paths = [out_dir / "voice" / Path(p).name if p else None for p in metadata["files"]]
    metadata["files"] = [p.name if p else None for p in paths]
    metadata["narration_sha256"] = signature
    media.write_json(cache_manifest, metadata)
    return paths, metadata


def render_clip(renderer, scene, timing, output, voice_path, index, count, ctx):
    duration = timing["duration_s"]
    fps = 30
    cmd = [media.ffmpeg_bin(), "-y", "-v", "warning", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "1920x1080", "-r", str(fps), "-i", "pipe:0"]
    if voice_path:
        cmd += ["-i", str(voice_path), "-af", "adelay=400:all=1,apad", "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-an"]
    camera = scene.get("camera", "none")
    if camera == "push_in":
        cmd += ["-vf", "zoompan=z='min(1.015,1+on*0.00004)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=30"]
    elif camera == "pan":
        cmd += ["-vf", "scale=1952:1098,crop=1920:1080:x='16+10*sin(t/3)':y=9"]
    cmd += ["-t", str(duration), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-threads", "4", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    with output.with_suffix(".log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log)
        try:
            for frame in range(round(duration * fps)):
                if frame % fps == 0:
                    ctx.check_cancelled()
                image = renderer.frame(scene, frame / fps, duration, index, count)
                process.stdin.write(image.tobytes())
            process.stdin.close()
            if process.wait(timeout=120):
                raise media.MediaError(output.with_suffix(".log").read_text(encoding="utf-8")[-2000:])
        except BaseException:
            process.kill()
            process.wait()
            raise


def render_storyboard(data, out_dir, ctx, narration="auto"):
    from .engines.assembly import AssemblyEngine
    from .engines.base import EngineRequest

    ctx.check_cancelled()
    validate_storyboard(data)
    started = time.perf_counter()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    voice_paths, voice_meta = local_narration(data, out_dir, narration)
    durations = [media.probe(path).duration_s if path else 0 for path in voice_paths]
    timings, total = scene_timing(data, durations)
    renderer, clips = VisualRenderer(data), []
    for i, (scene, timing, voice) in enumerate(zip(data["scenes"], timings, voice_paths, strict=True)):
        ctx.check_cancelled()
        ctx.log(f"Visuel {i + 1}/{len(timings)} : {scene['template']}", stage="visual")
        clip = out_dir / f"scene_{i + 1:02d}.mp4"
        render_clip(renderer, scene, timing, clip, voice, i, len(timings), ctx)
        renderer.frame(scene, min(2.5, timing["duration_s"] * 0.7), timing["duration_s"], i, len(timings)).save(out_dir / f"scene_{i + 1:02d}.jpg", quality=90)
        clips.append({"path": str(clip), "duration_s": timing["duration_s"]})
    if any(voice_paths):
        result = AssemblyEngine().run(EngineRequest(kind="assembly", output_dir=out_dir / "assembly",
            inputs={"clips": clips}, params={"format": "16:9", "fps": 30, "subtitles": False,
            "transitions": data.get("transition_s", 0.35) > 0, "transition_s": data.get("transition_s", 0.35)}), ctx)
        assembled = Path(next(a["path"] for a in result.artifacts if a["kind"] == "export"))
    else:
        # The existing assembly loudnorm fails on digital silence with FFmpeg 8.1.
        # A video-only path keeps that engine intact and emits no fake audio.
        assembled = out_dir / "silent_assembly.mp4"
        inputs, filters, previous = [], [], "0:v"
        for i, clip in enumerate(clips):
            inputs += ["-i", clip["path"]]
            if i:
                output_label = f"fade{i}"
                if data.get("transition_s", 0.35):
                    filters.append(f"[{previous}][{i}:v]xfade=duration={data.get('transition_s', 0.35)}:offset={timings[i]['start_s']}[{output_label}]")
                else:
                    filters.append(f"[{previous}][{i}:v]concat=n=2:v=1:a=0[{output_label}]")
                previous = output_label
        graph = ["-filter_complex", ";".join(filters)] if filters else []
        media.run_ffmpeg([*inputs, *graph, "-map", f"[{previous}]" if filters else previous,
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-threads", "4",
            "-t", str(total), "-movflags", "+faststart", str(assembled)])
    events = []
    for scene, timing, voice in zip(data["scenes"], timings, voice_paths, strict=True):
        if voice and scene.get("narration"):
            events += graphics.subtitle_events([{"start_s": timing["start_s"] + 0.4,
                "duration_s": timing["voice_duration_s"], "dialogue": scene["narration"]}], cue_max_chars=85)
    output = out_dir / "PILOTE_VISUAL_ENGINE_FR.mp4"
    if events:
        from .engines.assembly import _srt
        ass = graphics.build_ass(events, out_dir / "captions.ass", 1920, 1080,
            [graphics.AssStyle(name="Subtitle", font=renderer.font(34).getname()[0],
                size=34, margin_v=54, margin_l=100, margin_r=100, border_style=3,
                outline=9, back_colour="&H00251E10", outline_colour="&H00251E10")])
        # Relative filter path avoids platform-specific escaping in this new step.
        escaped = str(ass).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
        media.run_ffmpeg(["-i", str(assembled), "-vf", f"subtitles=filename='{escaped}'",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-threads", "4",
            "-c:a", "copy", "-movflags", "+faststart", str(output)], log_path=out_dir / "captions.log")
        (out_dir / "captions.srt").write_text(_srt(events), encoding="utf-8")
    else:
        shutil.copyfile(assembled, output)
    metrics = {"render_wall_s": round(time.perf_counter() - started, 3),
        "duration_s": total, "frames_expected": round(total * 30),
        "output_bytes": output.stat().st_size, "gpu_seconds": 0, "paid_api_calls": 0,
        "external_generation_cost_usd": 0, "electricity_cost": "not measured",
        "voice": voice_meta, "scenes": timings, "source_media_reused": False,
        "font_file": Path(renderer.font_path).name,
        "font_sha256": hashlib.sha256(Path(renderer.font_path).read_bytes()).hexdigest(),
        "storyboard_sha256": hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "python": platform.python_version(), "ffmpeg": media.ffmpeg_version()}
    media.write_json(out_dir / "metrics.json", metrics)
    return output, metrics
