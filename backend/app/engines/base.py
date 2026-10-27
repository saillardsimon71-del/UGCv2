"""Contrat unique entre le studio (produit) et les moteurs (IA/ffmpeg).

Ajouter/remplacer un modèle = écrire une classe ici. Aucune logique produit
n'importe un moteur directement : elle passe par le registre.
Kinds : face_swap | person_replace | motion_transfer | lip_sync | avatar |
        tts | voice_convert | video | assembly | analysis
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class Usage:
    provider: str = "local"
    gpu: str = "CPU"
    gpu_seconds: float = 0.0
    rate_usd_hr: float | None = None
    notes: str = ""

    def cost_usd(self) -> float:
        from ..config import get_settings
        rate = self.rate_usd_hr if self.rate_usd_hr is not None else get_settings().rate_for(self.provider, self.gpu)
        return round(self.gpu_seconds / 3600.0 * rate, 6)

    def to_dict(self) -> dict[str, Any]:
        from ..config import get_settings
        return {"provider": self.provider, "gpu": self.gpu,
                "gpu_seconds": round(self.gpu_seconds, 2),
                "rate_usd_hr": self.rate_usd_hr if self.rate_usd_hr is not None else get_settings().rate_for(self.provider, self.gpu),
                "cost_usd": self.cost_usd(), "notes": self.notes}


class EngineUnavailable(RuntimeError):
    pass


class JobCancelled(RuntimeError):
    pass


class JobContext(Protocol):
    job_id: str
    def log(self, message: str, progress: float | None = None, stage: str = "") -> None: ...
    def check_cancelled(self) -> None: ...


@dataclass
class EngineInfo:
    name: str
    kind: str
    label: str
    capabilities: list[str] = field(default_factory=list)
    requires_gpu: bool = False
    provider: str = "local"
    gpu: str = "CPU"
    simulated: bool = False   # plaque de test, jamais présentée comme un rendu IA
    verified: bool = False    # a produit un vrai résultat sur GPU réel (preuve dans docs/STATE.md)
    # unverified | benchmark_planned | benchmark_passed | production
    maturity: str = "unverified"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return vars(self).copy()


@dataclass
class EngineRequest:
    kind: str
    output_dir: Path
    project: dict[str, Any] = field(default_factory=dict)
    shot: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)

    @property
    def prompt(self) -> str:
        return str(self.params.get("prompt") or self.shot.get("prompt") or "")

    @property
    def duration_s(self) -> float:
        return float(self.params.get("duration_s") or self.shot.get("duration_s") or 5.0)

    def out(self, filename: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir / filename


@dataclass
class EngineOutput:
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    notes: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def add(self, path: Path, kind: str = "video", mime: str = "video/mp4", **meta: Any) -> None:
        self.artifacts.append({"path": str(path), "kind": kind, "mime": mime,
                                "bytes": path.stat().st_size if Path(path).exists() else 0, "meta": meta})


class Engine(ABC):
    info: EngineInfo

    def available(self) -> tuple[bool, str]:
        return True, ""

    def estimate(self, request: EngineRequest) -> dict[str, Any]:
        return {"gpu_seconds": 0.0, "cost_usd": 0.0, "basis": "cpu"}

    @abstractmethod
    def run(self, request: EngineRequest, ctx: JobContext) -> EngineOutput: ...

    @staticmethod
    def now() -> float:
        return time.time()
