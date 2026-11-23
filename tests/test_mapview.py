"""The map: one SVG per problem, lanes of programs, coloured lemma nodes."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from openfrontier.events import EventStore
from openfrontier.mapview import map_svg
from openfrontier.model import ProblemView, project

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _ts(minutes: int) -> str:
    return (T0 + timedelta(minutes=minutes)).isoformat(timespec="seconds")


def _tiny_view(db: Path) -> ProblemView:
    store = EventStore(db)
    store.append(
        "tiny",
        "problem_registered",
        {"problem": {"id": "tiny", "title": "A tiny problem"}},
        ts=_ts(0),
    )
    store.append(
        "tiny",
        "program_opened",
        {"id": "P1", "title": "Search small n", "goal": "check n < 100"},
        ts=_ts(1),
    )
    # three lemmas: one lands in the assigned lane, one in "unassigned"
    store.append(
        "tiny",
        "lemma_stated",
        {"id": "L-1", "title": "bound <b>four</b>", "program": "P1", "aim": "for_yes"},
        ts=_ts(2),
    )
    store.append(
        "tiny",
        "lemma_stated",
        {"id": "L-2", "title": "the middle case", "program": "P1", "aim": "for_yes"},
        ts=_ts(3),
    )
    store.append(
        "tiny",
        "lemma_stated",
        {"id": "L-3", "title": "a stray conjecture", "program": None, "aim": "neutral"},
        ts=_ts(4),
    )
    # L-1 -> checked
    store.append(
        "tiny",
        "seat_claimed",
        {"lemma": "L-1", "seat": "s1", "expires": None},
        ts=_ts(5),
    )
    store.append(
        "tiny",
        "artifact_submitted",
        {"lemma": "L-1", "seat": "s1", "artifact": {"path": "a.py", "oracle": "certificate_rerun"}},
        ts=_ts(6),
    )
    store.append(
        "tiny",
        "oracle_verdict",
        {
            "lemma": "L-1",
            "seat": "s1",
            "status": "checked",
            "oracle": "certificate_rerun/0.1",
            "artifact_sha256": "0" * 64,
            "details": {},
            "log_tail": "",
            "seconds": 0.1,
        },
        ts=_ts(7),
    )
    # L-2 stays claimed
    store.append(
        "tiny",
        "seat_claimed",
        {"lemma": "L-2", "seat": "s2", "expires": None},
        ts=_ts(8),
    )
    events = store.replay()
    store.close()
    return project(events)["tiny"]


def test_map_starts_with_svg_and_holds_every_node(tmp_path):
    view = _tiny_view(tmp_path / "t.db")
    assert view.nodes["L-1"].state == "checked"
    assert view.nodes["L-2"].state == "claimed"
    assert view.nodes["L-3"].state == "conjecture"

    svg = map_svg(view)
    assert isinstance(svg, str)
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert 'width="880"' in svg
    for node_id in ("L-1", "L-2", "L-3"):
        assert node_id in svg
    assert "unassigned" in svg
    assert "Search small n" in svg
    # both lanes get a program marker and an edge to their lemmas
    assert svg.count('class="of-program-marker"') == 2
    assert svg.count('class="of-edge"') == 3


def test_map_colours_by_state(tmp_path):
    svg = map_svg(_tiny_view(tmp_path / "t.db"))
    assert "#4ecb71" in svg  # checked
    assert "#e0b040" in svg  # claimed
    assert "#9aa7bd" in svg  # conjecture


def test_map_is_deterministic(tmp_path):
    view = _tiny_view(tmp_path / "t.db")
    assert map_svg(view) == map_svg(view)
    # a fresh projection of the same log renders identically too
    assert map_svg(view) == map_svg(project(EventStore(tmp_path / "t.db").replay())["tiny"])


def test_map_escapes_node_titles(tmp_path):
    svg = map_svg(_tiny_view(tmp_path / "t.db"))
    assert "&lt;b&gt;" in svg
    assert "<b>" not in svg
    assert "bound &lt;b&gt;four&lt;/b&gt; — checked" in svg


def test_map_renders_dead_and_unassigned_nodes(tmp_path):
    db = tmp_path / "t.db"
    store = EventStore(db)
    store.append("p", "problem_registered", {"problem": {"id": "p"}}, ts=_ts(0))
    store.append("p", "lemma_stated", {"id": "L-9", "title": "wrong turn", "program": None, "aim": None}, ts=_ts(1))
    store.append("p", "lemma_ruled_dead", {"lemma": "L-9", "reason": "counterexample"}, ts=_ts(2))
    events = store.replay()
    store.close()
    svg = map_svg(project(events)["p"])
    assert "#b06a7a" in svg
    assert 'stroke-dasharray="4 3"' in svg
    assert "line-through" in svg
