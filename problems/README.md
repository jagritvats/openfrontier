# Problems

One directory per problem instance. An instance is three things:

```
problems/<id>/
  problem.toml     the statement (plain + formal), references, default oracle
  artifacts/       self-contained files an oracle can run (the evidence)
  seed.py          drives the real CLI with a fixed clock, building the record
```

## Adding a new problem

1. Copy an existing instance directory and rename it.
2. Edit `problem.toml`. The `[context].literature` field is for what the
   literature already knows — it is shown as context, never as a result.
3. Write artifacts that honor the oracle contract (see `SPEC.md`): for
   `certificate_rerun`, a standalone program whose last stdout line is JSON
   `{"result": "holds"|"fails", ...}`. Deterministic, exact arithmetic,
   re-runnable by anyone.
4. Write `seed.py` that drives `openfrontier.cli` in a legal order
   (state lemmas → claim seats → submit artifacts → rule dead what died).
5. Re-run the site: `python -m openfrontier site --out site`.

## Rules

* Never hand-write `oracle_verdict` events. If the oracle didn't run it,
  it isn't checked. Seeds must call `cmd_submit`, which runs the real oracle.
* Refutations and dead approaches are first-class content. A good graveyard
  is a feature of an instance, not an embarrassment.
* Keep artifacts fast (seconds, not minutes). Big bounds belong in the
  literature field until the platform can afford them.
