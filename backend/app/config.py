"""Configuration du studio UGCv2 — tout par variables d'environnement `STUDIO_*`.

Principe : le studio démarre partout sans clé ni GPU. Les moteurs distants
(Modal) sont activés explicitement ; tant qu'ils ne le sont pas, l'interface
l'affiche honnêtement au lieu de simuler en silence.
Compatibilité : les anciennes variables `PVS_*` du précédent studio sont lues
en secours pour faciliter la migration.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    v = os.environ.get(f"STUDIO_{name}")
    if v is None or v == "":
        v = os.environ.get(f"PVS_{name}", default)
    return v.strip()


def _flag(name: str, default: bool) -> bool:
    raw = _env(name, "1" if default else "0").lower()
    return raw in {"1", "true", "yes", "on"}


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    repo_root: Path = field(default_factory=_root)
    data_dir: Path = field(init=False)
    db_path: Path = field(init=False)
    static_dir: Path = field(init=False)

    host: str = field(default_factory=lambda: _env("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(_env("PORT", "8000")))
    max_workers: int = field(default_factory=lambda: int(_env("MAX_WORKERS", "1")))

    # Plaques de test étiquetées SIMULATION. En production : STUDIO_ALLOW_MOCK=0
    allow_mock: bool = field(default_factory=lambda: _flag("ALLOW_MOCK", True))

    # --- Modal (GPU à la demande, 0 au repos) ------------------------------
    modal_enabled: bool = field(default_factory=lambda: _flag("MODAL_ENABLED", False))
    modal_workspace: str = field(default_factory=lambda: _env("MODAL_WORKSPACE", ""))
    # Applications déjà déployées et prouvées sur le workspace existant :
    app_video: str = field(default_factory=lambda: _env("MODAL_APP_VIDEO", "pvs-ltx"))
    app_avatar: str = field(default_factory=lambda: _env("MODAL_APP_AVATAR", "pvs-longcat-avatar"))
    # Nouvelles applications UGCv2 (déployées via deploy/*.py, voir docs/MODAL.md)
    app_face: str = field(default_factory=lambda: _env("MODAL_APP_FACE", "ugc-face"))
    app_perf: str = field(default_factory=lambda: _env("MODAL_APP_PERF", "ugc-perf"))
    app_lipsync: str = field(default_factory=lambda: _env("MODAL_APP_LIPSYNC", "ugc-lipsync"))
    app_voice: str = field(default_factory=lambda: _env("MODAL_APP_VOICE", "ugc-voice"))
    app_talk: str = field(default_factory=lambda: _env("MODAL_APP_TALK", "ugc-talk"))

    # --- Directeur créatif (LLM OpenAI-compatible, optionnel) ---------------
    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", "https://api.deepseek.com/v1"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "deepseek-chat"))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", ""))

    # Tarifs indicatifs USD/h GPU (surchargeables STUDIO_RATE_<FOURNISSEUR>_<GPU>)
    rate_card: dict = field(default_factory=lambda: {
        "modal:L40S": 2.84, "modal:A100_80GB": 3.72, "modal:H100_80GB": 4.90,
        "modal:T4": 0.59, "modal:L4": 0.80, "modal:A10G": 1.10,
        "local:CPU": 0.0, "local:local": 0.0,
    })

    def __post_init__(self):
        self.data_dir = Path(_env("DATA_DIR", str(self.repo_root / "data"))).resolve()
        self.db_path = self.data_dir / "studio.db"
        self.static_dir = self.repo_root / "frontend" / "dist"
        for sub in ("projects", "uploads", "exports", "tmp", "voices", "characters"):
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)

    @property
    def ffmpeg(self) -> str:
        explicit = _env("FFMPEG")
        if explicit:
            return explicit
        found = shutil.which("ffmpeg")
        if found:
            return found
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return "ffmpeg"

    def rate_for(self, provider: str, gpu: str) -> float:
        key = f"RATE_{provider.upper()}_{gpu.upper()}"
        v = _env(key)
        if v:
            return float(v)
        return self.rate_card.get(f"{provider}:{gpu}", 0.0)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
