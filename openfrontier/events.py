"""Append-only event store.

Everything the site shows — the feed, the counters, the map states — is a
projection of these events. There is deliberately no update and no delete.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

EVENT_TYPES = frozenset({
    "problem_registered",
    "program_opened",
    "lemma_stated",
    "seat_claimed",
    "artifact_submitted",
    "oracle_verdict",
    "lemma_ruled_dead",
    "milestone_reached",
})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    problem TEXT NOT NULL,
    type TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_problem ON events(problem, id);
"""


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Event:
    id: int
    ts: str
    problem: str
    type: str
    data: dict


class EventStore:
    """SQLite-backed append-only log."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.executescript(_SCHEMA)

    def append(self, problem: str, type: str, data: dict, ts: str | None = None) -> Event:
        if type not in EVENT_TYPES:
            raise ValueError(f"unknown event type: {type!r} (allowed: {sorted(EVENT_TYPES)})")
        ts = ts or utcnow_iso()
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
        cur = self._conn.execute(
            "INSERT INTO events (ts, problem, type, data) VALUES (?, ?, ?, ?)",
            (ts, problem, type, payload),
        )
        self._conn.commit()
        return Event(id=cur.lastrowid, ts=ts, problem=problem, type=type, data=data)

    def replay(self, problem: str | None = None) -> list[Event]:
        sql = "SELECT id, ts, problem, type, data FROM events"
        params: tuple = ()
        if problem is not None:
            sql += " WHERE problem = ?"
            params = (problem,)
        sql += " ORDER BY id"
        return [
            Event(id=r[0], ts=r[1], problem=r[2], type=r[3], data=json.loads(r[4]))
            for r in self._conn.execute(sql, params)
        ]

    def problems(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT problem FROM events WHERE type = 'problem_registered' ORDER BY id"
        )
        return [r[0] for r in rows]

    def close(self) -> None:
        self._conn.close()
