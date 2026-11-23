"""Command line: the whole platform loop, deliberately synchronous and local.

  python -m openfrontier init problems/erdos-straus
  python -m openfrontier open-program --problem P --id P1 --title ... --goal ...
  python -m openfrontier state-lemma --problem P --id L-001 --title ... [--program P1] [--aim for_yes]
  python -m openfrontier claim --problem P --lemma L-001 --seat brute-01 --ttl-h 24
  python -m openfrontier submit --problem P --lemma L-001 --seat brute-01 --artifact f.py --oracle certificate_rerun
  python -m openfrontier rule-dead --problem P --lemma L-003 --reason ...
  python -m openfrontier milestone --problem P --text ...
  python -m openfrontier feed [--problem P] [--reverse]
  python -m openfrontier stats
  python -m openfrontier site --out site
"""
from __future__ import annotations

import argparse
import json
import sys
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .events import EventStore
from .model import counters, project
from .oracles import get_oracle


def _store(args) -> EventStore:
    return EventStore(args.db)


def _require_node(store: EventStore, problem: str, lemma: str):
    views = project(store.replay(problem))
    if problem not in views or lemma not in views[problem].nodes:
        raise SystemExit(f"error: unknown lemma {problem}/{lemma}")
    return views[problem].nodes[lemma]


def cmd_init(args, ts=None):
    spec_path = Path(args.dir) / "problem.toml"
    spec = tomllib.loads(spec_path.read_text(encoding="utf-8"))
    store = _store(args)
    ev = store.append(spec["problem"]["id"], "problem_registered", spec, ts=ts)
    print(f"registered problem {spec['problem']['id']!r} (event #{ev.id})")


def cmd_open_program(args, ts=None):
    store = _store(args)
    ev = store.append(args.problem, "program_opened",
                      {"id": args.id, "title": args.title, "goal": args.goal}, ts=ts)
    print(f"program {args.id} opened (event #{ev.id})")


def cmd_state_lemma(args, ts=None):
    store = _store(args)
    ev = store.append(args.problem, "lemma_stated",
                      {"id": args.id, "title": args.title,
                       "program": args.program, "aim": args.aim}, ts=ts)
    print(f"lemma {args.id} stated (event #{ev.id})")


def cmd_claim(args, ts=None):
    node = _require_node(_store(args), args.problem, args.lemma)
    if node.state != "conjecture":
        raise SystemExit(f"error: {args.lemma} is {node.state}, cannot claim")
    base = datetime.fromisoformat(ts) if ts else datetime.now(timezone.utc)
    expires = (base + timedelta(hours=args.ttl_h)).isoformat(timespec="seconds") if args.ttl_h else None
    store = _store(args)
    ev = store.append(args.problem, "seat_claimed",
                      {"lemma": args.lemma, "seat": args.seat, "expires": expires}, ts=ts)
    print(f"{args.seat} claimed {args.lemma} (event #{ev.id})")


def cmd_submit(args, ts=None):
    node = _require_node(_store(args), args.problem, args.lemma)
    if node.state != "claimed" or node.seat != args.seat:
        raise SystemExit(f"error: {args.lemma} is not claimed by seat {args.seat!r}")
    oracle = get_oracle(args.oracle)
    artifact = str(Path(args.artifact))
    store = _store(args)
    store.append(args.problem, "artifact_submitted",
                 {"lemma": args.lemma, "seat": args.seat,
                  "artifact": {"path": artifact, "oracle": args.oracle}}, ts=ts)
    verdict = oracle.verify(artifact)
    ev = store.append(args.problem, "oracle_verdict",
                      {"lemma": args.lemma, "seat": args.seat, "status": verdict.status,
                       "oracle": verdict.oracle, "artifact_sha256": verdict.artifact_sha256,
                       "details": verdict.details, "log_tail": verdict.log_tail,
                       "seconds": verdict.seconds}, ts=ts)
    print(json.dumps({"lemma": args.lemma, "status": verdict.status, "event": ev.id,
                      "oracle": verdict.oracle, "sha256": verdict.artifact_sha256,
                      "details": verdict.details}, indent=2, ensure_ascii=False))


