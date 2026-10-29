"""AI demonstrations: an agent pipeline running live, and a Q&A terminal."""
from __future__ import annotations

from svgkit import (BORDER, CYAN, GREEN, MONO, MUTED, ORANGE, PANEL, PINK, SANS, TEXT, VIOLET,
                    bg_gradient, card_bg, f, frames_text, rrect, svg_doc, text, timed, typed_text,
                    window, BG)

# --------------------------------------------------------------------------- pipeline
NODES = [
    ("01", "Request", "NL or scheduled", CYAN),
    ("02", "Planner", "LangGraph / ADK", VIOLET),
    ("03", "Retrieve", "RAG · BigQuery", PINK),
    ("04", "Synthesize", "LLM drafting", ORANGE),
    ("05", "Validate", "guardrails + HITL", GREEN),
    ("06", "Deliver", "FastAPI · GKE", CYAN),
]

LOG = [
    ("planner", "decomposing request into sub-tasks", VIOLET),
    ("retrieve", "pulling grounded context from the data layer", PINK),
    ("synth", "drafting with citations to retrieved sources", ORANGE),
    ("validate", "checks passed; routing to human review", GREEN),
    ("deliver", "approved report published via API", CYAN),
]


def pipeline() -> str:
    W, H = 960, 500
    CYCLE = 14.0
    slot = 1.7
    start = 0.8
    bw, bh, gap, x0, y = 118, 70, 36, 36, 96

    defs = bg_gradient(W, H) + (
        '<filter id="gl" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="4"/></filter>')
    style = (".pk{filter:url(#gl)}")
    b = [card_bg(W, H)]
    b.append(text(32, 40, "AGENT PIPELINE · LIVE", 12, MUTED, weight="700", family=MONO, extra='letter-spacing="2"'))
    b.append(text(32, 62, "The shape of the agentic systems I build on Google Cloud", 13, MUTED))

    centers = []
    for i, (num, name, sub, col) in enumerate(NODES):
        x = x0 + i * (bw + gap)
        centers.append((x, x + bw))
        t0 = start + i * slot
        b.append(rrect(x, y, bw, bh, 12, fill=PANEL, stroke=BORDER))
        b.append(text(x + 12, y + 20, num, 10, col, weight="700", family=MONO))
        b.append(text(x + 12, y + 42, name, 15, TEXT, weight="700"))
        b.append(text(x + 12, y + 59, sub, 10, MUTED, family=MONO))
        # active highlight
        hl = (f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="12" fill="{col}" fill-opacity="0.12" '
              f'stroke="{col}" stroke-width="1.6"/>'
              f'<rect class="pk" x="{x}" y="{y}" width="{bw}" height="{bh}" rx="12" fill="none" stroke="{col}" '
              f'stroke-width="3" opacity="0.7"/>')
        b.append(timed(hl, t0, t0 + slot + 0.5, CYCLE, fade=0.2))

    # edges + travelling packets
    for i in range(len(NODES) - 1):
        xa, xb = centers[i][1], centers[i + 1][0]
        ym = y + bh / 2
        b.append(f'<line x1="{xa}" y1="{ym}" x2="{xb}" y2="{ym}" stroke="{BORDER}" stroke-width="2" stroke-dasharray="4 4"/>')
        b.append(f'<path d="M{xb - 7} {ym - 5} L{xb} {ym} L{xb - 7} {ym + 5}" fill="none" stroke="{MUTED}" stroke-width="1.6"/>')
        t0 = start + i * slot + slot * 0.55
        t1 = t0 + slot * 0.7
        col = NODES[i + 1][3]
        k = [0, t0 / CYCLE, t1 / CYCLE, 1]
        kt = ";".join(f(v) for v in k)
        b.append(
            f'<g opacity="0">{window(t0, t1, CYCLE, fade=0.05)}'
            f'<animateMotion dur="{f(CYCLE)}s" repeatCount="indefinite" keyTimes="{kt}" '
            f'keyPoints="0;0;1;1" calcMode="linear" path="M{xa} {ym} L{xb} {ym}"/>'
            f'<circle r="7" fill="{col}" opacity="0.35"/><circle r="3.2" fill="{col}"/></g>')

    # Human-in-the-loop feedback arc under validate -> synthesize
    vx = centers[4][0] + bw / 2
    sx = centers[3][0] + bw / 2
    yy = y + bh
    arc = (f'<path d="M{vx} {yy} C{vx} {yy + 30} {sx} {yy + 30} {sx} {yy}" fill="none" stroke="{GREEN}" '
           f'stroke-width="1.4" stroke-dasharray="3 4" stroke-opacity="0.8"/>')
    b.append(arc)
    b.append(text((vx + sx) / 2, yy + 48, "feedback loop: reviewer edits improve the next draft", 10,
                  GREEN, anchor="middle", family=MONO))

    # terminal
    ty = 236
    tw = 560
    b.append(rrect(36, ty, tw, 198, 10, fill="#0a0e14", stroke=BORDER))
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        b.append(f'<circle cx="{54 + i * 16}" cy="{ty + 17}" r="4.5" fill="{c}"/>')
    b.append(text(116, ty + 21, "agent.log", 11, MUTED, family=MONO))
    b.append(frames_text(36 + tw - 14, ty + 21, [f"t+{i * 4.8:04.1f}s" for i in range(14)], 0.3, CYCLE - 1.2,
                         CYCLE, 11, GREEN, anchor="end", weight="400", family=MONO))
    for i, (tag, msg, col) in enumerate(LOG):
        t0 = start + i * slot * 1.2 + 0.4
        yy2 = ty + 50 + i * 28
        d1, b1 = typed_text(56, yy2, f"[{tag}]", 12.5, t0, t0 + 0.4, CYCLE, fill=col, weight="700")
        d2, b2 = typed_text(56 + (len(tag) + 3) * 7.5, yy2, msg, 12.5, t0 + 0.4, t0 + 0.4 + len(msg) * 0.035, CYCLE,
                            fill=TEXT)
        b.append(f"<defs>{d1}{d2}</defs>{b1}{b2}")
    # clear the log right before the loop restarts
    b.append(f'<rect x="38" y="{ty + 30}" width="{tw - 4}" height="{198 - 34}" fill="#0a0e14" opacity="0">'
             f'{window(CYCLE - 0.5, CYCLE, CYCLE, fade=0.3)}</rect>')

    # race bars
    rx, rw = 632, 292
    b.append(rrect(rx - 16, ty, rw + 32, 198, 10, fill=PANEL, stroke=BORDER))
    b.append(text(rx, ty + 28, "TURNAROUND TIME", 10.5, MUTED, weight="700", family=MONO, extra='letter-spacing="1.5"'))
    b.append(text(rx, ty + 58, "Manual process", 12, TEXT, weight="600"))
    b.append(text(rx + rw, ty + 58, "2-3 weeks", 12, ORANGE, anchor="end", weight="700", family=MONO))
    b.append(f'<rect x="{rx}" y="{ty + 66}" width="{rw}" height="12" rx="6" fill="#21262d"/>')
    b.append(f'<rect x="{rx}" y="{ty + 66}" width="0" height="12" rx="6" fill="{ORANGE}">'
             f'<animate attributeName="width" dur="{f(CYCLE)}s" repeatCount="indefinite" keyTimes="0;0.15;0.85;0.95;1" '
             f'values="0;{rw};{rw};0;0"/></rect>')
    b.append(text(rx, ty + 112, "Agentic pipeline", 12, TEXT, weight="600"))
    b.append(text(rx + rw, ty + 112, "under 1 min", 12, GREEN, anchor="end", weight="700", family=MONO))
    b.append(f'<rect x="{rx}" y="{ty + 120}" width="{rw}" height="12" rx="6" fill="#21262d"/>')
    b.append(f'<rect x="{rx}" y="{ty + 120}" width="4" height="12" rx="6" fill="{GREEN}"/>')
    b.append(f'<circle cx="{rx + 4}" cy="{ty + 126}" r="9" fill="{GREEN}" opacity="0.35">'
             f'<animate attributeName="r" values="5;13;5" dur="1.6s" repeatCount="indefinite"/>'
             f'<animate attributeName="opacity" values="0.5;0;0.5" dur="1.6s" repeatCount="indefinite"/></circle>')
    b.append(text(rx, ty + 168, "20,000x+", 28, GREEN, weight="800"))
    b.append(text(rx + 150, ty + 168, "faster turnaround", 12, MUTED))
    b.append(text(rx, ty + 186, "Johnson & Johnson medical reports (stated in README)", 9.5, MUTED, family=MONO))

    b.append(text(32, H - 22, "Illustrative reference architecture - not a client diagram. Components vary per project.",
                  10, MUTED, family=MONO))
    return svg_doc(W, H, "".join(b), defs=defs, style=style, title="Live agent pipeline",
                   desc="A request flows through planner, retrieval, synthesis, validation and delivery agents")


