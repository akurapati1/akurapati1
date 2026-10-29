"""Tiny helpers for hand-built animated SVGs (SMIL + CSS, no dependencies).

GitHub renders README images through <img>, which runs SMIL and CSS animation
but no scripts, no external fonts and no pointer events. Everything here is
built within those limits.
"""
from __future__ import annotations

import itertools
from xml.sax.saxutils import escape

BG = "#0d1117"
PANEL = "#161b22"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
CYAN = "#58a6ff"
VIOLET = "#a371f7"
GREEN = "#3fb950"
ORANGE = "#f0883e"
PINK = "#f778ba"
TEAL = "#2dd4bf"

MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"

_ids = itertools.count(1)


def uid(prefix: str = "i") -> str:
    return f"{prefix}{next(_ids)}"


def reset_ids() -> None:
    global _ids
    _ids = itertools.count(1)


def esc(s: str) -> str:
    return escape(str(s), {'"': "&quot;"})


def f(n: float) -> str:
    """Compact number formatting."""
    s = f"{n:.2f}".rstrip("0").rstrip(".")
    return s or "0"


def blend(hex_a: str, hex_b: str, t: float) -> str:
    """Linear blend: t=1 -> a, t=0 -> b."""
    a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
    c = [round(x * t + y * (1 - t)) for x, y in zip(a, b)]
    return "#%02x%02x%02x" % tuple(c)


def svg_doc(w: int, h: int, body: str, *, defs: str = "", style: str = "",
            title: str = "", desc: str = "") -> str:
    label = f' aria-label="{esc(title)}"' if title else ""
    t = f"<title>{esc(title)}</title>" if title else ""
    d = f"<desc>{esc(desc)}</desc>" if desc else ""
    st = f"<style>{style}</style>" if style else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"{label}>{t}{d}'
        f"<defs>{defs}</defs>{st}{body}</svg>\n"
    )


def window(t0: float, t1: float, cycle: float, fade: float = 0.3) -> str:
    """<animate> that fades an element in at t0 and out at t1 inside a looping cycle.

    t1 >= cycle means "stay until the loop restarts".
    """
    fade = max(0.01, min(fade, (cycle - t0) / 2 if cycle > t0 else fade))
    pts: list[tuple[float, int]] = []
    if t0 <= 0:
        pts.append((0.0, 1))
    else:
        pts += [(0.0, 0), (t0, 0), (t0 + fade, 1)]
    if t1 >= cycle:
        pts.append((cycle, 1))
    else:
        pts += [(t1, 1), (min(t1 + fade, cycle - 0.001), 0), (cycle, 0)]
    # strictly increasing key times
    clean: list[tuple[float, int]] = []
    for t, v in pts:
        if clean and t <= clean[-1][0]:
            t = clean[-1][0] + 0.0005
        clean.append((min(t, cycle), v))
    clean[-1] = (cycle, clean[-1][1])
    kt = ";".join(f(t / cycle) if t < cycle else "1" for t, _ in clean)
    vals = ";".join(str(v) for _, v in clean)
    return (f'<animate attributeName="opacity" dur="{f(cycle)}s" repeatCount="indefinite" '
            f'keyTimes="{kt}" values="{vals}"/>')


def timed(inner: str, t0: float, t1: float, cycle: float, fade: float = 0.3,
          attrs: str = "") -> str:
    """Group that is only visible between t0 and t1 of a looping cycle."""
    return f'<g opacity="0" {attrs}>{window(t0, t1, cycle, fade)}{inner}</g>'


def typed_text(x: float, y: float, text: str, size: float, t0: float, t1: float,
               cycle: float, fill: str = TEXT, cw: float = 0.6, weight: str = "normal",
               family: str = MONO, cursor: str | None = None) -> tuple[str, str]:
    """Typewriter reveal. Returns (defs, body). Visible from t0 until the loop restarts.

    Width is pinned with textLength so the clip reveal matches the glyphs exactly.
    """
    cid = uid("clip")
    w = len(text) * size * cw
    kt = f"0;{f(t0 / cycle)};{f(t1 / cycle)};1"
    defs = (f'<clipPath id="{cid}"><rect x="{f(x)}" y="{f(y - size)}" height="{f(size * 1.5)}" width="0">'
            f'<animate attributeName="width" dur="{f(cycle)}s" repeatCount="indefinite" '
            f'keyTimes="{kt}" values="0;0;{f(w)};{f(w)}"/></rect></clipPath>')
    body = (f'<text x="{f(x)}" y="{f(y)}" font-family="{family}" font-size="{f(size)}" '
            f'font-weight="{weight}" fill="{fill}" textLength="{f(w)}" lengthAdjust="spacing" '
            f'clip-path="url(#{cid})" xml:space="preserve">{esc(text)}</text>')
    if cursor:
        body += (f'<rect y="{f(y - size * 0.95)}" width="{f(size * 0.55)}" height="{f(size * 1.15)}" fill="{cursor}">'
                 f'<animate attributeName="x" dur="{f(cycle)}s" repeatCount="indefinite" keyTimes="{kt}" '
                 f'values="{f(x)};{f(x)};{f(x + w)};{f(x + w)}"/></rect>')
    return defs, body


def frames_text(x: float, y: float, frames: list[str], t0: float, t1: float,
                cycle: float, size: float, fill: str, anchor: str = "start",
                weight: str = "700", family: str = SANS, last_fill: str | None = None) -> str:
    """Count-up / countdown: one <text> per frame, each visible for its slice."""
    n = len(frames)
    out = []
    for i, txt in enumerate(frames):
        a = t0 + (t1 - t0) * i / n
        b = t0 + (t1 - t0) * (i + 1) / n if i < n - 1 else cycle
        col = last_fill if (last_fill and i == n - 1) else fill
        out.append(
            f'<text x="{f(x)}" y="{f(y)}" text-anchor="{anchor}" font-family="{family}" '
            f'font-size="{f(size)}" font-weight="{weight}" fill="{col}" opacity="0">'
            f'{window(a, b, cycle, fade=0.01)}{esc(txt)}</text>'
        )
    return "".join(out)


def rrect(x, y, w, h, r=10, fill=PANEL, stroke=BORDER, sw=1, extra="") -> str:
    return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{r}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')


def text(x, y, s, size=12, fill=TEXT, anchor="start", weight="normal",
         family=SANS, extra="") -> str:
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{family}" font-size="{f(size)}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{esc(s)}</text>')


def card_bg(w: int, h: int, r: int = 14) -> str:
    return (f'<rect width="{w}" height="{h}" rx="{r}" fill="url(#bg)"/>'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{r}" fill="none" stroke="{BORDER}"/>')


def bg_gradient(w: int, h: int) -> str:
    return (f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#111a2b"/></linearGradient>')
