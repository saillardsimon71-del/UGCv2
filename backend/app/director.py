"""Directeur créatif : brief (français) -> storyboard de plans éditables.

Deux modes, même sortie validée :
- LLM OpenAI-compatible si une clé est configurée (JSON strict + 1 retry) ;
- gabarit local sinon : structure publicitaire éprouvée (Hook → Problème →
  Démonstration → Preuve → Appel à l'action), dialogues amorcés depuis le
  brief. Le gabarit ne prétend pas être « intelligent » : il donne une base
  de travail immédiate, modifiable plan par plan dans le studio.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .config import get_settings

STRUCTURE = [
    ("Hook", "avatar", 4.0, "Face caméra, accroche directe en moins de 3 secondes — promesse ou erreur à éviter."),
    ("Problème", "avatar", 6.0, "Le présentateur nomme le problème concret de l'audience, ton complice."),
    ("Démonstration", "b_roll", 7.0, "Plan produit / geste / avant-après. Montrer, pas dire."),
    ("Preuve", "avatar", 6.0, "Résultat, chiffre ou témoignage court, dit simplement."),
    ("Appel à l'action", "avatar", 4.0, "Une seule action demandée, dite clairement, sourire, regard caméra."),
]


def _sentences(brief: str) -> list[str]:
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", brief.replace("\n", " ")) if s.strip()]
    return parts or [brief.strip()]


def storyboard_local(brief: str, recipe: str = "create") -> list[dict[str, Any]]:
    sents = _sentences(brief)
    shots = []
    for i, (title, kind, dur, direction) in enumerate(STRUCTURE):
        dialogue = sents[i] if i < len(sents) else ""
        if i == 0 and not dialogue:
            dialogue = brief[:90]
        shots.append({"idx": i, "title": title, "kind": kind, "duration_s": dur,
                      "dialogue": dialogue,
                      "prompt": f"{direction} Style UGC réaliste, lumière naturelle, caméra tenue main légère, vertical 9:16."})
    return shots


def storyboard(brief: str, recipe: str = "create") -> tuple[list[dict[str, Any]], str]:
    """Retourne (plans, source) — source = 'llm' ou 'gabarit_local'."""
    s = get_settings()
    if s.llm_api_key:
        try:
            return _storyboard_llm(brief, recipe), "llm"
        except Exception:
            pass  # repli silencieux mais tracé par la source retournée
    return storyboard_local(brief, recipe), "gabarit_local"


def _storyboard_llm(brief: str, recipe: str) -> list[dict[str, Any]]:
    import httpx
    s = get_settings()
    system = ("Tu es directeur de création publicitaire UGC. Réponds UNIQUEMENT en JSON : "
              '{"shots":[{"title":"...","kind":"avatar|b_roll","duration_s":4,"dialogue":"...","prompt":"..."}]} '
              "4 à 6 plans, dialogues courts en français parlé naturel (une phrase par plan), prompts visuels précis.")
    for _ in range(2):
        r = httpx.post(f"{s.llm_base_url}/chat/completions",
                       headers={"Authorization": f"Bearer {s.llm_api_key}"},
                       json={"model": s.llm_model, "temperature": 0.6,
                             "messages": [{"role": "system", "content": system},
                                          {"role": "user", "content": f"Brief : {brief}\nRecette : {recipe}"}]},
                       timeout=120)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", text, re.S)
        data = json.loads(m.group(0))  # type: ignore[union-attr]
        shots = []
        for i, sh in enumerate(data["shots"][:8]):
            shots.append({"idx": i, "title": str(sh.get("title", f"Plan {i+1}"))[:60],
                          "kind": sh.get("kind") if sh.get("kind") in ("avatar", "b_roll") else "b_roll",
                          "duration_s": max(1.0, min(float(sh.get("duration_s", 5)), 15.0)),
                          "dialogue": str(sh.get("dialogue", ""))[:400], "prompt": str(sh.get("prompt", ""))[:600]})
        if shots:
            return shots
    raise ValueError("Storyboard LLM invalide")
