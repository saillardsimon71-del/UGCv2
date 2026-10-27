"""Le routeur de production : intention -> étapes, moteurs, blocages, coût."""
from backend.app import recipes


def avail_all_except(*missing):
    from backend.app.engines.modal_remote import SPECS
    base = {name: (name not in missing, "indisponible test" if name in missing else "")
            for name in SPECS}
    base.update({"analysis": (True, ""), "qc": (True, ""), "director": (True, ""),
                 "ffmpeg_assembly": (True, "")})
    return base


def test_sept_recettes_exposees_sans_jargon_modele_dans_le_titre():
    rs = recipes.list_recipes()
    assert {r["id"] for r in rs} == {"face_swap", "person_replace", "motion_transfer",
                                     "dub", "avatar", "voice_only", "create"}
    for r in rs:
        assert r["label"] and r["promise"]


def test_face_swap_exige_video_et_personnage():
    p = {"recipe": "face_swap", "quality": "production", "settings": {"inputs": {}}}
    plan = recipes.plan_production(p, [], avail_all_except())
    missing = {m["id"] for m in plan["missing_inputs"]}
    assert missing == {"video_source", "character"}
    assert not plan["ready"]


def test_premium_face_swap_bascule_sur_animate2():
    p = {"recipe": "face_swap", "quality": "premium",
         "settings": {"inputs": {"video_asset_id": "a", "character_id": "c"}}}
    shots = [{"duration_s": 5, "source_asset_id": "a", "character_id": "c"}]
    plan = recipes.plan_production(p, shots, avail_all_except())
    swap = next(s for s in plan["steps"] if s["id"] == "swap")
    assert swap["engine"] == "modal_animate2"
    assert plan["requires_gpu_spend"] and plan["estimate"]["cost_usd"] > 0


def test_doublage_avec_audio_fourni_saute_la_voix():
    p = {"recipe": "dub", "quality": "production",
         "settings": {"inputs": {"video_asset_id": "a", "audio_asset_id": "w"}}}
    shots = [{"duration_s": 8, "source_asset_id": "a", "dialogue": ""}]
    plan = recipes.plan_production(p, shots, avail_all_except())
    voice = next(s for s in plan["steps"] if s["id"] == "voice")
    assert voice["skipped"] and "performance réelle" in voice["skip_reason"]


def test_moteur_indisponible_devient_blocage_lisible():
    p = {"recipe": "avatar", "quality": "production",
         "settings": {"inputs": {"character_id": "c"}}}
    shots = [{"duration_s": 4, "character_id": "c", "dialogue": "Bonjour"}]
    plan = recipes.plan_production(p, shots, avail_all_except("modal_longcat_avatar"))
    assert not plan["ready"]
    assert any("indisponible" in b for b in plan["blockers"])


def test_brouillon_doublage_utilise_musetalk():
    p = {"recipe": "dub", "quality": "brouillon", "settings": {"inputs": {"video_asset_id": "a"}}}
    shots = [{"duration_s": 5, "source_asset_id": "a", "dialogue": "Texte"}]
    plan = recipes.plan_production(p, shots, avail_all_except())
    assert next(s for s in plan["steps"] if s["id"] == "lipsync")["engine"] == "modal_musetalk"
