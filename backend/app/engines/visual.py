from pathlib import Path
import json

from .base import Engine, EngineInfo, EngineOutput, Usage


class VisualEngine(Engine):
    info = EngineInfo(name="cpu_visual", kind="video", label="Illustrations pédagogiques CPU",
        capabilities=["workflow", "interface", "hook", "chart", "recap", "local_voice"],
        requires_gpu=False, provider="local", gpu="CPU", simulated=False,
        verified=True, maturity="benchmark_passed",
        notes="Graphiques originaux. Les interfaces illustrées sont signalées à l'écran.")

    def run(self, request, ctx):
        from ..visuals import render_storyboard
        ctx.check_cancelled()
        data = request.inputs.get("storyboard")
        if data is None:
            path = Path(request.inputs["storyboard_path"])
            data = json.loads(path.read_text(encoding="utf-8"))
        output, metrics = render_storyboard(data, request.output_dir, ctx,
                                            request.params.get("narration", "auto"))
        result = EngineOutput(usage=Usage(provider="local", gpu="CPU", gpu_seconds=0,
            notes="Pillow + montage FFmpeg existant"), diagnostics=metrics)
        result.add(output, "export", "video/mp4", duration_s=metrics["duration_s"], size="1920x1080")
        result.add(request.output_dir / "metrics.json", "report", "application/json")
        return result
