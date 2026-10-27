"""Routeur de production — « on commande une vidéo, pas un pipeline ».

L'utilisateur exprime une intention (recette) + fournit des sources + choisit
un niveau de qualité. Ce module décide, de façon explicable et testable :
  - quelles étapes exécuter, dans quel ordre ;
  - quel moteur pour chaque étape (mode avancé : visible et surchargeable) ;
  - ce qui bloque (source manquante, moteur indisponible, dépense GPU à confirmer) ;
  - l'estimation de coût GPU (hypothèses étiquetées, jamais présentées comme mesures).

Philosophie (brief) : partir d'une vraie performance filmée quand elle existe
et ne remplacer que ce qui doit l'être. D'où l'ordre des recettes : les
transformations d'une vidéo réelle passent avant la génération complète.
"""
from __future__ import annotations

from typing import Any

QUALITIES = {
    "brouillon": {"label": "Brouillon", "hint": "Rapide et économique — valider l'idée, le rythme, le texte."},
    "production": {"label": "Production", "hint": "Équilibre qualité/coût — le réglage client par défaut."},
    "premium": {"label": "Premium", "hint": "Meilleur moteur disponible + passe de finition — plans héros."},
}

# Estimation GPU par moteur : secondes GPU par seconde de vidéo produite.
# Hypothèses issues des mesures du précédent studio (LTX/LongCat) et de la
# littérature des dépôts ; à remplacer par nos mesures (benchmarks S1..S5).
GPU_S_PER_VIDEO_S = {
    "modal_facefusion": 1.5,      # inswapper + restauration, A10G
    "modal_animate2": 45.0,       # Wan Animate 2 distilled, L40S
    "modal_scail2": 90.0,         # SCAIL-2, plus lent, qualité challenge
    "modal_latentsync": 12.0,     # LatentSync 1.6 512px, L4/A10G
    "modal_musetalk": 1.2,        # MuseTalk temps réel ≈ brouillon
    "modal_longcat_avatar": 83.0, # mesuré : 308 s pour 3,72 s (A100, studio précédent)
    "modal_infinitetalk": 35.0,   # 720p littérature
    "modal_ltx": 22.0,            # mesuré ordre de grandeur : ~109 s / plan 5 s (L40S, chaud)
    "modal_chatterbox": 0.6,      # par seconde d'audio, T4/L4
    "modal_seedvc": 0.4,
    "edge_tts_fr": 0.0,
}

