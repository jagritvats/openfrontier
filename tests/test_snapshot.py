import json

from openfrontier.events import EventStore
from openfrontier.snapshot import snapshot_dict, write_snapshot

def _seed(db) -> EventStore:
    store = EventStore(db)
    append = store.append

    def ts(n: int) -> str:
        return f"2026-01-01T00:{n:02d}:00+00:00"

    append("p", "problem_registered", {"problem": {
        "id": "p", "title": "T", "field": "f", "status": "open", "statement_plain": "s",
    }}, ts=ts(0))
    append("p", "lemma_stated",
           {"id": "L-1", "title": "tiny bound", "program": "P-1", "aim": "for_yes"}, ts=ts(1))
    append("p", "seat_claimed",
           {"lemma": "L-1", "seat": "s1", "expires": None}, ts=ts(2))
    append("p", "artifact_submitted",
           {"lemma": "L-1", "seat": "s1",
            "artifact": {"path": "tiny.py", "oracle": "certificate_rerun"}}, ts=ts(3))
    append("p", "oracle_verdict",
           {"lemma": "L-1", "seat": "s1", "status": "checked",
            "oracle": "certificate_rerun/0.1", "artifact_sha256": "a" * 64,
            "details": {"result": "holds"}, "log_tail": '{"result": "holds"}',
            "seconds": 0.01}, ts=ts(4))
    append("p", "milestone_reached", {"text": "first check"}, ts=ts(5))
    return store


def test_snapshot_reads_spec_counters_and_verdict(tmp_path):
    store = _seed(tmp_path / "t.db")
    snap = snapshot_dict(store)

    assert snap["schema"] == "openfrontier/snapshot/0.1"
    assert len(snap["problems"]) == 1

    problem = snap["problems"][0]
    assert problem["id"] == "p"
    assert problem["title"] == "T"
    assert problem["field"] == "f"
    assert problem["status"] == "open"
    assert problem["statement_plain"] == "s"
    assert problem["counters"]["checked"] == 1
    assert problem["counters"]["open"] == 0

    (node,) = problem["nodes"]
    assert node["id"] == "L-1"
    assert node["state"] == "checked"
    assert node["dead_reason"] is None
    assert node["verdict"]["artifact_sha256"] == "a" * 64
    assert node["verdict"]["oracle"] == "certificate_rerun/0.1"
    assert node["verdict"]["status"] == "checked"

    assert problem["milestones"] == ["first check"]
    assert [e["id"] for e in problem["feed"]] == [1, 2, 3, 4, 5, 6]
    assert problem["feed"][4]["type"] == "oracle_verdict"
    assert problem["feed"][4]["summary"] == "L-1: checked (certificate_rerun/0.1)"


def test_write_snapshot_round_trips_and_is_deterministic(tmp_path):
    store = _seed(tmp_path / "t.db")

    first = write_snapshot(store, tmp_path / "a")
    second = write_snapshot(store, tmp_path / "b" / "nested")

    assert first == tmp_path / "a" / "snapshot.json"
    assert first.is_file()
    assert json.loads(first.read_text(encoding="utf-8")) == snapshot_dict(store)
    assert first.read_text(encoding="utf-8").endswith("\n")
    assert first.read_bytes() == second.read_bytes()
