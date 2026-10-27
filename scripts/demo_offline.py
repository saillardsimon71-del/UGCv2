"""Démo hors-ligne : prouve la chaîne studio de bout en bout SANS GPU.

Crée un projet « Créer de zéro », génère le storyboard, produit les plans
(plaques SIMULATION étiquetées, faute de moteur IA dans cet environnement),
monte, sous-titre, normalise le loudness et exporte un vrai MP4 vertical.
Ce fichier prouve le montage/la timeline/le QC — il ne prouve RIEN sur la
qualité des modèles. Il est nommé demo_SIMULATION_* pour qu'on ne puisse
jamais le confondre avec un rendu client.

Usage : .venv/bin/python scripts/demo_offline.py
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import jobs  # noqa: E402
from backend.app.main import app  # noqa: E402


def wait(client, job_id, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("succeeded", "failed", "cancelled"):
            return j
        time.sleep(0.5)
    raise TimeoutError(job_id)


def main() -> None:
    jobs.start()
    c = TestClient(app)
    p = c.post("/api/projects", json={
        "name": "DÉMO Chaîne studio (simulation)",
        "brief": "Publicité verticale pour un café de spécialité. Ton complice, présentatrice face caméra. "
                 "Le café du matin change la journée. Grains torréfiés chaque semaine. Essayez le premier paquet.",
        "recipe": "create", "format": "9:16", "quality": "brouillon"}).json()
    c.post(f"/api/projects/{p['id']}/storyboard")
    p = c.get(f"/api/projects/{p['id']}").json()
    print(f"Storyboard : {len(p['shots'])} plans")
    for s in p["shots"]:
        c.patch(f"/api/shots/{s['id']}", json={"duration_s": 3.0})
        j = c.post(f"/api/shots/{s['id']}/generate", json={}).json()
        done = wait(c, j["id"])
        print(f"  Plan {s['idx']+1} « {s['title']} » : {done['status']} (simulé={done['simulated']})")
        assert done["status"] == "succeeded", done.get("error")
    j = c.post(f"/api/projects/{p['id']}/export", json={}).json()
    done = wait(c, j["id"])
    assert done["status"] == "succeeded", done.get("error")
    exp = c.get(f"/api/projects/{p['id']}").json()["exports"][0]
    dest = ROOT / "data" / "exports" / "demo_SIMULATION_chaine_studio.mp4"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(exp["path"], dest)
    print(f"Export : {dest} ({dest.stat().st_size//1024} Ko) · QC emballage : {exp['qc'].get('verdict')} "
          f"· contient_simulation={exp['spec'].get('contains_simulation')}")
    print("Rappel : cet export est 100 % plaques de test. Il valide jobs + montage + sous-titres + QC, pas les modèles.")


if __name__ == "__main__":
    main()
