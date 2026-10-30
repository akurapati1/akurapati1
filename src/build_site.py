"""Build the standalone portfolio webpage into docs/ (served by GitHub Pages).

Static-first: all text, numbers and graphics are in the HTML itself. app.js only adds
interactivity (heatmap tooltips, skill explorer, in-browser RAG, fit check).
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from contributions import summarize

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DOCS = ROOT / "docs"


def knowledge_chunks(profile: dict, knowledge_md: str) -> list[dict]:
    """Split knowledge.md by heading into retrievable chunks, plus skills and offers."""
    chunks, h2, h3, lines = [], None, None, []

    def flush():
        if lines and h2 == "Focus areas":
            # one retrievable chunk per focus area so each can be found on its own
            for ln in lines:
                label = ln.split(":", 1)[0]
                chunks.append({"title": f"Focus areas › {label}", "kind": "focus", "lines": [ln]})
            lines.clear()
        elif lines:
            kind = {"Experience": "experience", "Projects": "project", "Focus areas": "focus",
                    "Contact": "contact", "Summary": "summary"}.get(h2 or "", "other")
            chunks.append({"title": " › ".join(x for x in (h2, h3) if x), "kind": kind, "lines": list(lines)})
            lines.clear()

    for raw in knowledge_md.splitlines():
        if raw.startswith("## "):
            flush(); h2, h3 = raw[3:].strip(), None
        elif raw.startswith("### "):
            flush(); h3 = raw[4:].strip()
        elif raw.startswith("- "):
            lines.append(raw[2:].strip())
    flush()

    for c in profile["categories"]:
        by: dict[str, list[str]] = {"core": [], "working": [], "familiar": []}
        for s in c["skills"]:
            by[s["level"]].append(s["name"])
        text = [f"{lvl}: {', '.join(v)}" for lvl, v in by.items() if v]
        chunks.append({"title": f"Skills › {c['name']}", "kind": "skills", "lines": text})
    for title, desc in profile["offers"]:
        chunks.append({"title": f"What I can build › {title}", "kind": "offer", "lines": [desc]})
    return chunks


def compact_stats(stats: dict | None) -> dict | None:
    if not stats or not stats.get("contributions", {}).get("weeks"):
        return None
    weeks = stats["contributions"]["weeks"]
    return {
        "weeks": [[[d["date"], d["count"], d["level"], d["weekday"]] for d in w["days"]] for w in weeks],
        "summary": summarize(weeks), "repos": stats.get("public_repos", 0),
    }


def _metric_html(m: dict) -> str:
    if m["kind"] == "frames":
        big, attrs = m["frames"][-1], ""
    else:
        big = f'{m["value"]:,}{m.get("suffix", "")}'
        attrs = f' data-count="{m["value"]}" data-suffix="{html.escape(m.get("suffix", ""))}"'
    was = f'<s class="was">was {html.escape(m["was"])}</s>' if m.get("was") else ""
    return (f'<div class="tile" style="--c:{m["color"]}">{was}<div class="big"{attrs}>{html.escape(big)}</div>'
            f'<div class="lbl">{html.escape(m["label"])}</div><div class="cap">{html.escape(m["caption"])}</div></div>')


def _live_html(s: dict | None) -> str:
    if not s:
        return ""
    sm = s["summary"]
    items = [(sm["total"], "", "contributions", "last 12 months", "#39d353"),
             (sm["active"], "", "active days", "days with commits / PRs", "#58a6ff"),
             (sm["longest"], " days", "longest streak", "consecutive days", "#a371f7"),
             (s["repos"], "", "public repos", "own, non-fork", "#f0883e")]
    return "".join(
        f'<div class="tile" style="--c:{c}"><div class="big" data-count="{v}" data-suffix="{html.escape(suf)}">{v:,}{suf}</div>'
        f'<div class="lbl">{lbl}</div><div class="cap">{cap}</div></div>' for v, suf, lbl, cap, c in items)


def build(profile: dict, knowledge_md: str, stats: dict | None) -> None:
    DOCS.mkdir(exist_ok=True)
    (DOCS / "assets").mkdir(exist_ok=True)
    for svg in (ROOT / "assets").glob("*.svg"):
        shutil.copy2(svg, DOCS / "assets" / svg.name)
    shutil.copy2(SRC / "web" / "style.css", DOCS / "style.css")
    shutil.copy2(SRC / "web" / "app.js", DOCS / "app.js")
    (DOCS / ".nojekyll").write_text("")

    cs = compact_stats(stats)
    data = {
        "repo": f'{profile["login"]}/{profile["login"]}', "email": profile["email"],
        "categories": profile["categories"], "chunks": knowledge_chunks(profile, knowledge_md), "stats": cs,
    }
    data_json = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    tpl = (SRC / "web" / "index.template.html").read_text(encoding="utf-8")
    suggestions = [q["q"] for q in profile["demo_questions"]] + ["Which skills are you strongest in?"]
    repl = {
        "NAME": html.escape(profile["name"]), "TITLE": html.escape(profile["title"]),
        "LOCATION": html.escape(profile["location"]), "EMPLOYER": html.escape(profile["employer"]),
        "EMAIL": html.escape(profile["email"]), "LINKEDIN": html.escape(profile["linkedin"]),
        "GITHUB": f'https://github.com/{profile["login"]}',
        "METRICS": "".join(_metric_html(m) for m in profile["metrics"][:4]),
        "LIVE": _live_html(cs),
        "OFFERS": "".join(f"<li><b>{html.escape(t)}</b><span>{html.escape(d)}</span></li>" for t, d in profile["offers"]),
        "SUGGESTIONS": "".join(f"<button type=\"button\">{html.escape(q)}</button>" for q in suggestions),
        "DATA": data_json,
    }
    for k, v in repl.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    (DOCS / "index.html").write_text(tpl, encoding="utf-8")
    print("wrote", DOCS / "index.html")
