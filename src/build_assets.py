"""Build every animated SVG and refresh the generated parts of README.md.

    python src/build_assets.py            # uses src/data/github_stats.json if present
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import build_site, contributions, demo_viz, hero, impact, skills_viz  # noqa: E402
from svgkit import BG, blend, reset_ids  # noqa: E402

LEVEL_MIX = {"core": 1.0, "working": 0.62, "familiar": 0.34}
LEVEL_ORDER = {"core": 0, "working": 1, "familiar": 2}
CAT_EMOJI = {"ai": "🤖", "cloud": "☁️", "data": "🗄️", "backend": "⚙️", "ml": "🧪", "lang": "💻"}


def load(name: str):
    p = SRC / "data" / name
    return json.loads(p.read_text()) if p.exists() else None


def badge(skill: dict, color: str, anchor: str = "") -> str:
    label = quote(skill["name"].replace("-", "--").replace("_", "__").replace(" ", "_"), safe="_-")
    col = blend(color, BG, LEVEL_MIX[skill["level"]]).lstrip("#")
    url = f"https://img.shields.io/badge/{label}-{col}?style=flat-square"
    if skill.get("logo"):
        url += f"&logo={skill['logo']}&logoColor=white"
    img = f'<img src="{url}" alt="{skill["name"]} ({skill["level"]})" />'
    # GitHub links bare images to the raw file; a same-page anchor makes the click a no-op instead
    return f'<a href="#{anchor}">{img}</a>' if anchor else img


def skills_markdown(profile: dict) -> str:
    out = []
    for c in profile["categories"]:
        sk = sorted(c["skills"], key=lambda s: LEVEL_ORDER[s["level"]])
        core = sum(1 for s in sk if s["level"] == "core")
        out.append(
            f'<a id="skills-{c["id"]}"></a>\n<details>\n<summary><b>{CAT_EMOJI.get(c["id"], "•")} {c["name"]}</b>'
            f' &nbsp;·&nbsp; {len(sk)} skills, {core} proven in shipped work</summary>\n<br/>\n\n'
            + "\n".join(badge(s, c["color"], f'skills-{c["id"]}') for s in sk) + "\n\n</details>\n"
        )
    return "\n".join(out)


def offers_markdown(profile: dict) -> str:
    rows = "\n".join(f"<tr><td><b>{t}</b></td><td>{d}</td></tr>" for t, d in profile["offers"])
    return f"<table>\n{rows}\n</table>"


def site_badges(profile: dict) -> tuple[str, str]:
    """Website badges, shown only once GitHub Pages is live (profile.json: site_live)."""
    if not profile.get("site_live"):
        return "", ""
    url = profile["site_url"]
    big = (f'<a href="{url}"><img src="https://img.shields.io/badge/🌐%20OPEN%20THE%20INTERACTIVE%20SITE-'
           f'Ask%20my%20AI%20·%20Skills%20·%20Fit%20check-1f6feb?style=for-the-badge" alt="Open the interactive site" /></a>')
    small = (f'<a href="{url}"><img src="https://img.shields.io/static/v1?message=Website&logo=googlechrome&label='
             f'&color=1f6feb&logoColor=white&style=for-the-badge" height="35" alt="Website" /></a>')
    return big, small


def replace_region(text: str, name: str, content: str) -> str:
    pat = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    if not pat.search(text):
        return text
    return pat.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text)


def main() -> None:
    profile = load("profile.json")
    stats = load("github_stats.json")
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)

    builders = {
        "hero.svg": lambda: hero.build(profile),
        "contributions.svg": lambda: contributions.build(stats),
        "impact.svg": lambda: impact.build(profile, stats),
        "skill-stream.svg": lambda: skills_viz.ticker(profile),
        "skill-constellation.svg": lambda: skills_viz.constellation(profile),
        "agent-pipeline.svg": lambda: demo_viz.pipeline(),
        "ask-terminal.svg": lambda: demo_viz.terminal(profile),
    }
    for name, fn in builders.items():
        reset_ids()
        (assets / name).write_text(fn(), encoding="utf-8")
        print("wrote", assets / name)

    knowledge = (SRC / "data" / "knowledge.md").read_text(encoding="utf-8")
    build_site.build(profile, knowledge, stats)

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = replace_region(text, "SKILLS", skills_markdown(profile))
    text = replace_region(text, "OFFERS", offers_markdown(profile))
    big, small = site_badges(profile)
    text = replace_region(text, "SITE_HERO", big)
    text = replace_region(text, "SITE_CONTACT", small)
    readme.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
