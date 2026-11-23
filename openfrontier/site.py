"""Static site generator: the public record, in the grammar of the format —
the map, the frontier, open conjectures, seats at work, the graveyard,
the raw feed, per-lemma evidence pages, an Atom feed and a JSON snapshot.
"""
from __future__ import annotations

import html
import os
from datetime import datetime
from pathlib import Path

from .events import Event, EventStore
from .model import Node, ProblemView, counters, project

BASE_URL = os.environ.get("OPENFRONTIER_BASE_URL", "https://jagritvats.github.io/openfrontier")
REPO_URL = "https://github.com/jagritvats/openfrontier"

CSS = """
:root { color-scheme: dark; }
body { background: #0e1116; color: #d7dde6; font: 15px/1.55 ui-monospace, 'Cascadia Code', Consolas, monospace; margin: 0; }
main { max-width: 920px; margin: 0 auto; padding: 48px 20px 80px; }
a { color: #7cb3ff; text-decoration: none; } a:hover { text-decoration: underline; }
h1 { font-size: 26px; margin: 0 0 4px; }
h2 { font-size: 15px; text-transform: uppercase; letter-spacing: .12em; color: #8b93a1; margin: 40px 0 12px; border-bottom: 1px solid #232a35; padding-bottom: 6px; }
h3 { font-size: 15px; margin: 0 0 6px; }
.sub { color: #8b93a1; }
.counters { display: flex; gap: 28px; flex-wrap: wrap; margin: 18px 0 8px; }
.counter b { font-size: 22px; display: block; }
.badge { display: inline-block; font-size: 12px; padding: 1px 8px; border-radius: 99px; margin-left: 8px; vertical-align: middle; white-space: nowrap; }
.aim { font-size: 11px; padding: 1px 7px; border-radius: 99px; margin-left: 6px; background: #1b2433; color: #8fa8cf; vertical-align: middle; }
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
.map { overflow-x: auto; background: #10151d; border: 1px solid #1b222c; border-radius: 10px; padding: 14px; }
.programs { display: grid; gap: 12px; }
.card { background: #10151d; border: 1px solid #1b222c; border-radius: 10px; padding: 14px 16px; }
pre.log { background: #0b0f14; border: 1px solid #1b222c; border-radius: 8px; padding: 12px; overflow-x: auto; font-size: 13px; white-space: pre-wrap; }
table.kv td { padding: 4px 14px 4px 0; color: #8b93a1; }
table.kv td + td { color: #d7dde6; }
input#of-search { width: 100%; box-sizing: border-box; background: #0b0f14; color: #d7dde6; border: 1px solid #232a35; border-radius: 8px; padding: 8px 12px; font: inherit; margin: 0 0 10px; }
input#of-search:focus { outline: 1px solid #2f3a4c; }
.milestones div { padding: 5px 0; border-bottom: 1px solid #141a22; font-size: 14px; }
.milestones .ts { color: #5c6675; margin-right: 10px; }
footer { margin-top: 56px; padding-top: 16px; border-top: 1px solid #232a35; color: #8b93a1; font-size: 13px; }
.statement { background: #10151d; border-left: 3px solid #2f3a4c; padding: 10px 14px; margin: 12px 0; }
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

AIM_LABEL = {"for_yes": "aims: yes", "for_no": "aims: no"}

SEARCH_JS = """const q = document.getElementById('of-search');
if (q) q.addEventListener('input', () => {
  const needle = q.value.toLowerCase();
  document.querySelectorAll('[data-of-row]').forEach(el => {
    el.style.display = el.textContent.toLowerCase().includes(needle) ? '' : 'none';
  });
});
"""


def esc(s) -> str:
    return html.escape(str(s))


def slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s).strip("-")


def lemma_href(problem_id: str, node_id: str) -> str:
    return f"lemma-{slug(problem_id)}-{slug(node_id)}.html"


def build_site(store: EventStore, out: str | Path) -> Path:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    events = store.replay()
    # the site is a deterministic projection of the log: evaluate claim expiry
    # as of the latest event, never as of the wall clock
    now = datetime.fromisoformat(events[-1].ts) if events else None
    views = project(events, now=now)

    from .atom import atom_feed
    from .snapshot import write_snapshot

    rows = []
    for pid in store.problems():
        v = views[pid]
        (out / f"{pid}.html").write_text(_problem_page(v), encoding="utf-8")
        (out / f"{pid}.atom").write_text(
            atom_feed(events, site_url=f"{BASE_URL}/{pid}.html", problem=pid), encoding="utf-8")
        for n in v.nodes.values():
            (out / lemma_href(pid, n.id)).write_text(_lemma_page(v, n), encoding="utf-8")
        c = counters(v)
        title = esc(v.spec["problem"]["title"]) if v.spec else esc(pid)
        rows.append(
            f"<tr data-of-row><td><a href='{esc(pid)}.html'>{title}</a></td>"
            f"<td><span class='badge conjecture'>open</span></td>"
            f"<td class='detail'>{c['checked']} checked · {c['open']} open · "
            f"{c['refuted']} refuted · {c['dead']} dead</td></tr>"
        )
    (out / "feed.atom").write_text(atom_feed(events, site_url=BASE_URL), encoding="utf-8")
    (out / "index.html").write_text(_index_page("".join(rows), events, views), encoding="utf-8")
    write_snapshot(store, out)
    return out


def _index_page(rows: str, events: list[Event], views: dict[str, ProblemView]) -> str:
    recent = "".join(_feed_line(e, show_problem=True) for e in reversed(events[-15:]))
    return _shell("OpenFrontier", f"""
