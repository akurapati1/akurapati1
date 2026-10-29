"""Animated contribution heatmap rendered from GitHub's contribution calendar."""
from __future__ import annotations

import datetime as dt

from svgkit import (BORDER, CYAN, GREEN, MONO, MUTED, SANS, TEXT, bg_gradient, card_bg, f,
                    frames_text, svg_doc, text)

W, H = 960, 270
PITCH, SIZE = 16, 12.5
X0, Y0 = 56, 104
CYCLE = 14.0
LEVEL_FILL = ["#1b222c", "#0e4429", "#006d32", "#26a641", "#39d353"]


def empty_calendar(today: dt.date | None = None) -> list[dict]:
    """53 weeks of zero days ending today - used before the first sync."""
    today = today or dt.date.today()
    start = today - dt.timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
    start -= dt.timedelta(weeks=52)
    weeks = []
    for w in range(53):
        days = []
        for d in range(7):
            day = start + dt.timedelta(weeks=w, days=d)
            if day <= today:
                days.append({"date": day.isoformat(), "count": 0, "level": 0, "weekday": d})
        weeks.append({"days": days})
    return weeks


def summarize(weeks: list[dict]) -> dict:
    days = [d for w in weeks for d in w["days"]]
    days.sort(key=lambda d: d["date"])
    total = sum(d["count"] for d in days)
    active = sum(1 for d in days if d["count"] > 0)
    best = max((d["count"] for d in days), default=0)
    longest = cur = 0
    for d in days:
        cur = cur + 1 if d["count"] > 0 else 0
        longest = max(longest, cur)
    # current streak: allow today to be empty (not over yet)
    current = 0
    for d in reversed(days):
        if d["count"] > 0:
            current += 1
        elif d is days[-1]:
            continue
        else:
            break
    return {"total": total, "active": active, "best": best, "longest": longest, "current": current}


def _count_frames(total: int, n: int = 28) -> list[str]:
    out = []
    for i in range(1, n + 1):
        p = i / n
        eased = 1 - (1 - p) ** 3
        out.append(f"{round(total * eased):,}")
    return out


