import xml.etree.ElementTree as ET

from openfrontier.atom import atom_feed
from openfrontier.events import Event, EventStore

NS = "{http://www.w3.org/2005/Atom}"
SITE = "https://openfrontier.example"


def _seed(store: EventStore) -> list[Event]:
    return [
        store.append("alpha", "problem_registered",
                     {"problem": {"id": "alpha", "title": "Alpha & <Beta>"}},
                     ts="2026-01-01T09:00:00+00:00"),
        store.append("alpha", "lemma_stated",
                     {"id": "L-1", "title": "a <tiny> bound", "program": None, "aim": "for_yes"},
                     ts="2026-01-01T10:00:00+00:00"),
        store.append("beta", "problem_registered",
                     {"problem": {"id": "beta", "title": "Beta"}},
                     ts="2026-01-01T11:00:00+00:00"),
        store.append("alpha", "oracle_verdict",
                     {"lemma": "L-1", "seat": "s1", "status": "holds",
                      "oracle": "certificate_rerun/0.1"},
                     ts="2026-01-01T12:00:00+00:00"),
        store.append("beta", "lemma_stated",
                     {"id": "L-7", "title": "beta bound", "program": None, "aim": "neutral"},
                     ts="2026-01-01T13:00:00+00:00"),
    ]


def _entries(xml_text: str) -> list[ET.Element]:
    return ET.fromstring(xml_text).findall(f"{NS}entry")


def test_feed_parses_with_metadata(tmp_path):
    events = _seed(EventStore(tmp_path / "t.db"))
    root = ET.fromstring(atom_feed(events, site_url=SITE))

    assert root.tag == f"{NS}feed"
    assert root.find(f"{NS}title").text == "OpenFrontier"
    assert root.find(f"{NS}id").text == SITE
    link = root.find(f"{NS}link")
    assert link.get("rel") == "alternate"
    assert link.get("href") == SITE
    assert root.find(f"{NS}updated").text == events[-1].ts
    assert len(root.findall(f"{NS}entry")) == len(events)


def test_entries_are_newest_first_by_id(tmp_path):
    events = _seed(EventStore(tmp_path / "t.db"))
    entries = _entries(atom_feed(events, site_url=SITE))

    ids = [int(e.find(f"{NS}id").text.split("#e")[1]) for e in entries]
    assert ids == [ev.id for ev in reversed(events)]
    assert ids == sorted(ids, reverse=True)


def test_filtering_by_problem(tmp_path):
    events = _seed(EventStore(tmp_path / "t.db"))
    xml_text = atom_feed(events, site_url=f"{SITE}/alpha.atom", problem="alpha")
    root = ET.fromstring(xml_text)
    entries = root.findall(f"{NS}entry")

    assert root.find(f"{NS}title").text == "OpenFrontier — alpha"
    assert len(entries) == 3
    assert [e.find(f"{NS}id").text for e in entries] == [
        f"{SITE}/alpha.atom#e{ev.id}" for ev in reversed(events) if ev.problem == "alpha"
    ]
    # The newest included event drives the feed timestamp, not the newest overall.
    newest_alpha = max((ev for ev in events if ev.problem == "alpha"), key=lambda ev: ev.ts)
    assert root.find(f"{NS}updated").text == newest_alpha.ts
    assert "beta" not in " ".join(e.find(f"{NS}title").text for e in entries)


def test_deterministic(tmp_path):
    events = _seed(EventStore(tmp_path / "t.db"))
    first = atom_feed(events, site_url=SITE)
    second = atom_feed(events, site_url=SITE)
    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")
    assert first.startswith("<?xml")


def test_entry_ids_summaries_and_escaping(tmp_path):
    events = _seed(EventStore(tmp_path / "t.db"))
    xml_text = atom_feed(events, site_url=SITE)
    entries = _entries(xml_text)

    assert all(f"{SITE}#e" in e.find(f"{NS}id").text for e in entries)

    by_type = {}
    for e in entries:
        title = e.find(f"{NS}title").text
        kind = title.split(" — ")[0]
        by_type.setdefault(kind, []).append(e)

    registered = by_type["problem_registered"][0]
    assert registered.find(f"{NS}title").text == "problem_registered — Beta"
    assert registered.find(f"{NS}content").text == "Beta"
    assert registered.find(f"{NS}content").get("type") == "text"

    verdict = by_type["oracle_verdict"][0]
    assert verdict.find(f"{NS}title").text == "oracle_verdict — L-1: holds (certificate_rerun/0.1)"
    assert verdict.find(f"{NS}content").text == "L-1: holds (certificate_rerun/0.1)"

    # Escaped on the wire, exact once parsed.
    alpha_titles = [e.find(f"{NS}title").text for e in by_type["problem_registered"]]
    assert "problem_registered — Alpha & <Beta>" in alpha_titles
    assert "&amp;" in xml_text and "&lt;Beta&gt;" in xml_text
    assert "ns0" not in xml_text

    for e in entries:
        assert e.find(f"{NS}updated").text == next(
            ev.ts for ev in events if e.find(f"{NS}id").text == f"{SITE}#e{ev.id}")


def test_empty_feed_uses_epoch(tmp_path):
    xml_text = atom_feed([], site_url=SITE)
    root = ET.fromstring(xml_text)

    assert root.find(f"{NS}updated").text == "1970-01-01T00:00:00+00:00"
    assert root.findall(f"{NS}entry") == []
    assert root.find(f"{NS}title").text == "OpenFrontier"