RECIPES: dict[str, dict[str, Any]] = {
    "face_swap": {
        "label": "Remplacer un visage",
        "icon": "🪞",
        "promise": "Votre vidéo réelle, avec un autre visage — expressions, regards, lumière et gestuelle d'origine conservés.",
        "needs": ["video_source", "character"],
        "needs_labels": {"video_source": "Vidéo à transformer", "character": "Visage (personnage)"},
        "steps": [
            {"id": "analyse", "label": "Analyse de la vidéo (visages, format, son)", "engine": "analysis"},
            {"id": "swap", "label": "Remplacement du visage + restauration peau", "engine": "modal_facefusion"},
            {"id": "qc", "label": "Contrôle qualité + revue humaine", "engine": "qc"},
        ],
        "premium_swap": {"swap": "modal_animate2",
                         "note": "Premium : remplacement par diffusion vidéo (Animate 2, mode remplacement) — meilleur sur cheveux/cou/occlusions, beaucoup plus lent."},
        "shot_kind": "face_swap",
    },
    "person_replace": {
        "label": "Remplacer la personne",
        "icon": "👤",
        "promise": "La performance filmée reste, la personne change — posture, déplacements, décor et cadrage conservés.",
        "needs": ["video_source", "character"],
        "needs_labels": {"video_source": "Vidéo de la performance", "character": "Nouvelle personne (photo)"},
        "steps": [
            {"id": "analyse", "label": "Analyse de la vidéo", "engine": "analysis"},
            {"id": "replace", "label": "Remplacement du personnage (Animate 2)", "engine": "modal_animate2"},
            {"id": "qc", "label": "Contrôle qualité + revue humaine", "engine": "qc"},
        ],
        "premium_swap": {"replace": "modal_scail2",
                         "note": "Premium : SCAIL-2 (sans squelette intermédiaire) — à comparer en benchmark S3 sur contacts/occlusions."},
        "shot_kind": "person_replace",
    },
    "motion_transfer": {
        "label": "Transférer une performance",
        "icon": "🎭",
        "promise": "Les mouvements d'une vidéo de référence, joués par votre personnage.",
        "needs": ["video_source", "character"],
        "needs_labels": {"video_source": "Vidéo de référence (mouvements)", "character": "Personnage (photo)"},
        "steps": [
            {"id": "analyse", "label": "Analyse de la référence", "engine": "analysis"},
            {"id": "transfer", "label": "Transfert de mouvement (Animate 2, mode animation)", "engine": "modal_animate2"},
            {"id": "qc", "label": "Contrôle qualité + revue humaine", "engine": "qc"},
        ],
        "premium_swap": {"transfer": "modal_scail2", "note": "Premium : SCAIL-2 end-to-end."},
        "shot_kind": "motion_transfer",
    },
    "dub": {
        "label": "Faire dire un autre texte",
        "icon": "💬",
        "promise": "Même vidéo, nouveau dialogue — voix de votre choix et lèvres resynchronisées proprement.",
        "needs": ["video_source", "dialogue_or_audio"],
        "needs_labels": {"video_source": "Vidéo de parole", "dialogue_or_audio": "Nouveau texte ou nouvel audio"},
        "steps": [
            {"id": "analyse", "label": "Analyse de la vidéo", "engine": "analysis"},
            {"id": "voice", "label": "Voix du nouveau dialogue (synthèse ou conversion)", "engine": "modal_chatterbox", "skip_if": "audio_fourni"},
            {"id": "lipsync", "label": "Synchronisation labiale (LatentSync 1.6)", "engine": "modal_latentsync"},
            {"id": "qc", "label": "Contrôle qualité + revue humaine", "engine": "qc"},
        ],
        "draft_swap": {"lipsync": "modal_musetalk", "note": "Brouillon : MuseTalk (rapide) pour valider le texte avant la passe LatentSync."},
        "shot_kind": "lip_sync",
    },
    "avatar": {
        "label": "Avatar parlant",
        "icon": "🎙️",
        "promise": "Une photo devient une personne qui parle face caméra — regard, respiration, micro-mouvements, pas seulement la bouche.",
        "needs": ["character", "dialogue_or_audio"],
        "needs_labels": {"character": "Personnage (photo)", "dialogue_or_audio": "Texte à dire ou audio enregistré"},
        "steps": [
            {"id": "voice", "label": "Voix (synthèse clonée ou performance convertie)", "engine": "modal_chatterbox", "skip_if": "audio_fourni"},
            {"id": "avatar", "label": "Animation parlante (LongCat Avatar 1.5)", "engine": "modal_longcat_avatar"},
            {"id": "qc", "label": "Contrôle qualité + revue humaine", "engine": "qc"},
        ],
        "premium_swap": {"avatar": "modal_longcat_avatar", "note": "LongCat 1.5 déjà prouvé sur notre Modal ; InfiniteTalk en challenger pour le doublage vidéo long (benchmark S4)."},
        "shot_kind": "avatar",
    },
    "voice_only": {
        "label": "Voix seule",
        "icon": "🗣️",
        "promise": "Un texte devient une voix humaine crédible, ou votre enregistrement change de timbre en gardant votre jeu.",
        "needs": ["dialogue_or_audio"],
        "needs_labels": {"dialogue_or_audio": "Texte, ou enregistrement à convertir"},
        "steps": [
            {"id": "voice", "label": "Synthèse (texte) ou conversion de timbre (audio)", "engine": "modal_chatterbox"},
            {"id": "qc", "label": "Écoute et validation", "engine": "qc"},
        ],
        "shot_kind": "voice_only",
    },
    "create": {
        "label": "Créer de zéro",
        "icon": "🎬",
        "promise": "Un brief devient une vidéo complète : storyboard, plans, voix, montage, sous-titres.",
        "needs": ["brief"],
        "needs_labels": {"brief": "Brief créatif"},
        "steps": [
            {"id": "storyboard", "label": "Storyboard (directeur créatif)", "engine": "director"},
            {"id": "plans", "label": "Génération des plans (vidéo et/ou avatar, plan par plan)", "engine": "modal_ltx"},
            {"id": "montage", "label": "Montage, sous-titres, mixage, loudness", "engine": "ffmpeg_assembly"},
            {"id": "qc", "label": "Contrôle qualité + revue humaine", "engine": "qc"},
        ],
        "shot_kind": "b_roll",
    },
}


