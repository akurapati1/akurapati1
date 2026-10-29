"""Skill visuals: scrolling ticker and a constellation graph."""
from __future__ import annotations

import math

from svgkit import (BORDER, MONO, MUTED, PANEL, SANS, TEXT, bg_gradient, blend, card_bg, esc, f,
                    svg_doc, text, BG)

LEVEL_ALPHA = {"core": 1.0, "working": 0.62, "familiar": 0.34}


# --------------------------------------------------------------------------- ticker
def ticker(profile: dict) -> str:
    W = 960
    cats = profile["categories"]
    rows = [
        [(s, c) for c in cats if c["id"] in ("ai", "ml", "lang") for s in c["skills"]],
        [(s, c) for c in cats if c["id"] in ("cloud", "data", "backend") for s in c["skills"]],
    ]
    # core skills first so the eye lands on them
    order = {"core": 0, "working": 1, "familiar": 2}
    H = 150
    body = [card_bg(W, H)]
    body.append(text(32, 36, "SKILL STREAM", 12, MUTED, weight="700", family=MONO, extra='letter-spacing="2"'))
    legend_x = W - 32
    for lvl in ("familiar", "working", "core"):
        body.append(text(legend_x, 36, lvl, 10.5, MUTED, anchor="end", family=MONO))
        legend_x -= 14 + len(lvl) * 6.4
        body.append(f'<circle cx="{f(legend_x + 6)}" cy="32" r="4" fill="#58a6ff" opacity="{LEVEL_ALPHA[lvl]}"/>')
        legend_x -= 18
    defs = bg_gradient(W, H) + (
        '<linearGradient id="fadeX" x1="0" x2="1" y1="0" y2="0">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.07" stop-color="#fff"/>'
        '<stop offset="0.93" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="fm"><rect width="{W}" height="{H}" fill="url(#fadeX)"/></mask>'
    )
    strips = []
    for ri, items in enumerate(rows):
        items = sorted(items, key=lambda it: order[it[0]["level"]])
        if ri == 1:
            items = items[::-1]
        # chip layout
        chips, x = [], 0.0
        for s, c in items:
            w = len(s["name"]) * 7.1 + 26
            chips.append((x, w, s, c))
            x += w + 10
        block_w = x
        reps = max(1, math.ceil((W + 40) / block_w))
        # build one block (repeated reps times), then duplicate for seamless loop
        one = []
        for r in range(reps):
            for cx, cw_, s, c in chips:
                a = LEVEL_ALPHA[s["level"]]
                col = c["color"]
                px = cx + r * block_w
                one.append(
                    f'<g transform="translate({f(px)},0)">'
                    f'<rect width="{f(cw_)}" height="30" rx="15" fill="{blend(col, BG, 0.16 * a + 0.04)}" '
                    f'stroke="{col}" stroke-opacity="{f(0.25 + 0.6 * a)}"/>'
                    f'<circle cx="14" cy="15" r="3.2" fill="{col}" opacity="{f(a)}"/>'
                    f'<text x="24" y="19.5" font-family="{SANS}" font-size="12.5" font-weight="{600 if s["level"] == "core" else 500}" '
                    f'fill="{TEXT}" fill-opacity="{f(0.45 + 0.55 * a)}">{esc(s["name"])}</text></g>')
        span = block_w * reps
        y = 54 + ri * 44
        dur = 38 + ri * 9
        frm, to = (0, -span) if ri == 0 else (-span, 0)
        strips.append(
            f'<g transform="translate(0,{y})"><g>'
            f'<animateTransform attributeName="transform" type="translate" from="{f(frm)} 0" to="{f(to)} 0" '
            f'dur="{dur}s" repeatCount="indefinite"/>'
            f'{"".join(one)}<g transform="translate({f(span)},0)">{"".join(one)}</g></g></g>')
    body.append(f'<g mask="url(#fm)">{"".join(strips)}</g>')
    return svg_doc(W, H, "".join(body), defs=defs, title="Skill stream",
                   desc="Scrolling ticker of skills, brighter chips are skills used in shipped projects")


