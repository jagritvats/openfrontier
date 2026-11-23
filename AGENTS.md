# OpenFrontier — agent notes

* Python 3.12, stdlib only. Package `openfrontier/` at repo root; run commands
  from the repo root.
* Tests: `python -m pytest`. Demo: `python problems/erdos-straus/seed.py --fresh`,
  then `python problems/collatz/seed.py`, then `python -m openfrontier site --out site`.
* The event log is append-only. Never edit or delete events; new event types go
  in `events.EVENT_TYPES` with a matching projection rule in `model.py`.
* Nothing may be labeled `checked` unless an oracle in this repo produced it.
  Seeds run the real oracle; do not hand-write `oracle_verdict` events.
* Determinism: seeds use a fixed clock; oracle subprocesses get `PYTHONHASHSEED=0`.
* Keep it simple. No dependencies without a strong reason.
