"""Impact counters: stated project outcomes (profile.json) + live GitHub numbers."""
from __future__ import annotations

from contributions import summarize
from svgkit import (GREEN, MONO, MUTED, PANEL, BORDER, SANS, TEXT, bg_gradient, card_bg, f,
                    rrect, svg_doc, text, blend)

W = 960
TILE_W, TILE_H, GAP = 216, 104, 16
MARGIN = 24
CYCLE = 10.0


def _tile(x, y, color, big, label, caption, was=None):
    b = [rrect(x, y, TILE_W, TILE_H, 12, fill=PANEL, stroke=BORDER)]
    b.append(f'<rect class="ac" x="{x}" y="{y + 14}" width="3" height="{TILE_H - 28}" rx="1.5" fill="{color}"/>')
    b.append(text(x + 20, y + 52, big, 34, color, weight="700"))
    if was:
        b.append(text(x + TILE_W - 14, y + 17, f"was {was}", 10, MUTED, anchor="end", family=MONO,
                      extra='text-decoration="line-through"'))
    b.append(text(x + 20, y + 74, label, 12.5, TEXT, weight="600"))
    b.append(text(x + 20, y + 92, caption, 10, MUTED, family=MONO))
    return "".join(b)


def build(profile: dict, stats: dict | None) -> str:
    rows = 2
    h = 72 + rows * TILE_H + (rows - 1) * GAP + 44
    b = [card_bg(W, h)]
    b.append(text(32, 40, "IMPACT", 12, MUTED, weight="700", family=MONO, extra='letter-spacing="2"'))
    b.append(text(32, 62, "What the systems I build actually moved", 13, MUTED))

    # row 1 - outcomes
    y = 78
    for i, m in enumerate(profile["metrics"][:4]):
        x = MARGIN + i * (TILE_W + GAP)
        big = m["frames"][-1] if m["kind"] == "frames" else f'{m["value"]:,}{m.get("suffix", "")}'
        b.append(_tile(x, y, m["color"], big, m["label"], m["caption"], was=m.get("was")))

    # row 2 - live numbers
    y += TILE_H + GAP
    synced = bool(stats and stats.get("contributions", {}).get("weeks"))
    live = []
    if synced:
        s = summarize(stats["contributions"]["weeks"])
        live = [
            (s["total"], "", "contributions", "last 12 months", "#39d353"),
            (s["active"], "", "active days", "days with commits/PRs", "#58a6ff"),
            (s["longest"], " days", "longest streak", "consecutive days", "#a371f7"),
            (stats.get("public_repos", 0), "", "public repos", "own, non-fork", "#f0883e"),
        ]
    else:
        live = [(None, "", n, "syncs from GitHub", MUTED) for n in
                ("contributions", "active days", "longest streak", "public repos")]
    for i, (val, suf, label, cap, col) in enumerate(live):
        x = MARGIN + i * (TILE_W + GAP)
        big = "-" if val is None else f"{int(val):,}{suf}"
        b.append(_tile(x, y, col, big, label, cap))

    b.append(text(W - 32, h - 14, "live numbers refresh daily via GitHub Actions", 10, MUTED, anchor="end", family=MONO))
    style = (".ac{transform-box:fill-box;transform-origin:center;animation:ac 4s ease-in-out infinite}"
             "@keyframes ac{0%,100%{transform:scaleY(1)}50%{transform:scaleY(.55)}}")
    return svg_doc(W, h, "".join(b), defs=bg_gradient(W, h), style=style, title="Impact metrics",
                   desc="Animated counters for project outcomes and live GitHub activity")
