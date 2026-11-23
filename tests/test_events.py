import pytest

from openfrontier.events import EventStore


@pytest.fixture()
def store(tmp_path):
    return EventStore(tmp_path / "test.db")


def test_append_replay_roundtrip(store):
    store.append("p", "problem_registered", {"problem": {"id": "p", "title": "T"}})
    store.append("p", "lemma_stated", {"id": "L-1", "title": "x", "program": None, "aim": "for_yes"})
    events = store.replay()
    assert [e.type for e in events] == ["problem_registered", "lemma_stated"]
    assert events[1].data["id"] == "L-1"
    assert events[0].id < events[1].id


def test_unknown_event_type_rejected(store):
    with pytest.raises(ValueError, match="unknown event type"):
        store.append("p", "agent_says_trust_me", {})


def test_problems_lists_registered_in_order(store):
    store.append("b", "problem_registered", {"problem": {"id": "b"}})
    store.append("a", "problem_registered", {"problem": {"id": "a"}})
    assert store.problems() == ["b", "a"]


def test_replay_filter_by_problem(store):
    store.append("a", "problem_registered", {"problem": {"id": "a"}})
    store.append("b", "problem_registered", {"problem": {"id": "b"}})
    assert [e.problem for e in store.replay("a")] == ["a"]