def list_recipes() -> list[dict[str, Any]]:
    return [{"id": k, **{kk: vv for kk, vv in v.items() if kk != "steps"}, "steps": v["steps"]}
            for k, v in RECIPES.items()]


def plan_production(project: dict[str, Any], shots: list[dict[str, Any]],
                      available: dict[str, tuple[bool, str]]) -> dict[str, Any]:
    """Plan d'exécution explicable pour un projet : étapes, moteurs, blocages, coût estimé."""
    recipe_id = project.get("recipe") or "create"
    recipe = RECIPES.get(recipe_id, RECIPES["create"])
    quality = project.get("quality") or "production"
    settings = project.get("settings") or {}
    inputs = settings.get("inputs") or {}

    steps = []
    for s in recipe["steps"]:
        step = dict(s)
        # Choix du moteur selon qualité (règles documentées dans DECISIONS_ENGINES.md)
        if quality == "premium" and "premium_swap" in recipe and s["id"] in recipe["premium_swap"]:
            step["engine"] = recipe["premium_swap"][s["id"]]
            step["quality_note"] = recipe["premium_swap"].get("note", "")
        if quality == "brouillon" and "draft_swap" in recipe and s["id"] in recipe.get("draft_swap", {}):
            step["engine"] = recipe["draft_swap"][s["id"]]
            step["quality_note"] = recipe["draft_swap"].get("note", "")
        # Saut d'étape si l'audio est fourni (on ne régénère pas une vraie performance)
        skipped = s.get("skip_if") == "audio_fourni" and bool(inputs.get("audio_asset_id"))
        ok, reason = available.get(step["engine"], (True, ""))
        step.update({"skipped": skipped,
                     "skip_reason": "Audio fourni par l'utilisateur — performance réelle conservée" if skipped else "",
                     "available": ok, "blocker": "" if ok else reason})
        steps.append(step)

    # Sources manquantes
    missing = []
    for need in recipe["needs"]:
        present = {
            "video_source": bool(inputs.get("video_asset_id") or any(s.get("source_asset_id") for s in shots)),
            "character": bool(inputs.get("character_id") or any(s.get("character_id") for s in shots)),
            "dialogue_or_audio": bool(inputs.get("audio_asset_id") or any((s.get("dialogue") or "").strip() for s in shots)),
            "brief": bool((project.get("brief") or "").strip()),
        }.get(need, True)
        if not present:
            missing.append({"id": need, "label": recipe["needs_labels"].get(need, need)})

    # Estimation (hypothèses étiquetées)
    total_s = sum(float(s.get("duration_s") or 5) for s in shots) or float(inputs.get("duration_s") or 10)
    gpu_seconds = 0.0
    for step in steps:
        if not step["skipped"]:
            gpu_seconds += GPU_S_PER_VIDEO_S.get(step["engine"], 0.0) * total_s
    from .config import get_settings
    rate = get_settings().rate_for("modal", "L40S")
    blockers = [f"Source manquante : {m['label']}" for m in missing]
    blockers += [f"{s['label']} — {s['blocker']}" for s in steps if not s["available"] and not s["skipped"]]
    gpu_steps = [s for s in steps if not s["skipped"] and GPU_S_PER_VIDEO_S.get(s["engine"], 0) > 0]
    return {
        "recipe": recipe_id, "label": recipe["label"], "quality": quality,
        "steps": steps, "missing_inputs": missing, "blockers": blockers,
        "ready": not blockers,
        "requires_gpu_spend": bool(gpu_steps),
        "estimate": {"video_seconds": round(total_s, 1), "gpu_seconds": round(gpu_seconds),
                     "cost_usd": round(gpu_seconds / 3600 * rate, 2),
                     "basis": "Hypothèses GPU_S_PER_VIDEO_S (recipes.py) — à remplacer par les mesures des benchmarks S1..S5."},
    }
