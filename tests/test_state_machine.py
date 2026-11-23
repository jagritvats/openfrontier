from datetime import datetime, timedelta, timezone

import pytest

from openfrontier.events import EventStore
from openfrontier.model import counters, project

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _ts(minutes: int) -> str:
    return (T0 + timedelta(minutes=minutes)).isoformat(timespec="seconds")


def _checked_sequence(store, problem="p", lemma="L-1"):
    store.append(problem, "problem_registered", {"problem": {"id": problem, "title": "T"}}, ts=_ts(0))
    store.append(problem, "lemma_stated", {"id": lemma, "title": "x", "program": None, "aim": "for_yes"}, ts=_ts(1))
    store.append(problem, "seat_claimed", {"lemma": lemma, "seat": "s1", "expires": None}, ts=_ts(2))
    store.append(problem, "artifact_submitted", {"lemma": lemma, "seat": "s1", "artifact": {"path": "a.py", "oracle": "certificate_rerun"}}, ts=_ts(3))
    store.append(problem, "oracle_verdict", {"lemma": lemma, "seat": "s1", "status": "checked", "oracle": "certificate_rerun/0.1", "artifact_sha256": "0" * 64, "details": {}, "log_tail": "", "seconds": 0.1}, ts=_ts(4))


def test_happy_path_to_checked(tmp_path):
    store = EventStore(tmp_path / "t.db")
    _checked_sequence(store)
    view = project(store.replay())["p"]
    assert view.nodes["L-1"].state == "checked"
    assert counters(view)["checked"] == 1
    assert len(view.nodes["L-1"].history) == 4


def test_verdict_without_submission_raises(tmp_path):
    store = EventStore(tmp_path / "t.db")
    store.append("p", "problem_registered", {"problem": {"id": "p"}}, ts=_ts(0))
    store.append("p", "lemma_stated", {"id": "L-1", "title": "x", "program": None, "aim": None}, ts=_ts(1))
    store.append("p", "oracle_verdict", {"lemma": "L-1", "seat": "s1", "status": "checked"}, ts=_ts(2))
    with pytest.raises(ValueError, match="verdict without a submission"):
        project(store.replay())


def test_cannot_claim_checked_lemma(tmp_path):
    store = EventStore(tmp_path / "t.db")
    _checked_sequence(store)
    store.append("p", "seat_claimed", {"lemma": "L-1", "seat": "s2", "expires": None}, ts=_ts(5))
    with pytest.raises(ValueError, match="cannot claim"):
        project(store.replay())


def test_cannot_rule_checked_dead(tmp_path):
    store = EventStore(tmp_path / "t.db")
    _checked_sequence(store)
    store.append("p", "lemma_ruled_dead", {"lemma": "L-1", "reason": "no"}, ts=_ts(5))
    with pytest.raises(ValueError, match="terminal|checked"):
        project(store.replay())


def test_submission_requires_live_claim(tmp_path):
    store = EventStore(tmp_path / "t.db")
    store.append("p", "problem_registered", {"problem": {"id": "p"}}, ts=_ts(0))
    store.append("p", "lemma_stated", {"id": "L-1", "title": "x", "program": None, "aim": None}, ts=_ts(1))
    store.append("p", "artifact_submitted", {"lemma": "L-1", "seat": "s1", "artifact": {"path": "a.py", "oracle": "o"}}, ts=_ts(2))
    with pytest.raises(ValueError, match="without a live claim"):
        project(store.replay())


def test_expired_claim_lapses_back(tmp_path):
    store = EventStore(tmp_path / "t.db")
    store.append("p", "problem_registered", {"problem": {"id": "p"}}, ts=_ts(0))
    store.append("p", "lemma_stated", {"id": "L-1", "title": "x", "program": None, "aim": None}, ts=_ts(1))
    store.append("p", "seat_claimed", {"lemma": "L-1", "seat": "s1", "expires": _ts(30)}, ts=_ts(2))
    later = T0 + timedelta(minutes=60)
    view = project(store.replay(), now=later)["p"]
    assert view.nodes["L-1"].state == "conjecture"
    assert view.nodes["L-1"].seat is None
    still_valid = project(store.replay(), now=T0 + timedelta(minutes=10))["p"]
    assert still_valid.nodes["L-1"].state == "claimed"
