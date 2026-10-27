"""Chaîne complète via l'API : projet -> génération (simulation étiquetée)
-> QC -> export montage réel ffmpeg. Prouve la plomberie studio, pas les modèles."""
import io

from conftest import wait_job


def test_system_honnête_sans_gpu(client):
    r = client.get("/api/system").json()
    assert any("Aucun moteur IA réel" in b for b in r["blockers"])
    sims = [e for e in r["engines"] if e["simulated"]]
    assert sims and all(e["name"].startswith("mock_") for e in sims)


def test_projet_avatar_generation_et_export(client):
    p = client.post("/api/projects", json={
        "name": "Test UGC", "brief": "Pub pour un café de spécialité, ton complice",
        "recipe": "avatar", "format": "9:16"}).json()
    shot = p["shots"][0]
    client.patch(f"/api/shots/{shot['id']}", json={
        "dialogue": "Tu savais que ton café du matin pouvait changer ta journée ?", "duration_s": 3.0})
    job = client.post(f"/api/shots/{shot['id']}/generate", json={}).json()
    done = wait_job(client, job["id"])
    assert done["status"] == "succeeded", done.get("error")
    # Sans GPU : le job doit dire qu'il a simulé — jamais de faux rendu
    assert done["simulated"] == 1
    assert "simulé" in (done["error"] or "").lower()

    p2 = client.get(f"/api/projects/{p['id']}").json()
    s2 = p2["shots"][0]
    assert s2["status"] == "generated"
    assert s2["selected_artifact"]
    assert s2["qc"]["verdict"] in ("pass", "review")
    videos = [t for t in s2["takes"] if t["kind"] == "video"]
    assert videos and videos[0]["meta"]["simulated"] is True

    job = client.post(f"/api/projects/{p['id']}/export", json={}).json()
    done = wait_job(client, job["id"])
    assert done["status"] == "succeeded", done.get("error")
    p3 = client.get(f"/api/projects/{p['id']}").json()
    assert len(p3["exports"]) == 1
    exp = p3["exports"][0]
    assert exp["spec"]["contains_simulation"] is True
    f = client.get(f"/api/exports/{exp['id']}/file")
    assert f.status_code == 200 and len(f.content) > 10_000


def test_storyboard_local(client):
    p = client.post("/api/projects", json={
        "name": "Storyboard", "brief": "Une app qui répond aux e-mails. Fini les relances oubliées.",
        "recipe": "create"}).json()
    r = client.post(f"/api/projects/{p['id']}/storyboard").json()
    assert r["source"] == "gabarit_local"
    assert len(r["shots"]) == 5
    assert r["shots"][0]["title"] == "Hook"


def test_upload_et_analyse_video(client, tmp_path):
    # Crée une vraie petite vidéo avec le moteur de plaques (via un plan généré)
    p = client.post("/api/projects", json={"name": "Analyse", "recipe": "face_swap"}).json()
    shot = p["shots"][0]
    client.patch(f"/api/shots/{shot['id']}", json={"duration_s": 2.0})
    job = client.post(f"/api/shots/{shot['id']}/generate", json={}).json()
    wait_job(client, job["id"])
    take = [t for t in client.get(f"/api/projects/{p['id']}").json()["shots"][0]["takes"]
            if t["kind"] == "video"][0]
    video_bytes = client.get(f"/api/artifacts/{take['id']}/file").content

    up = client.post("/api/assets/upload",
                     files={"file": ("source.mp4", io.BytesIO(video_bytes), "video/mp4")},
                     data={"project_id": p["id"], "role": "video_source",
                           "rights_note": "vidéo de test générée par nos soins"}).json()
    job = client.post(f"/api/assets/{up['id']}/analyse").json()
    done = wait_job(client, job["id"])
    assert done["status"] == "succeeded", done.get("error")
    assets = client.get("/api/assets").json()
    analysed = next(a for a in assets if a["id"] == up["id"])
    assert analysed["meta"]["analysis"]["media"]["width"] == 720
    assert len(analysed["meta"]["analysis"]["thumbnails"]) >= 1


def test_depense_gpu_jamais_implicite(client):
    """Sans confirm_spend, un moteur Modal (s'il était dispo) refuse ; ici on
    vérifie le garde-fou unitaire du payload."""
    from backend.app.engines.modal_remote import ModalEngine
    from backend.app.engines.base import EngineRequest
    from pathlib import Path
    eng = ModalEngine("modal_ltx")
    req = EngineRequest(kind="video", output_dir=Path("/tmp"), params={"confirm_spend": False})
    class Ctx:
        def log(self, *a, **k): pass
        def check_cancelled(self): pass
    try:
        eng.run(req, Ctx())
        raised = False
    except ValueError as exc:
        raised = "non confirmée" in str(exc)
    assert raised
