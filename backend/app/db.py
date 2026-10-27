"""SQLite — un fichier, pas d'ORM. Le plan (shot) est l'unité de travail :
état, prise sélectionnée, historique des prises, QC et revue humaine."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, brief TEXT NOT NULL DEFAULT '',
    recipe TEXT NOT NULL DEFAULT 'create', format TEXT NOT NULL DEFAULT '9:16',
    status TEXT NOT NULL DEFAULT 'draft', quality TEXT NOT NULL DEFAULT 'production',
    settings TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY, project_id TEXT, name TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL, path TEXT NOT NULL, mime TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'source', meta TEXT NOT NULL DEFAULT '{}',
    rights_note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
    ref_asset_id TEXT, refs TEXT NOT NULL DEFAULT '[]', voice_id TEXT,
    consent INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS voices (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, language TEXT NOT NULL DEFAULT 'fr',
    ref_asset_id TEXT, transcript TEXT NOT NULL DEFAULT '', params TEXT NOT NULL DEFAULT '{}',
    consent INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shots (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, idx INTEGER NOT NULL,
    kind TEXT NOT NULL DEFAULT 'b_roll', title TEXT NOT NULL DEFAULT '',
    duration_s REAL NOT NULL DEFAULT 5.0, dialogue TEXT NOT NULL DEFAULT '',
    prompt TEXT NOT NULL DEFAULT '', character_id TEXT, voice_id TEXT,
    source_asset_id TEXT, status TEXT NOT NULL DEFAULT 'draft',
    selected_artifact TEXT, params TEXT NOT NULL DEFAULT '{}',
    qc TEXT NOT NULL DEFAULT '{}', human_review TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_shots_project ON shots(project_id, idx);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY, project_id TEXT, shot_id TEXT, type TEXT NOT NULL,
    engine TEXT NOT NULL, params TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'queued', progress REAL NOT NULL DEFAULT 0,
    stage TEXT NOT NULL DEFAULT '', error TEXT, attempts INTEGER NOT NULL DEFAULT 0,
    provider TEXT NOT NULL DEFAULT 'local', gpu TEXT NOT NULL DEFAULT 'CPU',
    gpu_seconds REAL NOT NULL DEFAULT 0, cost_usd REAL NOT NULL DEFAULT 0,
    simulated INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
    started_at TEXT, finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at);
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY, job_id TEXT, project_id TEXT, shot_id TEXT,
    kind TEXT NOT NULL, path TEXT NOT NULL, mime TEXT NOT NULL DEFAULT 'application/octet-stream',
    bytes INTEGER NOT NULL DEFAULT 0, meta TEXT NOT NULL DEFAULT '{}',
    rating INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifacts_shot ON artifacts(shot_id);
CREATE TABLE IF NOT EXISTS exports (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, path TEXT NOT NULL,
    poster TEXT, srt_path TEXT, spec TEXT NOT NULL DEFAULT '{}',
    qc TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cost_events (
    id TEXT PRIMARY KEY, project_id TEXT, job_id TEXT, provider TEXT NOT NULL DEFAULT 'local',
    gpu TEXT NOT NULL DEFAULT 'CPU', gpu_seconds REAL NOT NULL DEFAULT 0,
    rate_usd_hr REAL NOT NULL DEFAULT 0, usd REAL NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
"""

JSON_FIELDS = {"settings", "meta", "refs", "params", "qc", "human_review", "spec"}
_lock = threading.Lock()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def conn() -> Iterator[sqlite3.Connection]:
    c = sqlite3.connect(get_settings().db_path, timeout=30, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    try:
        yield c
    finally:
        c.close()


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)


def _decode(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    d = dict(row)
    for k in JSON_FIELDS:
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k] or "{}")
            except json.JSONDecodeError:
                d[k] = {}
    return d


def _encode(data: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in data.items():
        out[k] = json.dumps(v, ensure_ascii=False) if k in JSON_FIELDS and not isinstance(v, str) else v
    return out


def insert(table: str, data: dict[str, Any]) -> dict[str, Any]:
    data = _encode(dict(data))
    cols = ", ".join(data.keys())
    marks = ", ".join("?" for _ in data)
    with _lock, conn() as c:
        c.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(data.values()))
    return get(table, data["id"])  # type: ignore[return-value]


def get(table: str, row_id: str) -> dict[str, Any] | None:
    with conn() as c:
        return _decode(c.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone())


def find(table: str, where: str = "1=1", args: tuple = (), order: str = "created_at DESC") -> list[dict[str, Any]]:
    with conn() as c:
        rows = c.execute(f"SELECT * FROM {table} WHERE {where} ORDER BY {order}", args).fetchall()
    return [r for r in (_decode(x) for x in rows) if r]


def update(table: str, row_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    if not data:
        return get(table, row_id)
    data = _encode(dict(data))
    sets = ", ".join(f"{k} = ?" for k in data)
    with _lock, conn() as c:
        c.execute(f"UPDATE {table} SET {sets} WHERE id = ?", (*data.values(), row_id))
    return get(table, row_id)


def delete(table: str, row_id: str) -> bool:
    with _lock, conn() as c:
        cur = c.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
        return cur.rowcount > 0
