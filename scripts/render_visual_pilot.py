import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import media
from backend.app.engines.base import EngineRequest
from backend.app.engines.visual import VisualEngine
from backend.app.visual_source import analyze_url, youtube_url

PRODUCTION = ROOT / "productions" / "US-FR-ADAPT-001-20261029"


class Context:
    def log(self, message, **kwargs):
        print(message, flush=True)

    def check_cancelled(self):
        pass


def main():
    parser = argparse.ArgumentParser(description="Pilote graphique original CPU UGCv2")
    parser.add_argument("--source-url", default="https://youtu.be/KSOxkhWs2Ic")
    parser.add_argument("--storyboard", type=Path)
    parser.add_argument("--out", type=Path, default=PRODUCTION / "VISUAL_OUTPUT")
    parser.add_argument("--narration", choices=["auto", "required", "cached", "none"], default="auto")
    parser.add_argument("--analyze-source", action="store_true", help="Analyse réseau isolée ; aucun média source dans le rendu")
    parser.add_argument("--analysis-only", action="store_true")
    args = parser.parse_args()
    url = youtube_url(args.source_url)
    if args.analyze_source or args.analysis_only:
        report = analyze_url(url, args.out)
        print("Analyse source : " + report["status"], flush=True)
    if args.analysis_only:
        return
    if args.storyboard:
        path = args.storyboard
    elif url == "https://www.youtube.com/watch?v=KSOxkhWs2Ic":
        path = PRODUCTION / "VISUAL_STORYBOARD.json"
    else:
        parser.error("Cette URL exige un storyboard FR original via --storyboard. L'adaptation sémantique universelle n'est pas implémentée.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if youtube_url(data["source_url"]) != url:
        parser.error("La référence du storyboard ne correspond pas à l'URL")
    result = VisualEngine().run(EngineRequest(kind="video", output_dir=args.out.resolve(),
        inputs={"storyboard": data}, params={"narration": args.narration}), Context())
    print(json.dumps(result.artifacts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
