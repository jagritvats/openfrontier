"""The whole record as JSON, for anyone who wants to build on it.

``snapshot.json`` is the machine-readable twin of the site: every problem, its
counters, its lemma map with verdicts, its milestones and its feed, derived
purely from the append-only event log. Same log in, same bytes out — there is
no clock and no environment in here, so two runs over an unchanged store diff
to nothing.

Claims are reported as the log states them. A lapsed TTL is a projection-time
concern (the site resolves it against the current time); a snapshot has no
current time, so it prints the record, not the reading of it.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .events import EventStore
from .model import counters, project

SCHEMA = "openfrontier/snapshot/0.1"

# Before any timestamp in the log, so no claim is expired by projection.
_NO_CLOCK = datetime.min.replace(tzinfo=timezone.utc)

_VERDICT_FIELDS = ("status", "oracle", "artifact_sha256", "details", "seconds")


def _summarize(ev) -> str:
    """One-line summary of an event; the same text the CLI feed prints."""
    from .cli import _summarize as summarize

    return summarize(ev)


def _problem_head(pid: str, spec: dict | None) -> dict:
    head = (spec or {}).get("problem") or {}
    return {
        "id": head.get("id", pid),
        "title": head.get("title", pid),
        "field": head.get("field", ""),
        "status": head.get("status", "open"),
        "statement_plain": head.get("statement_plain", ""),
    }


def _verdict(node) -> dict | None:
    if node.verdict is None:
        return None
    return {k: node.verdict.get(k) for k in _VERDICT_FIELDS}


def _node_dict(node) -> dict:
    return {
        "id": node.id,
        "title": node.title,
        "program": node.program,
        "aim": node.aim,
        "state": node.state,
        "seat": node.seat,
        "dead_reason": node.dead_reason if node.state == "dead" else None,
        "verdict": _verdict(node),
    }


def _problem_dict(view) -> dict:
    return {
        **_problem_head(view.id, view.spec),
        "counters": counters(view),
        "nodes": [_node_dict(view.nodes[nid]) for nid in sorted(view.nodes)],
        "milestones": [m.get("text", "") for m in view.milestones],
        "feed": [
            {"id": ev.id, "ts": ev.ts, "type": ev.type, "summary": _summarize(ev)}
            for ev in sorted(view.feed, key=lambda e: e.id)
        ],
    }


def snapshot_dict(store: EventStore) -> dict:
    """The full platform state as a plain JSON-ready dict."""
    views = project(store.replay(), now=_NO_CLOCK)
    return {
        "schema": SCHEMA,
        "problems": [_problem_dict(views[pid]) for pid in store.problems() if pid in views],
    }


def write_snapshot(store: EventStore, out: str | Path) -> Path:
    """Write ``<out>/snapshot.json`` and return its path."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "snapshot.json"
    body = json.dumps(snapshot_dict(store), ensure_ascii=False, sort_keys=True, indent=2)
    path.write_text(body + "\n", encoding="utf-8", newline="\n")
    return path
