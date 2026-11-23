from argparse import Namespace
from pathlib import Path

from openfrontier import cli
from openfrontier.events import EventStore
from openfrontier.site import build_site

ROOT = Path(__file__).resolve().parents[1]

T = iter(range(10_000))


def _ts() -> str:
    return f"2026-01-01T00:{next(T) % 60:02d}:00+00:00"


def _seed_tiny(db: Path, tmp_path: Path) -> None:
    artifact = tmp_path / "tiny.py"
    artifact.write_text('import json; print(json.dumps({"result": "holds", "bound": 10}))\n', encoding="utf-8")

    def ns(**kw):
        return Namespace(db=str(db), **kw)

    cli.cmd_init(ns(dir=str(ROOT / "problems" / "erdos-straus")), ts=_ts())
    cli.cmd_state_lemma(ns(problem="erdos-straus", id="L-1", title="tiny bound", program=None, aim="for_yes"), ts=_ts())
    cli.cmd_state_lemma(ns(problem="erdos-straus", id="L-2", title="the big one", program=None, aim="for_yes"), ts=_ts())
    cli.cmd_claim(ns(problem="erdos-straus", lemma="L-1", seat="s1", ttl_h=None), ts=_ts())
    cli.cmd_submit(ns(problem="erdos-straus", lemma="L-1", seat="s1",
                      artifact=str(artifact), oracle="certificate_rerun"), ts=_ts())


def test_site_renders_states(tmp_path):
    db = tmp_path / "t.db"
    _seed_tiny(db, tmp_path)
    out = build_site(EventStore(db), tmp_path / "site")
    index = (out / "index.html").read_text(encoding="utf-8")
    page = (out / "erdos-straus.html").read_text(encoding="utf-8")
    assert "Erdős–Straus conjecture" in index
    assert "badge checked" in page
    assert "certificate_rerun/0.1" in page
    assert "the big one" in page
    assert "Nothing here is an agent's own account" in page


def test_seed_tiny_marks_checked(tmp_path, capsys):
    db = tmp_path / "t.db"
    _seed_tiny(db, tmp_path)
    capsys.readouterr()
    cli.main(["--db", str(db), "stats"])
    out = capsys.readouterr().out
    assert "checked 1" in out
    assert "open 1" in out
