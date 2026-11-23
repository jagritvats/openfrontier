"""Map view: one problem's programs and lemmas as a single inline SVG.

The grammar of the drawing is the grammar of the platform:

  lanes    one horizontal lane per program, in the order the programs were
           opened. Lemmas whose program is missing or unknown fall into a
           final lane labelled "unassigned".
  marker   the small circle at the left of a lane is the program itself.
  nodes    the lemmas of that program, left to right by id, each a rounded
           rectangle carrying the lemma id; its <title> holds
           "id -- title -- state" for the hover tooltip.
  edges    a straight line from the lane's marker to each of its lemmas:
           a program holds its lemmas, it does not merely list them.
  colours  the lemma's state. checked green, conjecture grey-blue, claimed
           amber, submitted / build_error cyan, refuted red, dead mauve.
           Dead lemmas are struck through, so the graveyard reads as one.

Output is deterministic: the same ProblemView renders byte-identical SVG.
"""
from __future__ import annotations

import html

from .model import Node, ProblemView

WIDTH = 880

STATE_FILL: dict[str, str] = {
    "checked": "#4ecb71",
    "conjecture": "#9aa7bd",
    "claimed": "#e0b040",
    "submitted": "#5fbcd3",
    "build_error": "#5fbcd3",
    "refuted": "#e06c60",
    "dead": "#b06a7a",
}

EDGE_COLOR = "#2a3342"
NODE_TEXT = "#0e1116"
LABEL_COLOR = "#8b93a1"
LANE_RULE = "#1b222c"

_LANE_H = 64
_PAD = 12
_LABEL_X = 14
_LABEL_W = 196
_LABEL_CHARS = 25
_MARKER_X = _LABEL_X + _LABEL_W
_MARKER_R = 5
_NODE_X0 = _MARKER_X + 18
_NODE_W = 120
_NODE_H = 34
_NODE_GAP = 12


def map_svg(view: ProblemView) -> str:
    """Render ``view`` as an inline SVG string (no XML header, width 880)."""
    lanes = _lanes(view)
    height = max(_LANE_H, _PAD * 2 + _LANE_H * len(lanes))
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" font-family="monospace" font-size="12" '
        f'role="img" aria-label="{_esc(f"map of {view.id}")}">'
    ]

    # lane rules first, so markers, edges and nodes sit on top of them
    for i in range(1, len(lanes)):
        y = _PAD + i * _LANE_H
        out.append(
            f'<line class="of-lane-rule" x1="0" y1="{y}" x2="{WIDTH}" y2="{y}" '
            f'stroke="{LANE_RULE}" stroke-width="1"/>'
        )

    for i, (pid, title, nodes) in enumerate(lanes):
        top = _PAD + i * _LANE_H
        cy = top + _LANE_H // 2
        node_y = top + (_LANE_H - _NODE_H) // 2

        for j in range(len(nodes)):
            x = _NODE_X0 + j * (_NODE_W + _NODE_GAP)
            out.append(
                f'<line class="of-edge" x1="{_MARKER_X + _MARKER_R}" y1="{cy}" '
                f'x2="{x}" y2="{cy}" stroke="{EDGE_COLOR}" stroke-width="1.5"/>'
            )

        label = "unassigned" if pid is None else (f"{pid} — {title}" if title else pid)
        shown = _clip(label, _LABEL_CHARS)
        label_svg = (
            f'<text class="of-lane-label" x="{_LABEL_X}" y="{cy + 4}" fill="{LABEL_COLOR}">'
            f"{_esc(shown)}"
        )
        if shown != label:
            label_svg += f"<title>{_esc(label)}</title>"
        label_svg += "</text>"
        out.append(label_svg)
        out.append(
            f'<circle class="of-program-marker" cx="{_MARKER_X}" cy="{cy}" '
            f'r="{_MARKER_R}" fill="{LABEL_COLOR}"/>'
        )

        for j, node in enumerate(nodes):
            x = _NODE_X0 + j * (_NODE_W + _NODE_GAP)
            out.append(_node_svg(node, x, node_y))

    out.append("</svg>")
    return "".join(out)


def _lanes(view: ProblemView) -> list[tuple[str | None, str, list[Node]]]:
    """Programs in insertion order, each with its lemmas sorted by id, then
    any node whose program is missing or unknown."""
    lanes: list[tuple[str | None, str, list[Node]]] = []
    for program in view.programs.values():
        pid = program["id"]
        nodes = sorted(
            (n for n in view.nodes.values() if n.program == pid), key=lambda n: n.id
        )
        lanes.append((pid, str(program.get("title") or ""), nodes))
    known = {pid for pid, _, _ in lanes}
    rest = sorted(
        (n for n in view.nodes.values() if n.program not in known), key=lambda n: n.id
    )
    if rest:
        lanes.append((None, "", rest))
    return lanes


def _node_svg(node: Node, x: int, y: int) -> str:
    fill = STATE_FILL.get(node.state, STATE_FILL["conjecture"])
    dead = node.state == "dead"
    stroke = f' stroke="{NODE_TEXT}" stroke-dasharray="4 3"' if dead else ""
    strike = ' style="text-decoration:line-through"' if dead else ""
    tooltip = f"{node.id} — {node.title} — {node.state}"
    return (
        f"<g>"
        f"<title>{_esc(tooltip)}</title>"
        f'<rect class="of-node {_esc(node.state)}" x="{x}" y="{y}" '
        f'width="{_NODE_W}" height="{_NODE_H}" rx="6" fill="{fill}"{stroke}/>'
        f'<text x="{x + _NODE_W // 2}" y="{y + _NODE_H // 2 + 4}" '
        f'text-anchor="middle" fill="{NODE_TEXT}"{strike}>{_esc(node.id)}</text>'
        f"</g>"
    )


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _esc(value: object) -> str:
    return html.escape(str(value))
