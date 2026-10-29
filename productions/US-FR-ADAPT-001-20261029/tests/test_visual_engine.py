import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def board():
    return {
        "schema": "ugcv2.visual.v1",
        "source_url": "https://youtu.be/KSOxkhWs2Ic",
        "width": 1920, "height": 1080, "fps": 30, "transition_s": 0.35,
        "scenes": [{"id": "test", "template": "workflow", "duration_s": 3,
                    "title": "Une chaîne à vérifier", "eyebrow": "LE PRINCIPE",
                    "narration": "Une personne valide la réponse.",
                    "nodes": ["Demande", "Données", "IA", "Validation"]}],
    }


def test_source_media_and_false_execution_are_rejected():
    from backend.app.visuals import validate_storyboard
    for field, value in [("media_path", "https://youtube.com/source.mp4"),
                         ("executed", True)]:
        data = board()
        data["scenes"][0][field] = value
        with pytest.raises(ValueError):
            validate_storyboard(data)


def test_invalid_timing_and_overflow_rejected():
    from backend.app.visuals import validate_storyboard
    for change in [{"duration_s": 0}, {"title": "Mot " * 200},
                   {"nodes": ["A"] * 10}, {"duration_s": float("nan")}]:
        data = board()
        data["scenes"][0].update(change)
        with pytest.raises(ValueError):
            validate_storyboard(data)


def test_every_template_animates_and_keeps_disclosure_visible():
    from backend.app.visuals import VisualRenderer
    scenes = [board()["scenes"][0],
              {"template": "hook", "title": "Sept demandes. Un premier tri.",
               "messages": ["Fuite sous l'évier", "Demande de prix"]},
              {"template": "interface", "title": "Un brouillon, à valider",
               "request": "L'eau coule sous mon évier.", "category": "Plomberie",
               "draft": "Pouvez-vous préciser depuis quand ?"},
              {"template": "chart", "title": "Trois étapes à contrôler",
               "bars": [{"label": "Entrée", "value": 1}, {"label": "Validation", "value": 3}]},
              {"template": "recap", "title": "Vous gardez la décision",
               "items": ["Vérifier", "Corriger", "Valider"]}]
    renderer = VisualRenderer(board())
    for scene in scenes:
        early, later = renderer.frame(scene, 0.1, 3), renderer.frame(scene, 2.2, 3)
        assert later.size == (1920, 1080)
        assert ImageChops.difference(early, later).getbbox() is not None
        badge = later.crop((1260, 54, 1850, 123))
        assert len(badge.getcolors(1000000)) > 20


def test_voice_fits_without_clipping_and_transition_accounting():
    from backend.app.visuals import scene_timing
    timings, total = scene_timing(board(), [4.0])
    assert timings[0]["duration_s"] >= 4.6
    assert timings[0]["voice_start_s"] == 0.4
    assert total == timings[0]["duration_s"]
    data = board()
    data["scenes"].append(copy.deepcopy(data["scenes"][0]))
    timings, total = scene_timing(data, [0, 0])
    assert total == 5.65
    assert timings[1]["start_s"] == 2.65


def test_voice_finishes_before_long_transition_starts():
    from backend.app.visuals import scene_timing
    data = board()
    data["transition_s"] = 0.8
    data["scenes"].append(copy.deepcopy(data["scenes"][0]))
    timings, _ = scene_timing(data, [4, 4])
    assert timings[0]["voice_start_s"] + timings[0]["voice_duration_s"] <= timings[1]["start_s"]


