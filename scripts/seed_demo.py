"""Amorce un studio de démonstration navigateur : personnage de référence
(photo synthétique fournie avec le dépôt) + une production par recette-clé,
prêtes à explorer dans l'UI. Aucun rendu GPU n'est lancé.
Usage : .venv/bin/python scripts/seed_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import db  # noqa: E402
from backend.app.config import get_settings  # noqa: E402


def main() -> None:
    db.init()
    settings = get_settings()
    ref_src = ROOT / "benchmarks" / "character_reference.png"
    dest = settings.data_dir / "uploads" / "character_reference.png"
    dest.write_bytes(ref_src.read_bytes())
    existing = db.find("characters", "name = ?", ("Élise — personnage de démonstration",))
    if existing:
        print("Déjà amorcé."); return
    asset = db.insert("assets", {"id": db.new_id("asset"), "project_id": None,
                                 "name": "character_reference.png", "kind": "image",
                                 "path": str(dest), "mime": "image/png", "role": "character_ref",
                                 "rights_note": "Photo de référence fournie avec le dépôt (benchmarks). À confirmer avant usage client.",
                                 "meta": {}, "created_at": db.now_iso()})
    char = db.insert("characters", {"id": db.new_id("char"), "name": "Élise — personnage de démonstration",
                                    "description": "Présentatrice bureau, lumière naturelle. Référence des benchmarks S1/S3/S4.",
                                    "ref_asset_id": asset["id"], "refs": [], "voice_id": None,
                                    "consent": 0, "created_at": db.now_iso(), "updated_at": db.now_iso()})
    now = db.now_iso()
    demos = [
        ("S4 · Avatar parlant — Élise présente un café", "avatar",
         "Élise présente un café de spécialité, ton complice, format TikTok.",
         "Bonjour ! Tu savais que ton café du matin pouvait changer toute ta journée ?"),
        ("S2 · Doublage — nouveau texte sur vidéo existante", "dub",
         "Importer une vidéo de parole autorisée, puis générer pour comparer MuseTalk vs LatentSync.",
         "Aujourd'hui, on vous montre comment gagner une heure par jour, sans effort."),
        ("S1 · Remplacement de visage", "face_swap",
         "Importer une vidéo autorisée : le studio conserve la performance et remplace le visage par Élise.", ""),
        ("S5 · Publicité complète 30 s (à créer après S1–S4)", "create",
         "Une application qui répond aux e-mails des artisans. Fini les relances oubliées. "
         "Les devis partent tout seuls, validés en un toucher. Trois cents artisans l'utilisent déjà. "
         "Essayez gratuitement cette semaine.", ""),
    ]
    for name, recipe, brief, dialogue in demos:
        p = db.insert("projects", {"id": db.new_id("prj"), "name": name, "brief": brief, "recipe": recipe,
                                   "format": "9:16", "quality": "production", "status": "draft",
                                   "settings": {"inputs": {"character_id": char["id"]}},
                                   "created_at": now, "updated_at": now})
        kind = {"avatar": "avatar", "dub": "lip_sync", "face_swap": "face_swap", "create": "b_roll"}[recipe]
        db.insert("shots", {"id": db.new_id("shot"), "project_id": p["id"], "idx": 0, "kind": kind,
                            "title": "Plan 1", "duration_s": 5.0, "dialogue": dialogue,
                            "prompt": "Face caméra, lumière naturelle de fenêtre, bureau clair, style UGC réaliste, caméra légèrement tenue main.",
                            "character_id": char["id"], "created_at": now, "updated_at": now})
    print(f"Amorcé : 1 personnage + {len(demos)} productions de démonstration (aucun rendu lancé).")


if __name__ == "__main__":
    main()
