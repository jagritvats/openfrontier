"""Seed the collatz instance. Run after the erdos-straus seed (shares the db).

Run from the repo root:  python problems/collatz/seed.py
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
T0 = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "frontier.db"))
    args = ap.parse_args()

    tick = iter(range(10_000))

    def ts() -> str:
        return (T0 + timedelta(minutes=next(tick))).isoformat(timespec="seconds")

    def ns(**kw) -> Namespace:
        return Namespace(db=args.db, **kw)

    cli.cmd_init(ns(dir=str(HERE)), ts=ts())
    cli.cmd_open_program(ns(problem="collatz", id="P1", title="Empirical verification",
                            goal="Push the verified bound up, and map the structure of trajectories."), ts=ts())

    cli.cmd_state_lemma(ns(problem="collatz", id="L-001",
                           title="Every starting value n ≤ 100,000 reaches 1",
                           program="P1", aim="for_yes"), ts=ts())
    cli.cmd_state_lemma(ns(problem="collatz", id="L-002",
                           title="The full conjecture: every n ≥ 1 reaches 1",
                           program="P1", aim="for_yes"), ts=ts())
    cli.cmd_state_lemma(ns(problem="collatz", id="L-003",
                           title="Total stopping time is bounded by 2 · log2(n) for all n ≤ 100,000",
                           program="P1", aim="for_yes"), ts=ts())

    cli.cmd_claim(ns(problem="collatz", lemma="L-001", seat="brute-01", ttl_h=24), ts=ts())
    cli.cmd_submit(ns(problem="collatz", lemma="L-001", seat="brute-01",
                      artifact=str(ART / "cert_collatz.py"), oracle="certificate_rerun"), ts=ts())

    # A plausible-sounding claim, left open: nobody has submitted evidence yet.
    cli.cmd_claim(ns(problem="collatz", lemma="L-003", seat="skeptic-01", ttl_h=8760), ts=ts())


if __name__ == "__main__":
    main()
