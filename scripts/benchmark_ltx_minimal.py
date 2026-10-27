import argparse
import base64
import contextlib
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROMPT = (
    "A photorealistic medium shot of a fictional woman in her forties with short "
    "curly auburn hair, wearing a dark blue linen shirt, standing in a warm sunlit "
    "kitchen with pale stone walls and wooden shelves. She holds a small recipe "
    "notebook and makes a relaxed explanatory hand gesture, then smiles naturally. "
    "The woman, her clothes, and the entire kitchen are different from the source "
    "person and office. Preserve the broad timing of the hand gesture. Real skin "
    "texture, stable hands and fingers, soft window light, steady camera. "
    "Natural quiet kitchen room tone, subtle fabric and notebook sounds. "
    "No intelligible dialogue."
)
RATE_PER_SECOND = 0.000542 + 8 * 0.0000131 + 64 * 0.00000222


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--use-checkout-worker", action="store_true")
    parser.add_argument("--confirm-spend", default="non")
    parser.add_argument("--max-wait", type=int, default=300)
    args = parser.parse_args()
    if not 1 <= args.max_wait <= 300:
        parser.error("--max-wait doit être compris entre 1 et 300 secondes.")
    if args.execute and args.confirm_spend != "oui":
        parser.error("Le calcul payant exige --execute --confirm-spend oui après autorisation humaine.")

    from deploy import modal_ltx_worker as worker

    content = args.source.read_bytes()
    payload = {"prompt": PROMPT, "duration_s": 6, "aspect_ratio": "16:9",
               "seed": 42, "audio_mode": "native", "trace_id": "ugcv2-proof-6s",
               "video_mp4_base64": base64.b64encode(content).decode("ascii")}
    request = worker.validate(payload)
    source = worker.probe_source_video(args.source, request)
    graph = worker.build_graph(request, output_prefix="proof/test", uploaded_video="source.mp4")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"status": "ready_not_executed",
              "app": "ugcv2-proof-v2v" if args.use_checkout_worker else "pvs-ltx", "function": "render_clip",
              "worker_source": "checkout_ephemeral" if args.use_checkout_worker else "existing_deployment",
              "workspace_expected": args.workspace, "source": str(args.source.resolve()),
              "source_sha256": hashlib.sha256(content).hexdigest(), "source_probe": source,
              "request": {k: v for k, v in request.items() if "base64" not in k},
              "graph_sha256": hashlib.sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest(),
              "estimated_usd_per_second": RATE_PER_SECOND,
              "estimate_60_to_300_seconds_usd": [round(RATE_PER_SECOND * t, 4) for t in (60, 300)],
              "cost_note": "Scénarios, pas un devis ni un plafond. Chargement, arrêt, stockage et facture à vérifier.",
              "remote_contract_note": "Graphe validé localement ; version et support V2V du worker déployé non attestés.",
              "source_audio": "absent", "output_audio": "génération native, pas une conservation de voix"}
    report_path = args.output_dir / "proof_report.json"

    def save():
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    save()
    if not args.execute:
        print(json.dumps({"status": report["status"], "report": str(report_path),
                          "remote_compute_started": False}, indent=2))
        return

    import modal

    account = subprocess.run([sys.executable, "-m", "modal", "token", "info"],
                             capture_output=True, text=True, check=True)
    match = re.search(r"^Workspace:\s+(\S+)", account.stdout, re.MULTILINE)
    if not match or match[1] != args.workspace:
        raise SystemExit("Workspace Modal différent ou non vérifiable : aucun calcul lancé.")
    context = (worker.app.run(name="ugcv2-proof-v2v", environment_name="main")
               if args.use_checkout_worker else contextlib.nullcontext())
    with context:
        function = (worker.render_clip if args.use_checkout_worker else
                    modal.Function.from_name("pvs-ltx", "render_clip", environment_name="main").hydrate())
        started = time.monotonic()
        call = function.spawn(payload)
        report.update(status="running", call_id=call.object_id)
        save()
        complete = False
        try:
            result = call.get(timeout=args.max_wait)
            complete = True
        except BaseException as exc:
            report.update(status="failed", error_type=type(exc).__name__,
                          observed_client_seconds=round(time.monotonic() - started, 2),
                          billing_actual_usd=None)
            raise
        finally:
            try:
                if not complete:
                    call.cancel(terminate_containers=True)
                    report["cancellation_requested"] = True
            finally:
                save()

    raw = args.output_dir / "after_raw.mp4"
    raw.write_bytes(base64.b64decode(result["video_base64"], validate=True))
    report.update(status="produced_pending_verification", metadata=result["metadata"],
                  observed_client_seconds=round(time.monotonic() - started, 2), billing_actual_usd=None)
    save()
    metadata = result["metadata"]
    if (metadata.get("continuity_mode") != "video"
            or (metadata.get("source_video") or {}).get("sha256") != report["source_sha256"]):
        report["status"] = "real_generation_source_conditioning_not_verified"
        save()
        raise RuntimeError("MP4 reçu mais conditionnement par la source non attesté par le worker.")
    probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams",
                            "-show_format", "-of", "json", str(raw)],
                           capture_output=True, text=True, check=True)
    info = json.loads(probe.stdout)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    if abs(float(info["format"]["duration"]) - 145 / 24) > 0.2:
        raise RuntimeError("Durée du résultat inattendue.")
    if not any(s["codec_type"] == "audio" for s in info["streams"]):
        raise RuntimeError("Résultat sans audio : preuve audiovisuelle incomplète.")
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-xerror", "-i", str(raw),
                    "-f", "null", "-"], capture_output=True, check=True)
    comparison = args.output_dir / "before_left_after_right.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", str(args.source), "-i", str(raw),
                    "-filter_complex", "[0:v]scale=672:384,setsar=1,fps=24[a];"
                    "[1:v]scale=672:384,setsar=1,fps=24[b];[a][b]hstack=inputs=2[v]",
                    "-map", "[v]", "-map", "1:a:0", "-shortest", "-c:v", "libx264",
                    "-crf", "18", "-c:a", "aac", str(comparison)], capture_output=True, check=True)
    from backend.app import media

    report.update(status="technically_verified_human_review_required", output_probe=info,
                  output_frames=int(video.get("nb_read_frames", 0)), loudness=media.loudness(raw),
                  cost_estimate_from_worker_seconds_usd=round(
                      RATE_PER_SECOND * float(result["metadata"].get("generation_seconds", 0)), 4),
                  comparison=str(comparison.resolve()),
                  review="Vérifier personne ET décor remplacés, gestes, mains, dents, scintillement et son ; noter /5.")
    save()
    print(json.dumps({"status": report["status"], "report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
