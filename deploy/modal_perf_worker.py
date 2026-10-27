"""UGCv2 — Performance (remplacement de personne / transfert de mouvement)
sur Modal via WanGP headless, app `ugc-perf`.

Pourquoi WanGP comme substrat d'exécution : il intègre DÉJÀ, avec
quantifications adaptées au GPU et téléchargement automatique des poids,
Wan2.2 Animate 2 (août 2026, sans squelette intermédiaire) et SCAIL-2
(juin 2026), les deux meilleurs candidats actuels. Réécrire leurs pipelines
serait exactement le gaspillage que le brief interdit.
Le studio pilote WanGP par son mode headless officiel :
    python wgp.py --process settings.json --output-dir ./out
(docs/CLI.md du dépôt WanGP ; `--dry-run` valide sans générer.)

ÉTAT : NON EXÉCUTÉ sur GPU. Les clés média du fichier settings
(image_start / video_guide…) suivent le format des exports WanGP ; la
première session GPU doit commencer par `--mode validate` (dry-run, sans
génération) sur une scène S3, corriger si besoin, puis épingler le commit.
C'est écrit ici noir sur blanc pour ne pas vendre du vent.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import modal

APP_NAME = os.getenv("UGC_WANGP_APP", "ugc-perf")
GPU = os.getenv("UGC_MODAL_GPU_PERF", "L40S")
WANGP_REF = os.getenv("WANGP_REF", "main")  # épingler le commit après validation S3
app = modal.App(APP_NAME)
vol = modal.Volume.from_name("ugc-wangp-models", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .run_commands(
        f"git clone --depth 1 --branch {WANGP_REF} https://github.com/deepbeepmeep/WanGP /opt/WanGP",
        "cd /opt/WanGP && pip install -r requirements.txt",
        "cd /opt/WanGP && git rev-parse HEAD > /opt/wangp_commit.txt",
    )
)

MODELS = {"animate2": "defaults/animate2.json", "animate2_distilled": "defaults/animate2_distilled.json",
          "scail2_14B": "defaults/scail2_14B.json", "infinitetalk": "defaults/infinitetalk.json",
          "longcat_avatar_v1_5": "defaults/longcat_avatar_v1_5.json"}


def _build_settings(model: str, workdir: Path, params: dict) -> Path:
    tpl = Path("/opt/WanGP") / MODELS[model]
    settings = json.loads(tpl.read_text())
    settings.update({
        "prompt": params.get("prompt") or settings.get("prompt", ""),
        "seed": int(params.get("seed", 42)),
        # Clés média au format des exports WanGP (à confirmer par validate) :
        "image_start": str(workdir / "ref.png"),
        "image_refs": [str(workdir / "ref.png")],
        "video_source": str(workdir / "driving.mp4"),
        "control_video": str(workdir / "driving.mp4"),
        "video_guide": str(workdir / "driving.mp4"),
        "audio_source": str(workdir / "audio.wav") if (workdir / "audio.wav").exists() else "",
        "resolution": params.get("resolution", settings.get("resolution", "832x480")),
    })
    if model.startswith("scail2"):
        settings.setdefault("custom_settings", {})["scail2_animate_preprocessing"] = (
            "processed" if params.get("mode") == "replace" else "raw")
    out = workdir / "settings.json"
    out.write_text(json.dumps(settings, indent=2))
    return out


@app.function(image=image, timeout=900, volumes={"/models": vol})
def doctor() -> dict:
    commit = Path("/opt/wangp_commit.txt").read_text().strip() if Path("/opt/wangp_commit.txt").exists() else "?"
    present = {m: (Path("/opt/WanGP") / f).exists() for m, f in MODELS.items()}
    return {"app": APP_NAME, "wangp_commit": commit, "defaults_present": present,
            "models_on_volume": sorted(p.name for p in Path("/models").rglob("*.safetensors"))[:10],
            "note": "WanGP télécharge les poids adaptés au GPU au premier rendu."}


@app.function(image=image, gpu=GPU, cpu=8, memory=65536, timeout=5400,
              min_containers=0, max_containers=1, scaledown_window=2,
              volumes={"/models": vol, "/opt/WanGP/ckpts": vol})
def render_perf(video_b64: str, image_b64: str, params: dict) -> dict:
    model = str(params.get("model", "animate2"))
    if model not in MODELS:
        raise ValueError(f"Modèle inconnu : {model} (connus : {sorted(MODELS)})")
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ugc-perf-") as tmp:
        d = Path(tmp)
        (d / "driving.mp4").write_bytes(base64.b64decode(video_b64, validate=True))
        (d / "ref.png").write_bytes(base64.b64decode(image_b64, validate=True))
        settings = _build_settings(model, d, params)
        # Validation du format avant toute génération (échoue vite, coût ~nul)
        dry = subprocess.run(["python", "wgp.py", "--process", str(settings), "--dry-run"],
                             cwd="/opt/WanGP", capture_output=True, text=True, timeout=600)
        if dry.returncode != 0:
            raise RuntimeError("Settings WanGP refusés au dry-run (corriger _build_settings) :\n"
                               + (dry.stdout + dry.stderr)[-2000:])
        out_dir = d / "out"
        r = subprocess.run(["python", "wgp.py", "--process", str(settings),
                            "--output-dir", str(out_dir), "--verbose", "1"],
                           cwd="/opt/WanGP", capture_output=True, text=True, timeout=5200)
        found = sorted(out_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime) if out_dir.exists() else []
        if r.returncode != 0 or not found:
            raise RuntimeError(f"WanGP/{model} a échoué :\n{(r.stdout + r.stderr)[-2500:]}")
        vol.commit()
        out = found[-1]
        return {"video_b64": base64.b64encode(out.read_bytes()).decode(),
                "metadata": {"engine": f"wangp:{model}", "mode": params.get("mode"), "gpu": GPU,
                             "gpu_wall_seconds": round(time.perf_counter() - t0, 1),
                             "bytes": out.stat().st_size}}


@app.function(image=image, gpu=GPU, timeout=1800, volumes={"/models": vol})
def validate(model: str = "animate2") -> dict:
    """Dry-run WanGP sur des médias factices minuscules : valide le settings
    sans lancer de génération. Premier pas obligatoire de la session S3."""
    with tempfile.TemporaryDirectory(prefix="ugc-validate-") as tmp:
        d = Path(tmp)
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=512x512:r=16:d=1",
                        str(d / "driving.mp4")], capture_output=True, check=True)
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=gray:s=512x512:d=1",
                        "-frames:v", "1", str(d / "ref.png")], capture_output=True, check=True)
        settings = _build_settings(model, d, {"prompt": "test"})
        r = subprocess.run(["python", "wgp.py", "--process", str(settings), "--dry-run"],
                           cwd="/opt/WanGP", capture_output=True, text=True, timeout=1500)
        return {"model": model, "returncode": r.returncode,
                "tail": (r.stdout + r.stderr)[-1500:]}


@app.local_entrypoint()
def main(mode: str = "doctor", model: str = "animate2"):
    if mode == "doctor":
        print(doctor.remote())
    elif mode == "validate":
        print(validate.remote(model))
    else:
        raise SystemExit("Modes : doctor | validate.")


@app.function(image=image, gpu=GPU, cpu=8, memory=65536, timeout=5400,
              min_containers=0, max_containers=1, scaledown_window=2,
              volumes={"/models": vol, "/opt/WanGP/ckpts": vol})
def render_talk(audio_b64: str, video_b64: str, image_b64: str, params: dict) -> dict:
    """InfiniteTalk via WanGP (déployer ce fichier une 2e fois avec
    UGC_WANGP_APP=ugc-talk). Audio + photo OU vidéo, durée longue.
    NON VALIDÉ — benchmark S4 (challenger de LongCat pour le doublage long)."""
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ugc-talk-") as tmp:
        d = Path(tmp)
        (d / "audio.wav").write_bytes(base64.b64decode(audio_b64, validate=True))
        if video_b64:
            (d / "driving.mp4").write_bytes(base64.b64decode(video_b64, validate=True))
        if image_b64:
            (d / "ref.png").write_bytes(base64.b64decode(image_b64, validate=True))
        settings = _build_settings("infinitetalk", d, params)
        dry = subprocess.run(["python", "wgp.py", "--process", str(settings), "--dry-run"],
                             cwd="/opt/WanGP", capture_output=True, text=True, timeout=600)
        if dry.returncode != 0:
            raise RuntimeError("Settings WanGP refusés au dry-run :\n" + (dry.stdout + dry.stderr)[-2000:])
        out_dir = d / "out"
        r = subprocess.run(["python", "wgp.py", "--process", str(settings),
                            "--output-dir", str(out_dir), "--verbose", "1"],
                           cwd="/opt/WanGP", capture_output=True, text=True, timeout=5200)
        found = sorted(out_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime) if out_dir.exists() else []
        if r.returncode != 0 or not found:
            raise RuntimeError("WanGP/infinitetalk a échoué :\n" + (r.stdout + r.stderr)[-2500:])
        vol.commit()
        out = found[-1]
        return {"video_b64": base64.b64encode(out.read_bytes()).decode(),
                "metadata": {"engine": "wangp:infinitetalk", "gpu": GPU,
                             "gpu_wall_seconds": round(time.perf_counter() - t0, 1),
                             "bytes": out.stat().st_size}}