def cmd_rule_dead(args, ts=None):
    node = _require_node(_store(args), args.problem, args.lemma)
    if node.state == "checked":
        raise SystemExit(f"error: {args.lemma} is checked; checked is terminal")
    store = _store(args)
    ev = store.append(args.problem, "lemma_ruled_dead",
                      {"lemma": args.lemma, "reason": args.reason}, ts=ts)
    print(f"{args.lemma} ruled dead (event #{ev.id})")


def cmd_milestone(args, ts=None):
    store = _store(args)
    ev = store.append(args.problem, "milestone_reached", {"text": args.text}, ts=ts)
    print(f"milestone (event #{ev.id})")


def cmd_feed(args, ts=None):
    store = _store(args)
    events = store.replay(args.problem)
    if args.reverse:
        events = list(reversed(events))
    for ev in events:
        print(f"#{ev.id:<4} {ev.ts}  {ev.problem:<14} {ev.type:<20} {_summarize(ev)}")


def _summarize(ev) -> str:
    d = ev.data
    if ev.type == "problem_registered":
        return d["problem"]["title"]
    if ev.type in {"program_opened", "lemma_stated"}:
        return f"{d['id']}: {d['title']}"
    if ev.type == "seat_claimed":
        return f"{d['seat']} -> {d['lemma']}"
    if ev.type == "artifact_submitted":
        return f"{d['seat']} -> {d['lemma']} ({d['artifact']['oracle']})"
    if ev.type == "oracle_verdict":
        return f"{d['lemma']}: {d['status']} ({d['oracle']})"
    if ev.type == "lemma_ruled_dead":
        return f"{d['lemma']}: {d['reason']}"
    if ev.type == "milestone_reached":
        return d["text"]
    return ""


def cmd_stats(args, ts=None):
    store = _store(args)
    views = project(store.replay())
    for pid in store.problems():
        v, c = views[pid], counters(views[pid])
        title = v.spec["problem"]["title"] if v.spec else pid
        print(f"{pid:<16} {title}")
        print(f"  checked {c['checked']} · open {c['open']} "
              f"({c['claimed']} seats at work) · refuted {c['refuted']} · ruled dead {c['dead']}")


def cmd_site(args, ts=None):
    from .site import build_site
    out = build_site(_store(args), args.out)
    print(f"site written to {out}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="openfrontier", description=__doc__)
    p.add_argument("--db", default="frontier.db")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="register a problem from its directory (problem.toml)")
    s.add_argument("dir")

    s = sub.add_parser("open-program")
    s.add_argument("--problem", required=True)
    s.add_argument("--id", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--goal", required=True)

    s = sub.add_parser("state-lemma")
    s.add_argument("--problem", required=True)
    s.add_argument("--id", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--program")
    s.add_argument("--aim", choices=["for_yes", "for_no", "neutral"], default="neutral")

    s = sub.add_parser("claim")
    s.add_argument("--problem", required=True)
    s.add_argument("--lemma", required=True)
    s.add_argument("--seat", required=True)
    s.add_argument("--ttl-h", type=float, default=None)

    s = sub.add_parser("submit")
    s.add_argument("--problem", required=True)
    s.add_argument("--lemma", required=True)
    s.add_argument("--seat", required=True)
    s.add_argument("--artifact", required=True)
    s.add_argument("--oracle", default="certificate_rerun")

    s = sub.add_parser("rule-dead")
    s.add_argument("--problem", required=True)
    s.add_argument("--lemma", required=True)
    s.add_argument("--reason", required=True)

    s = sub.add_parser("milestone")
    s.add_argument("--problem", required=True)
    s.add_argument("--text", required=True)

    s = sub.add_parser("feed")
    s.add_argument("--problem")
    s.add_argument("--reverse", action="store_true")

    sub.add_parser("stats")

    s = sub.add_parser("site")
    s.add_argument("--out", default="site")
    return p


COMMANDS = {
    "init": cmd_init,
    "open-program": cmd_open_program,
    "state-lemma": cmd_state_lemma,
    "claim": cmd_claim,
    "submit": cmd_submit,
    "rule-dead": cmd_rule_dead,
    "milestone": cmd_milestone,
    "feed": cmd_feed,
    "stats": cmd_stats,
    "site": cmd_site,
}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    COMMANDS[args.cmd](args)
    return 0
