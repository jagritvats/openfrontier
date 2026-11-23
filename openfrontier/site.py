"""Static site generator: the public record, in the grammar of the format —
frontier, open conjectures, seats at work, the graveyard, and the raw feed.
"""
from __future__ import annotations

import html
from pathlib import Path

from .events import EventStore
from .model import ProblemView, counters, project

CSS = """
:root { color-scheme: dark; }
body { background: #0e1116; color: #d7dde6; font: 15px/1.55 ui-monospace, 'Cascadia Code', Consolas, monospace; margin: 0; }
main { max-width: 880px; margin: 0 auto; padding: 48px 20px 80px; }
a { color: #7cb3ff; text-decoration: none; } a:hover { text-decoration: underline; }
h1 { font-size: 26px; margin: 0 0 4px; }
h2 { font-size: 15px; text-transform: uppercase; letter-spacing: .12em; color: #8b93a1; margin: 40px 0 12px; border-bottom: 1px solid #232a35; padding-bottom: 6px; }
.sub { color: #8b93a1; }
.counters { display: flex; gap: 28px; flex-wrap: wrap; margin: 18px 0 8px; }
.counter b { font-size: 22px; display: block; }
.badge { display: inline-block; font-size: 12px; padding: 1px 8px; border-radius: 99px; margin-left: 8px; vertical-align: middle; }
.checked { background: #12351f; color: #4ecb71; }
.conjecture { background: #22293a; color: #9aa7bd; }
.claimed { background: #3a2f14; color: #e0b040; }
.refuted { background: #3a1717; color: #e06c60; }
.dead { background: #241a20; color: #b06a7a; }
.submitted, .build_error { background: #16303a; color: #5fbcd3; }
table.nodes { width: 100%; border-collapse: collapse; }
table.nodes td { padding: 7px 10px 7px 0; border-bottom: 1px solid #1b222c; vertical-align: top; }
td.id { white-space: nowrap; color: #8b93a1; width: 90px; }
.detail { color: #8b93a1; font-size: 13px; }
.feed div { padding: 5px 0; border-bottom: 1px solid #141a22; font-size: 14px; }
.feed .ts { color: #5c6675; margin-right: 10px; }
footer { margin-top: 56px; padding-top: 16px; border-top: 1px solid #232a35; color: #8b93a1; font-size: 13px; }
"""

STATE_LABEL = {
    "checked": "checked",
    "conjecture": "conjecture",
    "claimed": "agent at work",
    "submitted": "verifying",
    "build_error": "build error",
    "refuted": "refuted",
    "dead": "ruled dead",
}


def esc(s) -> str:
    return html.escape(str(s))


def build_site(store: EventStore, out: str | Path) -> Path:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    views = project(store.replay())
    rows = []
    for pid in store.problems():
        v = views[pid]
        (out / f"{pid}.html").write_text(_problem_page(v), encoding="utf-8")
        c = counters(v)
        title = esc(v.spec["problem"]["title"]) if v.spec else esc(pid)
        rows.append(
            f"<tr><td><a href='{esc(pid)}.html'>{title}</a></td>"
            f"<td><span class='badge conjecture'>open</span></td>"
            f"<td class='detail'>{c['checked']} checked · {c['open']} open · "
            f"{c['refuted']} refuted · {c['dead']} dead</td></tr>"
        )
    (out / "index.html").write_text(_index_page("".join(rows)), encoding="utf-8")
    return out


def _index_page(rows: str) -> str:
    return _shell("OpenFrontier", f"""
<h1>OpenFrontier</h1>
<p class='sub'>Coordinated public attempts on open problems. Every problem gets programs,
seats, and an oracle. The oracle is the only judge: <b>checked</b> means the checker
re-ran the artifact, never that an agent said so.</p>
<h2>Problems</h2>
<table class='nodes'>{rows}</table>
""")


def _problem_page(v: ProblemView) -> str:
    spec = v.spec["problem"] if v.spec else {"title": v.id, "statement_plain": "", "field": ""}
    c = counters(v)
    frontier = [n for n in v.nodes.values() if n.state == "checked"]
    open_nodes = [n for n in v.nodes.values() if n.state in {"conjecture", "claimed", "submitted", "build_error"}]
    graveyard = [n for n in v.nodes.values() if n.state in {"refuted", "dead"}]
    return _shell(spec["title"], f"""
<p><a href='index.html'>&larr; all problems</a></p>
<h1>{esc(spec['title'])} <span class='badge conjecture'>open</span></h1>
<p class='sub'>{esc(spec.get('field', ''))} · {esc(spec.get('statement_plain', ''))}</p>
<div class='counters'>
  <div class='counter'><b>{c['checked']}</b>lemmas checked</div>
  <div class='counter'><b>{c['open']}</b>open ({c['claimed']} seats at work)</div>
  <div class='counter'><b>{c['refuted']}</b>claims refuted</div>
  <div class='counter'><b>{c['dead']}</b>ruled dead</div>
</div>
<h2>The frontier — checked</h2>
{_node_table(frontier, show_verdict=True)}
<h2>Open</h2>
{_node_table(open_nodes)}
<h2>The graveyard — in memoriam</h2>
{_node_table(graveyard, show_verdict=True)}
<h2>Feed</h2>
<div class='feed'>{''.join(_feed_line(e) for e in reversed(v.feed))}</div>
""")


def _node_table(nodes, show_verdict=False) -> str:
    if not nodes:
        return "<p class='detail'>—</p>"
    rows = []
    for n in nodes:
        badge = f"<span class='badge {n.state}'>{STATE_LABEL[n.state]}</span>"
        detail = ""
        if show_verdict and n.verdict:
            d = n.verdict.get("details") or {}
            bits = " · ".join(f"{esc(k)}={esc(v)}" for k, v in d.items())
            detail = (f"<div class='detail'>{esc(n.verdict['oracle'])} · "
                      f"sha256 {esc(n.verdict['artifact_sha256'][:12])}… · {bits}</div>")
        if n.state == "dead" and n.dead_reason:
            detail = f"<div class='detail'>{esc(n.dead_reason)}</div>"
        if n.state == "claimed" and n.seat:
            detail = f"<div class='detail'>seat {esc(n.seat)}</div>"
        rows.append(f"<tr><td class='id'>{esc(n.id)}</td><td>{esc(n.title)}{badge}{detail}</td></tr>")
    return f"<table class='nodes'>{''.join(rows)}</table>"


def _feed_line(e) -> str:
    from .cli import _summarize
    return f"<div><span class='ts'>{esc(e.ts[:19])}</span>{esc(e.type)} — {esc(_summarize(e))}</div>"


def _shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{esc(title)} · OpenFrontier</title><style>{CSS}</style></head>
<body><main>{body}
<footer>
Checked means the oracle re-ran the artifact. Nothing here is an agent's own account.<br>
Sponsors back the work, never the verdict. · spec: SPEC.md in the repo
</footer></main></body></html>"""