# --------------------------------------------------------------------------- terminal Q&A
def terminal(profile: dict) -> str:
    W, H = 960, 250
    qas = profile["demo_questions"]
    slot = 9.0
    CYCLE = slot * len(qas)
    defs = bg_gradient(W, H)
    b = [card_bg(W, H)]
    b.append(rrect(24, 20, W - 48, H - 40, 10, fill="#0a0e14", stroke=BORDER))
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        b.append(f'<circle cx="{44 + i * 16}" cy="38" r="4.5" fill="{c}"/>')
    b.append(text(W / 2, 42, "ask-abhilash  -  grounded in my real projects", 11, MUTED, anchor="middle", family=MONO))
    for i, qa in enumerate(qas):
        t0 = i * slot
        q = "$ " + qa["q"]
        parts = []
        d, tq = typed_text(48, 84, q, 15, t0 + 0.3, t0 + 0.3 + len(q) * 0.045, CYCLE, fill=CYAN, weight="700")
        defs += d
        parts.append(tq)
        ans_t = t0 + 0.3 + len(q) * 0.045 + 0.6
        parts.append(timed(
            f'<circle cx="52" cy="112" r="3.5" fill="{VIOLET}"><animate attributeName="opacity" values="1;.2;1" dur="0.6s" repeatCount="indefinite"/></circle>'
            + text(64, 116, "retrieving context · reasoning · citing sources", 12, MUTED, family=MONO),
            ans_t - 0.5, ans_t, CYCLE, fade=0.05))
        yy = 148
        for ln in qa["a"]:
            dd, tt = typed_text(48, yy, ln, 14, ans_t, ans_t + len(ln) * 0.03, CYCLE, fill=TEXT)
            defs += dd
            parts.append(tt)
            ans_t += len(ln) * 0.03 + 0.15
            yy += 24
        b.append(timed("".join(parts), t0, t0 + slot - 0.3, CYCLE, fade=0.2))
    b.append(text(48, 220, "answers are generated from my real project data - try it live below", 11.5, GREEN, family=MONO))
    return svg_doc(W, H, "".join(b), defs=defs, title="Ask my AI",
                   desc="Animated terminal answering recruiter questions about Abhilash's experience")