def test_real_encode_and_engine_contract(tmp_path):
    from backend.app.engines.base import EngineRequest
    from backend.app.engines.visual import VisualEngine
    from backend.app import media

    class Context:
        def log(self, *args, **kwargs):
            pass

        def check_cancelled(self):
            pass

    data = board()
    data["scenes"][0]["duration_s"] = 1
    result = VisualEngine().run(EngineRequest(
        kind="video", output_dir=tmp_path, inputs={"storyboard": data},
        params={"narration": "none"}), Context())
    export = next(a for a in result.artifacts if a["kind"] == "export")
    info = media.probe(export["path"])
    assert (info.width, info.height, info.fps) == (1920, 1080, 30)
    assert abs(info.duration_s - 1) < 0.08
    assert result.usage.gpu_seconds == 0
    subprocess.run(["ffmpeg", "-v", "error", "-i", export["path"],
                    "-f", "null", "-"], check=True, capture_output=True)
    metrics_path = tmp_path / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["scenes"][0]["voice_duration_s"] = 0.2
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts/qc_visual_pilot.py"), str(tmp_path)],
                   capture_output=True)
    qc = json.loads((tmp_path / "qc.json").read_text(encoding="utf-8"))
    assert "missing_expected_voice" in qc["errors"]


def test_cancelled_render_produces_no_export(tmp_path):
    from backend.app.engines.base import EngineRequest, JobCancelled
    from backend.app.engines.visual import VisualEngine

    class Context:
        def check_cancelled(self):
            raise JobCancelled("test")

    with pytest.raises(JobCancelled):
        VisualEngine().run(EngineRequest(kind="video", output_dir=tmp_path,
                           inputs={"storyboard": board()}), Context())
    assert not list(tmp_path.glob("export*.mp4"))


def test_only_youtube_video_urls_are_accepted():
    from backend.app.visual_source import youtube_url
    assert youtube_url("https://youtu.be/KSOxkhWs2Ic") == "https://www.youtube.com/watch?v=KSOxkhWs2Ic"
    for url in ["https://evil.test/?v=KSOxkhWs2Ic", "file:///etc/passwd",
                "https://youtube.com.evil.test/watch?v=KSOxkhWs2Ic",
                "https://youtube.com/playlist?list=abc"]:
        with pytest.raises(ValueError):
            youtube_url(url)


def test_caption_analysis_preserves_source_timecodes():
    from backend.app.visual_source import caption_segments
    assert caption_segments({"events": [
        {"tStartMs": 1250, "dDurationMs": 2000, "segs": [{"utf8": "A trigger"}, {"utf8": " starts."}]},
        {"tStartMs": 4000, "segs": [{"utf8": "\n"}]}]}) == [
        {"start_s": 1.25, "duration_s": 2.0, "text": "A trigger starts."}]


def test_cache_cannot_silently_use_an_old_narration(tmp_path):
    from backend.app.visuals import local_narration
    (tmp_path / "voice").mkdir()
    (tmp_path / "voice" / "manifest.json").write_text(json.dumps({
        "narration_sha256": "outdated", "files": ["old.wav"]}), encoding="utf-8")
    with pytest.raises(ValueError, match="Cache voix"):
        local_narration(board(), tmp_path, "cached")


def test_formal_schema_and_runtime_accept_pilot():
    import jsonschema
    from backend.app.visuals import validate_storyboard
    schema = json.loads((ROOT / "backend/app/visual_storyboard.schema.json").read_text(encoding="utf-8"))
    pilot = json.loads((Path(__file__).parents[1] / "VISUAL_STORYBOARD.json").read_text(encoding="utf-8"))
    jsonschema.validate(pilot, schema)
    validate_storyboard(pilot)


@pytest.mark.parametrize("camera", ["push_in", "pan"])
def test_two_silent_scenes_with_camera_really_transition(tmp_path, camera):
    from backend.app.engines.base import EngineRequest
    from backend.app.engines.visual import VisualEngine
    from backend.app import media

    class Context:
        def log(self, *args, **kwargs):
            pass

        def check_cancelled(self):
            pass

    data = board()
    data["scenes"][0].update({"duration_s": 1, "camera": camera})
    second = copy.deepcopy(data["scenes"][0])
    second.update({"id": "second", "title": "Le contrôle humain"})
    data["scenes"].append(second)
    result = VisualEngine().run(EngineRequest(kind="video", output_dir=tmp_path,
        inputs={"storyboard": data}, params={"narration": "none"}), Context())
    info = media.probe(result.artifacts[0]["path"])
    assert abs(info.duration_s - 1.65) < 0.08
    assert not info.has_audio