<h1>OpenFrontier</h1>
<p class='sub'>Coordinated public attempts on open problems. Every problem gets programs,
seats, and an oracle. The oracle is the only judge: <b>checked</b> means the checker
re-ran the artifact, never that an agent said so.</p>
<div class='programs'>
  <div class='card'><h3>problem → programs</h3><div class='detail'>A famous open question, stated
  precisely, split into lines of attack with goals in plain words.</div></div>
  <div class='card'><h3>programs → seats → lemmas</h3><div class='detail'>A seat is a mandate inside a
  program. Seats take lemmas: statements, bounds, and claims to prove or break.</div></div>
  <div class='card'><h3>the oracle decides</h3><div class='detail'>Every claim is re-run by a machine
  oracle in a pinned environment. Refutations count as results and rest in the graveyard.</div></div>
</div>
<h2>Problems</h2>
<input id='of-search' type='search' placeholder='search problems, lemmas, feed…' autocomplete='off'>
<table class='nodes'>{rows}</table>
<h2>Latest from the record</h2>
<div class='feed'>{recent}</div>
""", atom=f"{BASE_URL}/feed.atom")


def _problem_page(v: ProblemView) -> str:
    from .mapview import map_svg
    spec = v.spec["problem"] if v.spec else {"title": v.id, "statement_plain": "", "field": ""}
    ctx = v.spec.get("context", {}) if v.spec else {}
    c = counters(v)
    frontier = [n for n in v.nodes.values() if n.state == "checked"]
    open_nodes = [n for n in v.nodes.values() if n.state in {"conjecture", "claimed", "submitted", "build_error"}]
    graveyard = [n for n in v.nodes.values() if n.state in {"refuted", "dead"}]
    return _shell(spec["title"], f"""
<p><a href='index.html'>&larr; all problems</a></p>
<h1>{esc(spec['title'])} <span class='badge conjecture'>{esc(spec.get('status', 'open'))}</span></h1>
<div class='statement'>{esc(spec.get('statement_plain', ''))}
{f"<div class='detail'>{esc(spec.get('statement_formal', ''))}</div>" if spec.get('statement_formal') else ""}</div>
<p class='sub'>{esc(spec.get('field', ''))}{f" · {esc(ctx.get('literature', ''))}" if ctx.get('literature') else ""}</p>
<div class='counters'>
  <div class='counter'><b>{c['checked']}</b>lemmas checked</div>
  <div class='counter'><b>{c['open']}</b>open ({c['claimed']} seats at work)</div>
  <div class='counter'><b>{c['refuted']}</b>claims refuted</div>
  <div class='counter'><b>{c['dead']}</b>ruled dead</div>
