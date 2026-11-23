"""The record, syndicated.

An Atom 1.0 projection of the append-only event log: one feed, or one feed
per problem, with entries newest-first. Nothing here reads the clock — the
feed's ``updated`` is the newest event timestamp, so the same events always
render to the same bytes.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

from .events import Event

ATOM_NS = "http://www.w3.org/2005/Atom"

#: ``updated`` for a feed with no entries. Deliberately not "now".
_EPOCH = "1970-01-01T00:00:00+00:00"

ET.register_namespace("", ATOM_NS)


def _q(tag: str) -> str:
    """Qualify a local tag name with the Atom namespace."""
    return f"{{{ATOM_NS}}}{tag}"


def _ts_key(ev: Event) -> tuple[int, object]:
    """Sort key for a timestamp: parsed when possible, raw string otherwise."""
    try:
        return (1, datetime.fromisoformat(ev.ts))
    except (TypeError, ValueError):
        return (0, ev.ts)


def _latest_ts(events: list[Event]) -> str:
    if not events:
        return _EPOCH
    return max(events, key=_ts_key).ts


def atom_feed(events: list[Event], *, site_url: str, problem: str | None = None) -> str:
    """Render ``events`` as an Atom 1.0 document.

    With ``problem`` set, only that problem's events are included and the
    feed title carries the problem id. Entry order is newest-first by event
    id; the feed ``updated`` is the newest included event's timestamp (or
    the epoch when there are none), never the current time.
    """
    from .cli import _summarize  # lazy: cli imports the event store, avoid a cycle

    included = [ev for ev in events if problem is None or ev.problem == problem]
    included.sort(key=lambda ev: ev.id, reverse=True)

    title = "OpenFrontier" if problem is None else f"OpenFrontier — {problem}"

    feed = ET.Element(_q("feed"))
    ET.SubElement(feed, _q("title")).text = title
    ET.SubElement(feed, _q("id")).text = site_url
    ET.SubElement(feed, _q("link"), {"rel": "alternate", "href": site_url})
    ET.SubElement(feed, _q("updated")).text = _latest_ts(included)
    # RFC 4287 requires an author on the feed (or on every entry).
    author = ET.SubElement(feed, _q("author"))
    ET.SubElement(author, _q("name")).text = "OpenFrontier"

    for ev in included:
        summary = _summarize(ev)
        entry = ET.SubElement(feed, _q("entry"))
        ET.SubElement(entry, _q("title")).text = f"{ev.type} — {summary}"
        ET.SubElement(entry, _q("id")).text = f"{site_url}#e{ev.id}"
        ET.SubElement(entry, _q("updated")).text = ev.ts
        ET.SubElement(entry, _q("content"), {"type": "text"}).text = summary

    return ET.tostring(feed, encoding="utf-8", xml_declaration=True).decode("utf-8")
