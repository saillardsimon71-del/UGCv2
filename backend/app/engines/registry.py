"""Registre des moteurs + résolution : pour un besoin (kind), quel moteur réel
est disponible ici et maintenant ? La réponse est toujours honnête :
disponible / indisponible + raison affichable dans l'UI."""
from __future__ import annotations

from typing import Any

from ..config import get_settings
from .analysis import AnalysisEngine
from .assembly import AssemblyEngine
from .base import Engine
from .mock import TestPlateEngine
from .modal_remote import SPECS, ModalEngine

# Ordre de préférence par kind (production d'abord). Le routeur (recipes.py)
# peut imposer un moteur précis selon la qualité ; ceci est le repli.
PREFERENCE: dict[str, list[str]] = {
    "video": ["modal_ltx"],
    "avatar": ["modal_longcat_avatar", "modal_infinitetalk"],
    "face_swap": ["modal_facefusion"],
    "person_replace": ["modal_animate2", "modal_scail2"],
    "motion_transfer": ["modal_animate2", "modal_scail2"],
    "lip_sync": ["modal_latentsync", "modal_musetalk"],
    "tts": ["modal_chatterbox"],
    "voice_convert": ["modal_seedvc"],
}

_cache: dict[str, Engine] = {}


def get_engine(name: str) -> Engine:
    if name in _cache:
        return _cache[name]
    if name == "analysis":
        eng: Engine = AnalysisEngine()
    elif name in ("ffmpeg_assembly", "assembly"):
        eng = AssemblyEngine()
    elif name in SPECS:
        eng = ModalEngine(name)
        # Animate2/SCAIL2 servent deux kinds : l'instance garde son kind principal,
        # le mode (animate/replace) est porté par la requête.
    elif name.startswith("mock_"):
        eng = TestPlateEngine(name.removeprefix("mock_"))
    else:
        raise KeyError(f"Moteur inconnu : {name}")
    _cache[name] = eng
    return eng


def all_engines() -> list[Engine]:
    names = ["analysis", "ffmpeg_assembly"] + list(SPECS.keys()) + [f"mock_{k}" for k in PREFERENCE]
    return [get_engine(n) for n in names]


def availability_map() -> dict[str, tuple[bool, str]]:
    out = {}
    for eng in all_engines():
        # QC/directeur sont des étapes internes toujours disponibles
        out[eng.info.name] = eng.available()
    out["qc"] = (True, "")
    out["director"] = (True, "")
    return out


def resolve(kind: str, preferred: str | None = None) -> tuple[Engine | None, str]:
    """Retourne (moteur, explication). Simulation seulement en dernier recours
    et si autorisée — l'appelant doit surfacer `engine.info.simulated`."""
    candidates = ([preferred] if preferred else []) + [c for c in PREFERENCE.get(kind, []) if c != preferred]
    reasons = []
    for name in candidates:
        eng = get_engine(name)
        ok, reason = eng.available()
        if ok:
            return eng, f"{eng.info.label}"
        reasons.append(f"{name} : {reason}")
    if get_settings().allow_mock:
        return get_engine(f"mock_{kind}"), "Aucun moteur réel disponible — plaque de test (SIMULATION). " + " ; ".join(reasons)
    return None, " ; ".join(reasons) or f"Aucun moteur pour {kind}"


def system_report() -> dict[str, Any]:
    from ..media import ffmpeg_version
    engines = []
    for eng in all_engines():
        ok, reason = eng.available()
        d = eng.info.to_dict()
        d.update({"available": ok, "unavailable_reason": reason})
        engines.append(d)
    blockers = []
    real = [e for e in engines if e["available"] and not e["simulated"] and e["kind"] not in ("assembly", "analysis")]
    if not real:
        blockers.append("Aucun moteur IA réel disponible : activer Modal (docs/MODAL.md) pour les vrais rendus. "
                        "La chaîne studio (import, analyse, montage, QC, export) fonctionne en CPU.")
    if not get_settings().llm_api_key:
        blockers.append("Aucune clé LLM : le directeur créatif utilise ses gabarits locaux français.")
    return {"engines": engines, "blockers": blockers, "ffmpeg": ffmpeg_version(),
            "modal_enabled": get_settings().modal_enabled, "allow_mock": get_settings().allow_mock}