# --------------------------------------------------------------------------- constellation
def constellation(profile: dict) -> str:
    W, H = 960, 680
    cx, cy = W / 2, H / 2 + 14
    cats = profile["categories"]
    defs = bg_gradient(W, H) + (
        '<radialGradient id="core" cx="0.5" cy="0.5" r="0.5">'
        '<stop offset="0" stop-color="#58a6ff" stop-opacity="0.9"/><stop offset="1" stop-color="#a371f7" stop-opacity="0.15"/></radialGradient>'
    )
    style = (
        ".ed{stroke-dasharray:2 6;animation:fl 3s linear infinite}"
        "@keyframes fl{to{stroke-dashoffset:-16}}"
        ".tw{animation:tw 3.4s ease-in-out infinite}"
        "@keyframes tw{0%,100%{opacity:.55}50%{opacity:1}}"
        ".rg{transform-box:fill-box;transform-origin:center;animation:rg 5s ease-out infinite}"
        "@keyframes rg{0%{transform:scale(.4);opacity:.7}100%{transform:scale(2.6);opacity:0}}"
        ".hub{transform-box:fill-box;transform-origin:center;animation:hb 4s ease-in-out infinite}"
        "@keyframes hb{0%,100%{transform:scale(1)}50%{transform:scale(1.12)}}"
    )
    b = [card_bg(W, H)]
    b.append(text(32, 40, "SKILL CONSTELLATION", 12, MUTED, weight="700", family=MONO, extra='letter-spacing="2"'))
    b.append(text(32, 60, "brighter star = used in shipped projects", 11, MUTED, family=MONO))

    # ripples from the centre
    for i in range(3):
        b.append(f'<circle class="rg" cx="{f(cx)}" cy="{f(cy)}" r="40" fill="none" stroke="#58a6ff" '
                 f'stroke-width="1.2" style="animation-delay:-{i * 1.66:.2f}s"/>')

    hub_r_x, hub_r_y = 235, 205
    n = len(cats)
    edges, nodes, labels, hubs = [], [], [], []
    for ci, c in enumerate(cats):
        ang = -math.pi / 2 + ci * 2 * math.pi / n
        hx, hy = cx + hub_r_x * math.cos(ang), cy + hub_r_y * math.sin(ang)
        col = c["color"]
        edges.append(f'<line class="ed" x1="{f(cx)}" y1="{f(cy)}" x2="{f(hx)}" y2="{f(hy)}" stroke="{col}" '
                     f'stroke-opacity="0.45" stroke-width="1.4" style="animation-delay:-{ci * 0.5}s"/>')
        sk = [s for s in c["skills"] if s.get("graph")]
        k = len(sk)
        out = ang  # fan outward from the centre
        spread = min(math.radians(150), math.radians(34) * max(k - 1, 1))
        for si, s in enumerate(sk):
            a = out + (0 if k == 1 else -spread / 2 + spread * si / (k - 1))
            ring = 84 + (42 if (k > 5 and si % 2) else 0)
            sx = hx + ring * math.cos(a) * 1.25
            sy = hy + ring * math.sin(a) * 0.95
            lvl = s["level"]
            al = {"core": 1.0, "working": 0.7, "familiar": 0.4}[lvl]
            r = {"core": 4.6, "working": 3.6, "familiar": 3}[lvl]
            edges.append(f'<line x1="{f(hx)}" y1="{f(hy)}" x2="{f(sx)}" y2="{f(sy)}" stroke="{col}" '
                         f'stroke-opacity="{f(0.14 + 0.2 * al)}" stroke-width="1"/>')
            nodes.append(f'<circle class="tw" cx="{f(sx)}" cy="{f(sy)}" r="{r}" fill="{col}" opacity="{f(al)}" '
                         f'style="animation-delay:-{(ci * 1.3 + si * 0.53) % 3.4:.2f}s"/>')
            right = math.cos(a) >= -0.15
            dx = 9 if right else -9
            labels.append(text(sx + dx, sy + 4, s.get("short", s["name"]), 11.5, TEXT, anchor="start" if right else "end",
                               weight="600" if lvl == "core" else "400", extra=f'fill-opacity="{f(0.5 + 0.5 * al)}"'))
        hubs.append(
            f'<g><circle class="hub" cx="{f(hx)}" cy="{f(hy)}" r="9" fill="{col}"/>'
            f'<circle cx="{f(hx)}" cy="{f(hy)}" r="15" fill="none" stroke="{col}" stroke-opacity="0.35"/></g>')
        # hub title sits on the inner side so it never collides with the skill fan
        halo = f'paint-order="stroke" stroke="{BG}" stroke-width="5" stroke-linejoin="round"'
        title = c["name"].upper()
        if abs(math.cos(ang)) < 0.25:
            ty = hy + (34 if math.sin(ang) < 0 else -26)
            labels.append(text(hx, ty, title, 10.5, col, anchor="middle", weight="700", family=MONO,
                               extra=f'letter-spacing="1.2" {halo}'))
        else:
            inward = -1 if math.cos(ang) > 0 else 1
            labels.append(text(hx + inward * 20, hy + 4, title, 10.5, col,
                               anchor="start" if inward > 0 else "end", weight="700", family=MONO,
                               extra=f'letter-spacing="1.2" {halo}'))
    b += edges + nodes + hubs + labels
    # core
    b.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="34" fill="url(#core)"/>'
             f'<circle cx="{f(cx)}" cy="{f(cy)}" r="34" fill="none" stroke="#58a6ff" stroke-opacity="0.8"/>')
    b.append(text(cx, cy - 2, "ABHILASH", 11, TEXT, anchor="middle", weight="800", family=MONO))
    b.append(text(cx, cy + 12, "AI ENGINEER", 8, TEXT, anchor="middle", weight="600", family=MONO))
    return svg_doc(W, H, "".join(b), defs=defs, style=style, title="Skill constellation",
                   desc="Animated graph connecting skill categories to individual skills")