</div>
<h2>The map</h2>
<div class='map'>{map_svg(v)}</div>
{_programs_section(v)}
<h2>The frontier — checked</h2>
{_node_table(v, frontier, show_verdict=True)}
<h2>Open</h2>
{_node_table(v, open_nodes)}
<h2>The graveyard — in memoriam</h2>
{_node_table(v, graveyard, show_verdict=True)}
{_milestones_section(v)}
<h2>Feed</h2>
<input id='of-search' type='search' placeholder='filter the feed…' autocomplete='off'>
<div class='feed'>{''.join(_feed_line(e) for e in reversed(v.feed))}</div>
""", atom=f"{BASE_URL}/{v.id}.atom")


def _programs_section(v: ProblemView) -> str:
    if not v.programs:
        return ""
    cards = []
    for p in v.programs.values():
        lemmas = [n for n in v.nodes.values() if n.program == p["id"]]
        done = sum(1 for n in lemmas if n.state == "checked")
        rows = "".join(
            f"<tr data-of-row><td class='id'><a href='{esc(lemma_href(v.id, n.id))}'>{esc(n.id)}</a></td>"
            f"<td>{esc(n.title)}<span class='badge {n.state}'>{STATE_LABEL[n.state]}</span></td></tr>"
            for n in sorted(lemmas, key=lambda x: x.id)
        )
        cards.append(
            f"<div class='card'><h3>{esc(p['id'])} · {esc(p['title'])} "
            f"<span class='detail'>{done}/{len(lemmas)} checked</span></h3>"
            f"<div class='detail'>{esc(p.get('goal', ''))}</div>"
            f"<table class='nodes'>{rows}</table></div>"
        )
    return f"<h2>Programs</h2><div class='programs'>{''.join(cards)}</div>"


def _milestones_section(v: ProblemView) -> str:
    if not v.milestones:
        return ""
    items = "".join(f"<div>{esc(m['text'])}</div>" for m in v.milestones)
    return f"<h2>Milestones</h2><div class='milestones'>{items}</div>"


def _node_table(v: ProblemView, nodes, show_verdict=False) -> str:
    if not nodes:
        return "<p class='detail'>—</p>"
    rows = []
    for n in nodes:
        badge = f"<span class='badge {n.state}'>{STATE_LABEL[n.state]}</span>"
        aim = f"<span class='aim'>{AIM_LABEL[n.aim]}</span>" if n.aim in AIM_LABEL else ""
        detail = ""
        if show_verdict and n.verdict:
            d = n.verdict.get("details") or {}
            bits = " · ".join(f"{esc(k)}={esc(val)}" for k, val in d.items())
            detail = (f"<div class='detail'>{esc(n.verdict['oracle'])} · "
                      f"sha256 {esc(n.verdict['artifact_sha256'][:12])}… · {bits} · "
                      f"<a href='{esc(lemma_href(v.id, n.id))}'>evidence</a></div>")
        if n.state == "dead" and n.dead_reason:
            detail = f"<div class='detail'>{esc(n.dead_reason)}</div>"
        if n.state == "claimed" and n.seat:
            detail = f"<div class='detail'>seat {esc(n.seat)}</div>"
        rows.append(
            f"<tr data-of-row><td class='id'><a href='{esc(lemma_href(v.id, n.id))}'>{esc(n.id)}</a></td>"
            f"<td>{esc(n.title)}{badge}{aim}{detail}</td></tr>"
        )
    return f"<table class='nodes'>{''.join(rows)}</table>"


def _lemma_page(v: ProblemView, n: Node) -> str:
    badge = f"<span class='badge {n.state}'>{STATE_LABEL[n.state]}</span>"
    aim = f"<span class='aim'>{AIM_LABEL[n.aim]}</span>" if n.aim in AIM_LABEL else ""
    program = v.programs.get(n.program or "", None)
    program_line = (f"<tr><td>program</td><td>{esc(program['id'])} · {esc(program['title'])}</td></tr>"
                    if program else "")
    seat_line = f"<tr><td>seat</td><td>{esc(n.seat)}</td></tr>" if n.seat else ""
    verdict_block = ""
    if n.verdict:
        d = n.verdict.get("details") or {}
        details_rows = "".join(f"<tr><td>{esc(k)}</td><td>{esc(val)}</td></tr>" for k, val in d.items())
        log = n.verdict.get("log_tail") or ""
        artifact = (n.artifact or {}).get("path", "")
        verdict_block = f"""
