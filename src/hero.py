"""Hero banner: pulsing neural network + typewriter role line."""
from __future__ import annotations

import math
import random

from svgkit import (BG, BORDER, CYAN, GREEN, MONO, MUTED, SANS, TEXT, VIOLET, bg_gradient,
                    card_bg, f, svg_doc, text, timed, typed_text)

W, H = 960, 320
CYCLE_PER_ROLE = 4.0


def _network():
    """Layered nodes on the right side; returns (nodes_by_layer, edges)."""
    layers_x = [560, 650, 740, 830, 910]
    counts = [4, 6, 7, 6, 3]
    rnd = random.Random(7)
    layers = []
    for x, c in zip(layers_x, counts):
        top, bottom = 52, H - 52
        step = (bottom - top) / (c - 1)
        layers.append([(x + rnd.uniform(-6, 6), top + i * step + rnd.uniform(-5, 5)) for i in range(c)])
    edges = []
    for a, b in zip(layers, layers[1:]):
        for i, p in enumerate(a):
            # connect to the 2-3 nearest nodes in the next layer
            near = sorted(b, key=lambda q: abs(q[1] - p[1]))[:3]
            for q in near:
                edges.append((p, q))
    return layers, edges


def build(profile: dict) -> str:
    roles = profile["roles"]
    cycle = CYCLE_PER_ROLE * len(roles)
    layers, edges = _network()

    defs = bg_gradient(W, H) + (
        f'<linearGradient id="name" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{TEXT}"/><stop offset="0.6" stop-color="{CYAN}"/>'
        f'<stop offset="1" stop-color="{VIOLET}"/></linearGradient>'
        f'<radialGradient id="glow" cx="0.75" cy="0.5" r="0.6">'
        f'<stop offset="0" stop-color="{VIOLET}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>'
    )
    style = (
        ".n{animation:np 3.2s ease-in-out infinite}"
        "@keyframes np{0%,100%{opacity:.35}50%{opacity:1}}"
        ".e{stroke-dasharray:3 5;animation:flow 2.4s linear infinite}"
        "@keyframes flow{to{stroke-dashoffset:-16}}"
        ".dot{animation:blink 1.6s ease-in-out infinite}"
        "@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}"
    )

    body = [card_bg(W, H), f'<rect width="{W}" height="{H}" rx="14" fill="url(#glow)"/>']

    # edges
    for (x1, y1), (x2, y2) in edges:
        body.append(f'<line class="e" x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" '
                    f'stroke="{CYAN}" stroke-opacity="0.22" stroke-width="1"/>')
    # travelling signals
    rnd = random.Random(11)
    for k in range(14):
        p, q = rnd.choice(edges)
        dur = rnd.uniform(1.6, 3.0)
        begin = rnd.uniform(0, 3)
        col = rnd.choice([CYAN, VIOLET, GREEN])
        body.append(
            f'<circle r="2.4" fill="{col}"><animateMotion dur="{f(dur)}s" begin="{f(begin)}s" '
            f'repeatCount="indefinite" path="M{f(p[0])} {f(p[1])} L{f(q[0])} {f(q[1])}"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" dur="{f(dur)}s" begin="{f(begin)}s" '
            f'repeatCount="indefinite"/></circle>')
    # nodes
    for li, layer in enumerate(layers):
        for ni, (x, y) in enumerate(layer):
            delay = (li * 0.45 + ni * 0.27) % 3.2
            col = VIOLET if li in (0, 4) else CYAN
            body.append(f'<circle class="n" cx="{f(x)}" cy="{f(y)}" r="{4 if li in (0, 4) else 3.2}" '
                        f'fill="{col}" style="animation-delay:-{f(delay)}s"/>')

    # copy
    body.append(text(48, 58, "● LIVE PROFILE", 11, GREEN, weight="700", family=MONO,
                     extra='letter-spacing="2" class="dot"'))
    body.append(text(48, 118, profile["name"], 46, "url(#name)", weight="800"))
    body.append(text(48, 150, f'{profile["title"]}  ·  {profile["location"]}', 15, MUTED, family=MONO))
    body.append(text(48, 172, f'now: {profile["employer"]}', 13, MUTED, family=MONO))

    # typed roles
    cw, size = 0.6, 19
    for i, role in enumerate(roles):
        t0 = i * CYCLE_PER_ROLE + 0.2
        t1 = t0 + 1.9
        end = (i + 1) * CYCLE_PER_ROLE - 0.15
        d, b = typed_text(48, 232, "> " + role, size, t0, t1, cycle, fill=CYAN, cw=cw, cursor=VIOLET)
        # hold the revealed text only during its own slot
        body.append(f'<defs>{d}</defs>' + timed(b, i * CYCLE_PER_ROLE, end, cycle, fade=0.15))

    body.append(f'<line x1="48" y1="262" x2="470" y2="262" stroke="{BORDER}"/>')
    body.append(text(48, 288, "Production-grade agentic systems on Google Cloud", 12.5, MUTED))

    return svg_doc(W, H, "".join(body), defs=defs, style=style,
                   title=f'{profile["name"]} - {profile["title"]}',
                   desc="Animated neural network banner with rotating taglines")
