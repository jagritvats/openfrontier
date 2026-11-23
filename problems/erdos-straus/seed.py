"""Seed the erdos-straus instance by driving the real CLI code paths with a
fixed clock, so the demo record is stable. Every `checked` below was actually
re-run by the oracle while seeding.

Run from the repo root:  python problems/erdos-straus/seed.py [--fresh]
"""
import argparse
import sys
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from openfrontier import cli  # noqa: E402

HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts"
T0 = datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true", help="delete the db first")
    ap.add_argument("--db", default=str(ROOT / "frontier.db"))
    ap.add_argument("--limit", type=int, default=None,
                    help="unused placeholder for parity with certificates")
    args = ap.parse_args()

    db = Path(args.db)
    if args.fresh and db.exists():
        db.unlink()

    tick = iter(range(10_000))

    def ts() -> str:
        return (T0 + timedelta(minutes=next(tick))).isoformat(timespec="seconds")

    def ns(**kw) -> Namespace:
        return Namespace(db=str(db), **kw)

    cli.cmd_init(ns(dir=str(HERE)), ts=ts())
    cli.cmd_open_program(ns(problem="erdos-straus", id="P1", title="Elementary bounds",
                            goal="Small cases, parametric families, and cheap counterexample hunts."), ts=ts())

    cli.cmd_state_lemma(ns(problem="erdos-straus", id="L-001",
                           title="Every n ≤ 1,000 admits a solution",
                           program="P1", aim="for_yes"), ts=ts())
    cli.cmd_state_lemma(ns(problem="erdos-straus", id="L-002",
                           title="The full conjecture: every n ≥ 2 admits a solution",
                           program="P1", aim="for_yes"), ts=ts())
    cli.cmd_state_lemma(ns(problem="erdos-straus", id="L-003",
                           title="A solution with a = b = c exists for every n",
                           program="P1", aim="for_yes"), ts=ts())
    cli.cmd_state_lemma(ns(problem="erdos-straus", id="L-004",
                           title="The family n ≡ 3 (mod 4) is solvable, explicitly",
                           program="P1", aim="for_yes"), ts=ts())
    cli.cmd_state_lemma(ns(problem="erdos-straus", id="L-005",
                           title="The family n ≡ 2 (mod 3) is solvable, explicitly",
                           program="P1", aim="for_yes"), ts=ts())

    cli.cmd_claim(ns(problem="erdos-straus", lemma="L-001", seat="brute-01", ttl_h=24), ts=ts())
    cli.cmd_submit(ns(problem="erdos-straus", lemma="L-001", seat="brute-01",
                      artifact=str(ART / "cert_bound.py"), oracle="certificate_rerun"), ts=ts())
    cli.cmd_milestone(ns(problem="erdos-straus",
                         text="First verified bound on the platform: 4/n solvable for all "
                              "n ≤ 1,000, re-runnable by anyone."), ts=ts())

    cli.cmd_claim(ns(problem="erdos-straus", lemma="L-004", seat="algebra-01", ttl_h=24), ts=ts())
    cli.cmd_submit(ns(problem="erdos-straus", lemma="L-004", seat="algebra-01",
                      artifact=str(ART / "cert_mod4.py"), oracle="certificate_rerun"), ts=ts())

    cli.cmd_claim(ns(problem="erdos-straus", lemma="L-003", seat="skeptic-01", ttl_h=24), ts=ts())
    cli.cmd_submit(ns(problem="erdos-straus", lemma="L-003", seat="skeptic-01",
                      artifact=str(ART / "refute_equal_denom.py"), oracle="certificate_rerun"), ts=ts())
    cli.cmd_rule_dead(ns(problem="erdos-straus", lemma="L-003",
                         reason="Refuted by certificate at n = 2 (equal denominators would need "
                                "a = 3/2). Refutations count; filed with thanks."), ts=ts())

    # The live edge of the map: a seat at work, nothing submitted yet.
    # Long ttl so the sample record keeps showing the seat at work.
    cli.cmd_claim(ns(problem="erdos-straus", lemma="L-005", seat="algebra-02", ttl_h=8760), ts=ts())


if __name__ == "__main__":
    main()