def build(stats: dict | None) -> str:
    synced = bool(stats and stats.get("contributions", {}).get("weeks"))
    weeks = stats["contributions"]["weeks"] if synced else empty_calendar()
    s = summarize(weeks)

    defs = bg_gradient(W, H) + (
        '<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset="0.5" stop-color="#fff" stop-opacity="0.22"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="gridclip"><rect x="{X0 - 4}" y="{Y0 - 4}" width="{len(weeks) * PITCH + 8}" height="{7 * PITCH + 8}"/></clipPath>'
    )
    # Static-first: every element is visible without animation; animation only adds a pulse wave.
    style = (
        f".c{{transform-box:fill-box;transform-origin:center;animation:pop {f(CYCLE)}s ease-in-out infinite}}"
        "@keyframes pop{0%,8%,100%{transform:scale(1)}3%{transform:scale(1.55)}}"
        ".tw{fill:none;stroke:#fff;stroke-width:1.2;animation:tw 2.6s ease-in-out infinite}"
        "@keyframes tw{0%,100%{opacity:0}50%{opacity:.9}}"
    )

    b = [card_bg(W, H)]
    b.append(text(32, 40, "CONTRIBUTIONS", 12, MUTED, weight="700", family=MONO, extra='letter-spacing="2"'))
    b.append(text(32, 76, "", 1))  # keeps y rhythm predictable for tests
    if synced:
        b.append(text(32, 82, f"{s['total']:,}", 40, TEXT, weight="700"))
        b.append(text(32 + 14 + len(f"{s['total']:,}") * 22, 82, "in the last year", 14, MUTED))
    else:
        b.append(text(32, 82, "syncing...", 34, MUTED, weight="700"))

    # right-hand stat chips
    chips = [("active days", s["active"]), ("longest streak", s["longest"]), ("best day", s["best"])]
    cx = W - 32
    for label, val in reversed(chips):
        b.append(text(cx, 58, str(val) if synced else "-", 22, GREEN if synced else MUTED,
                      anchor="end", weight="700", family=SANS))
        b.append(text(cx, 76, label, 10.5, MUTED, anchor="end", family=MONO))
        cx -= 120

    # month labels + day labels
    month_marks = []
    last_month = None
    for wi, w in enumerate(weeks):
        if not w["days"]:
            continue
        d0 = dt.date.fromisoformat(w["days"][0]["date"])
        if d0.month != last_month:
            month_marks.append((wi, d0))
            last_month = d0.month
    for i, (wi, d0) in enumerate(month_marks):
        nxt = month_marks[i + 1][0] if i + 1 < len(month_marks) else 99
        if nxt - wi >= 3 and X0 + wi * PITCH < W - 40:  # skip cramped partial months
            b.append(text(X0 + wi * PITCH, Y0 - 10, d0.strftime("%b"), 10, MUTED, family=MONO))
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        b.append(text(X0 - 8, Y0 + row * PITCH + SIZE - 2, name, 9.5, MUTED, anchor="end", family=MONO))

    # cells
    cells = []
    for wi, w in enumerate(weeks):
        for d in w["days"]:
            wd = d.get("weekday", dt.date.fromisoformat(d["date"]).isoweekday() % 7)
            x = X0 + wi * PITCH
            y = Y0 + wd * PITCH
            lvl = max(0, min(4, int(d.get("level", 0))))
            delay = wi * 0.035 + wd * 0.012
            cells.append(f'<rect class="c" x="{x}" y="{y}" width="{SIZE}" height="{SIZE}" rx="2.5" '
                         f'fill="{LEVEL_FILL[lvl]}" style="animation-delay:{f(delay)}s"/>')
            if lvl == 4:
                td = (wi * 0.37 + wd * 0.21) % 2.6
                cells.append(f'<rect class="tw" x="{x}" y="{y}" width="{SIZE}" height="{SIZE}" rx="2.5" '
                             f'style="animation-delay:-{f(td)}s"/>')
    b.append("".join(cells))

    # light sweep over the grid
    gw = len(weeks) * PITCH
    b.append(
        f'<g clip-path="url(#gridclip)"><rect y="{Y0 - 4}" width="70" height="{7 * PITCH + 8}" fill="url(#sweep)" opacity="0">'
        f'<animate attributeName="x" dur="{f(CYCLE)}s" repeatCount="indefinite" '
        f'keyTimes="0;0.22;0.5;1" values="{X0 - 80};{X0 - 80};{X0 + gw};{X0 + gw}"/>'
        f'<animate attributeName="opacity" dur="{f(CYCLE)}s" repeatCount="indefinite" '
        f'keyTimes="0;0.22;0.23;0.5;0.51;1" values="0;0;1;1;0;0"/></rect></g>')

    # legend
    lx = X0 + gw - 5 * (SIZE + 4) - 70
    ly = Y0 + 7 * PITCH + 16
    b.append(text(lx, ly + 10, "Less", 10, MUTED, anchor="end", family=MONO))
    for i, col in enumerate(LEVEL_FILL):
        b.append(f'<rect x="{lx + 8 + i * (SIZE + 4)}" y="{ly}" width="{SIZE}" height="{SIZE}" rx="2.5" fill="{col}"/>')
    b.append(text(lx + 8 + 5 * (SIZE + 4) + 4, ly + 10, "More", 10, MUTED, family=MONO))

    if synced:
        cur = s["current"]
        b.append(text(X0, ly + 10, f"current streak: {cur} day{'s' if cur != 1 else ''}", 10.5, MUTED, family=MONO))
    else:
        b.append(text(X0, ly + 10,
                      'waiting for first sync: run the "Refresh profile" workflow to light this up with real data',
                      10.5, CYAN, family=MONO))

    return svg_doc(W, H, "".join(b), defs=defs, style=style, title="Animated GitHub contribution graph",
                   desc=f"{s['total']} contributions in the last year" if synced else "Contribution graph pending first sync")
