"""Projection: replay events into the current state of each problem.

This module is also the state machine. Illegal transitions raise, loudly — a
platform whose record can silently contradict itself is worse than no record.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .events import Event

OPEN_STATES = {"conjecture", "claimed", "submitted", "build_error"}


@dataclass
class Node:
    id: str
    title: str
    program: str | None
    aim: str | None
    state: str = "conjecture"
    seat: str | None = None
    claim_expires: str | None = None
    artifact: dict | None = None
    verdict: dict | None = None
    dead_reason: str | None = None
    history: list[Event] = field(default_factory=list)


@dataclass
class ProblemView:
    id: str
    spec: dict | None = None
    programs: dict[str, dict] = field(default_factory=dict)
    nodes: dict[str, Node] = field(default_factory=dict)
    milestones: list[dict] = field(default_factory=list)
    feed: list[Event] = field(default_factory=list)


def project(events: list[Event], now: datetime | None = None) -> dict[str, ProblemView]:
    now = now or datetime.now(timezone.utc)
    views: dict[str, ProblemView] = {}
    for ev in events:
        view = views.setdefault(ev.problem, ProblemView(id=ev.problem))
        view.feed.append(ev)
        _apply(view, ev)
    # an idle seat lapses back to a conjecture
    for view in views.values():
        for node in view.nodes.values():
            if node.state == "claimed" and node.claim_expires and _parse(node.claim_expires) <= now:
                node.state = "conjecture"
                node.seat = None
                node.claim_expires = None
    return views


def _apply(view: ProblemView, ev: Event) -> None:
    t, d = ev.type, ev.data
    if t == "problem_registered":
        view.spec = d
    elif t == "program_opened":
        view.programs[d["id"]] = d
    elif t == "lemma_stated":
        if d["id"] in view.nodes:
            raise ValueError(f"{view.id}: duplicate lemma {d['id']} (event #{ev.id})")
        view.nodes[d["id"]] = Node(
            id=d["id"], title=d["title"], program=d.get("program"),
            aim=d.get("aim"), history=[ev],
        )
    elif t == "seat_claimed":
        node = _node(view, d["lemma"], ev)
        if node.state != "conjecture":
            raise ValueError(f"{view.id}/{node.id}: cannot claim while {node.state!r} (event #{ev.id})")
        node.state, node.seat, node.claim_expires = "claimed", d["seat"], d.get("expires")
        node.history.append(ev)
    elif t == "artifact_submitted":
        node = _node(view, d["lemma"], ev)
        if node.state != "claimed" or node.seat != d["seat"]:
            raise ValueError(
                f"{view.id}/{node.id}: submission from seat {d['seat']!r} "
                f"without a live claim (event #{ev.id})"
            )
        node.state, node.artifact = "submitted", d["artifact"]
        node.history.append(ev)
    elif t == "oracle_verdict":
        node = _node(view, d["lemma"], ev)
        if node.state != "submitted":
            raise ValueError(f"{view.id}/{node.id}: verdict without a submission (event #{ev.id})")
        status = d["status"]
        if status not in {"checked", "refuted", "build_error"}:
            raise ValueError(f"{view.id}/{node.id}: unknown verdict {status!r} (event #{ev.id})")
        node.state, node.verdict = status, d
        node.history.append(ev)
    elif t == "lemma_ruled_dead":
        node = _node(view, d["lemma"], ev)
        if node.state == "checked":
            raise ValueError(f"{view.id}/{node.id}: cannot rule a checked lemma dead (event #{ev.id})")
        node.state, node.dead_reason = "dead", d["reason"]
        node.history.append(ev)
    elif t == "milestone_reached":
        view.milestones.append(d)


def _node(view: ProblemView, lemma_id: str, ev: Event) -> Node:
    try:
        return view.nodes[lemma_id]
    except KeyError:
        raise ValueError(f"{view.id}: event #{ev.id} references unknown lemma {lemma_id!r}") from None


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def counters(view: ProblemView) -> dict[str, int]:
    out = {"checked": 0, "refuted": 0, "dead": 0, "claimed": 0, "open": 0}
    for n in view.nodes.values():
        if n.state in out:
            out[n.state] += 1
        if n.state in OPEN_STATES:
            out["open"] += 1
    return out