<h2>Verdict</h2>
<table class='kv'>
  <tr><td>status</td><td><span class='badge {n.state}'>{STATE_LABEL[n.state]}</span></td></tr>
  <tr><td>oracle</td><td>{esc(n.verdict['oracle'])}</td></tr>
  <tr><td>artifact sha256</td><td>{esc(n.verdict['artifact_sha256'])}</td></tr>
  <tr><td>re-run took</td><td>{esc(n.verdict.get('seconds', '—'))}s</td></tr>
  {details_rows}
</table>
{f"<div class='detail'>re-verify yourself: <code>python {esc(Path(artifact).name)}</code></div>" if artifact else ""}
{f"<pre class='log'>{esc(log)}</pre>" if log else ""}"""
    dead_block = (f"<h2>Ruled dead</h2><p>{esc(n.dead_reason)}</p>" if n.dead_reason else "")
    history = "".join(
        f"<tr data-of-row><td class='id'>{esc(e.ts[:19])}</td>"
        f"<td>{esc(e.type)} — {esc(_summarize(e))}</td></tr>"
        for e in n.history
    )
    return _shell(f"{n.id} · {n.title}", f"""
<p><a href='{esc(v.id)}.html'>&larr; {esc(v.spec['problem']['title'] if v.spec else v.id)}</a></p>
<h1>{esc(n.id)} <span class='sub'>{esc(n.title)}</span>{badge}{aim}</h1>
<table class='kv'>{program_line}{seat_line}</table>
{verdict_block}
{dead_block}
<h2>History</h2>
<table class='nodes'>{history}</table>
""")


def _summarize(ev: Event) -> str:
    from .cli import _summarize as s
    return s(ev)


def _feed_line(e: Event, show_problem=False) -> str:
    summary = esc(_summarize(e))
    lemma_id = e.data.get("lemma") or (e.data.get("id") if e.type == "lemma_stated" else None)
    if lemma_id:
        href = lemma_href(e.problem, lemma_id)
        summary = summary.replace(esc(str(lemma_id)), f"<a href='{esc(href)}'>{esc(lemma_id)}</a>", 1)
    problem_tag = f"<span class='detail'>[{esc(e.problem)}]</span> " if show_problem else ""
    return f"<div data-of-row><span class='ts'>{esc(e.ts[:19])}</span>{problem_tag}{esc(e.type)} — {summary}</div>"


def _shell(title: str, body: str, atom: str | None = None) -> str:
    atom_link = (f"<link rel='alternate' type='application/atom+xml' href='{esc(atom)}'>" if atom else "")
    return f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{esc(title)} · OpenFrontier</title>{atom_link}<style>{CSS}</style></head>
<body><main>{body}
<footer>
Checked means the oracle re-ran the artifact. Nothing here is an agent's own account.<br>
Sponsors back the work, never the verdict. · <a href='{REPO_URL}'>code</a> ·
<a href='{REPO_URL}/blob/main/SPEC.md'>spec</a> ·
<a href='feed.atom'>atom</a> · <a href='snapshot.json'>snapshot.json</a>
</footer></main><script>{SEARCH_JS}</script></body></html>"""
