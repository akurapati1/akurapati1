/* Portfolio page logic. Vanilla JS, no dependencies, no network calls.
 *
 * Everything "AI" on this page runs locally in the visitor's browser:
 *   - Ask:  BM25 retrieval over the knowledge base, answers are quoted lines + visible sources (a tiny RAG).
 *   - Fit:  skill matching of a pasted job description against evidenced skill levels, gaps included.
 * Pure functions are exported for tests/web.test.js; DOM code only runs in a browser.
 */
(function () {
  "use strict";

  // ------------------------------------------------------------------ NLP helpers
  const STOP = new Set(("a an and are as at be but by can could did do does for from had has have he her his how i in is it its me my of on or our she so than that the their them then there these they this to us was we were what when where which who why will with would you your about tell give " +
    "abhilash him got get use used using").split(" "));

  const SYNONYMS = {
    gcp: ["google", "cloud"], jnj: ["johnson"], "j&j": ["johnson"], llm: ["llm"], llms: ["llm"], k8s: ["kubernetes"], postgres: ["postgresql"], ml: ["machine", "learning"],
    mlops: ["mlops", "deployment"], ai: ["ai"], agent: ["agentic", "agent"], agents: ["agentic", "agent"],
    job: ["role", "experience"], work: ["experience", "role"], worked: ["experience", "role"],
    built: ["build", "architected"], build: ["architected", "build"], projects: ["project"],
    contact: ["email", "linkedin", "contact"], hire: ["contact", "email"], reach: ["contact", "email"],
    trust: ["trustworthy", "validation", "review"], safe: ["trustworthy", "validation"],
    cloud: ["google", "cloud"], database: ["postgresql", "data"], databases: ["postgresql", "data"],
  };

  function stem(w) {
    if (w.length > 4 && w.endsWith("ies")) return w.slice(0, -3) + "y";
    if (w.length > 5 && w.endsWith("ing")) return w.slice(0, -3);
    if (w.length > 4 && w.endsWith("ed")) return w.slice(0, -2);
    if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss")) return w.slice(0, -1);
    return w;
  }

  function tokenize(text) {
    const raw = String(text).toLowerCase().replace(/&/g, " & ").match(/[a-z0-9&]+/g) || [];
    const out = [];
    for (const w of raw) {
      if (STOP.has(w) || w === "&") continue;
      out.push(stem(w));
    }
    return out;
  }

  function expandQuery(tokens, rawText) {
    const out = [];
    const rawLower = String(rawText).toLowerCase();
    if (/j\s*&\s*j/.test(rawLower)) out.push("johnson");
    for (const t of tokens) {
      out.push(t);
      for (const s of SYNONYMS[t] || []) out.push(stem(s));
    }
    return out;
  }

  // ------------------------------------------------------------------ BM25 retrieval
  // Evidence (what I actually did) should outrank blurbs (what I could do): BM25 alone favours short documents.
  const KIND_PRIOR = { experience: 1.4, project: 1.4, focus: 1.1, summary: 1.0, skills: 0.95, contact: 1.0, offer: 0.8, other: 1.0 };

  class Index {
    constructor(chunks) {
      this.chunks = chunks;
      this.k1 = 1.4;
      this.b = 0.7;
      this.docs = chunks.map((c) => tokenize(c.title + " " + c.title + " " + c.lines.join(" ")));
      this.avg = this.docs.reduce((n, d) => n + d.length, 0) / (this.docs.length || 1);
      this.df = new Map();
      for (const d of this.docs) for (const t of new Set(d)) this.df.set(t, (this.df.get(t) || 0) + 1);
      this.tf = this.docs.map((d) => {
        const m = new Map();
        for (const t of d) m.set(t, (m.get(t) || 0) + 1);
        return m;
      });
    }

    search(query) {
      const q = expandQuery(tokenize(query), query);
      const N = this.docs.length;
      const scores = this.docs.map((d, i) => {
        let s = 0;
        for (const t of new Set(q)) {
          const f = this.tf[i].get(t);
          if (!f) continue;
          const n = this.df.get(t);
          const idf = Math.log(1 + (N - n + 0.5) / (n + 0.5));
          s += idf * ((f * (this.k1 + 1)) / (f + this.k1 * (1 - this.b + (this.b * d.length) / this.avg)));
        }
        return { i, score: s * (KIND_PRIOR[this.chunks[i].kind] || 1) };
      });
      return scores.filter((x) => x.score > 0).sort((a, b) => b.score - a.score)
        .map((x) => ({ chunk: this.chunks[x.i], score: x.score }));
    }
  }

  const MIN_SCORE = 1.2;

  /** Compose an answer from retrieved chunks. Never invents text: it only quotes knowledge-base lines. */
  function answer(question, index) {
    const hits = index.search(question);
    const trace = hits.slice(0, 4).map((h) => ({ title: h.chunk.title, score: Math.round(h.score * 100) / 100 }));
    if (!hits.length || hits[0].score < MIN_SCORE) return { found: false, lines: [], sources: [], trace };
    const q = new Set(expandQuery(tokenize(question), question));
    // the best chunk always answers; a second one joins only if it is nearly as relevant
    const top = hits.filter((h, i) => i === 0 || h.score >= hits[0].score * 0.85).slice(0, 2);
    const lines = [];
    for (const h of top) {
      let chosen;
      if (h.chunk.lines.length <= 4) {
        chosen = h.chunk.lines.map((l, idx) => ({ l, idx })); // short chunk: quote it whole so key facts are never dropped
      } else {
        const ranked = h.chunk.lines
          .map((l, idx) => ({ l, idx, ov: tokenize(l).filter((t) => q.has(t)).length }))
          .sort((a, b) => b.ov - a.ov || a.idx - b.idx);
        const pick = ranked.filter((r) => r.ov > 0).slice(0, 3);
        chosen = (pick.length ? pick : ranked.slice(0, 2)).sort((a, b) => a.idx - b.idx);
      }
      for (const r of chosen) if (!lines.includes(r.l)) lines.push(r.l);
    }
    return { found: true, lines: lines.slice(0, 5), sources: top.map((h) => h.chunk.title), trace };
  }

  // ------------------------------------------------------------------ job-fit analysis
  const ALIASES = {
    "Google Cloud": ["gcp", "google cloud platform", "google cloud"], Kubernetes: ["k8s"], PostgreSQL: ["postgres"],
    "RAG Pipelines": ["rag", "retrieval augmented generation", "retrieval-augmented generation", "retrieval augmented"],
    "Agentic AI": ["agentic", "ai agents", "agent frameworks", "autonomous agents"],
    "Multi-Agent Reasoning": ["multi-agent", "multi agent"], "MCP Servers": ["mcp", "model context protocol"],
    "Prompt Engineering": ["prompt design", "prompting"], "Human-in-the-Loop": ["hitl", "human in the loop"],
    "Claude API": ["claude", "anthropic"], "OpenAI API": ["openai", "gpt-4", "gpt4", "chatgpt"],
    "CI/CD": ["ci cd", "continuous integration", "continuous delivery", "continuous deployment"],
    "Async Python ETL": ["etl"], "GKE": ["google kubernetes engine"], "scikit-learn": ["sklearn", "scikit learn"],
    "Node.js": ["nodejs", "node js"], "Pub/Sub": ["pubsub", "pub sub"], "Google ADK": ["adk", "agent development kit"],
    "RLHF-style Feedback Loops": ["rlhf"], "Vertex AI": ["vertex"], "Spring": ["spring boot"],
    "Dataflow": ["apache beam"], "FastAPI": ["fast api"], TypeScript: ["ts"], JavaScript: ["js"],
  };

  // Common stack terms a role might ask for. If one appears in the JD and is NOT in the profile, it is reported as a gap.
  const VOCAB = ["aws", "azure", "spark", "pyspark", "scala", "golang", "rust", "c++", "c#", ".net", "snowflake", "databricks",
    "airflow", "terraform", "ansible", "elasticsearch", "tableau", "power bi", "looker", "dbt", "hadoop", "cassandra",
    "dynamodb", "redshift", "sagemaker", "bedrock", "angular", "vue", "django", "graphql", "grpc", "helm", "prometheus",
    "grafana", "mlflow", "kubeflow", "pinecone", "weaviate", "faiss", "hugging face", "llamaindex", "autogen", "crewai",
    "fine-tuning", "fine tuning", "lora", "cuda", "computer vision", "time series", "a/b testing", "swift", "kotlin",
    "php", "ruby", "salesforce", "oracle", "sql server", "snowpark", "langsmith", "triton", "onnx", "ray", "flink"];

  function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

  function hasTerm(text, term) {
    const t = escapeRe(term.toLowerCase());
    return new RegExp("(^|[^a-z0-9+#.])" + t + "($|[^a-z0-9+#])", "i").test(text);
  }

  const WEIGHT = { core: 3, working: 2, familiar: 1 };

  function analyzeJD(rawText, categories) {
    const text = String(rawText).replace(/\s+/g, " ");
    const lower = text.toLowerCase();
    const matched = [];
    const profileTerms = new Set();
    for (const c of categories) {
      for (const s of c.skills) {
        const names = [s.name, ...(ALIASES[s.name] || [])];
        names.forEach((n) => profileTerms.add(n.toLowerCase()));
        let hit;
        if (s.name.length === 1) {
          hit = new RegExp("(^|[\\s,(/])" + escapeRe(s.name) + "($|[\\s,)/.;])").test(text);
        } else {
          hit = names.some((n) => hasTerm(lower, n));
        }
        if (hit) matched.push({ name: s.name, level: s.level, category: c.name });
      }
    }
    const gaps = VOCAB.filter((v) => !profileTerms.has(v) && hasTerm(lower, v));
    const total = matched.length + gaps.length;
    if (total < 3) return { verdict: "Not enough to judge", reason: "Few recognisable tech terms in the text.", matched, gaps, score: null };
    const score = matched.reduce((n, m) => n + WEIGHT[m.level], 0) / (3 * total);
    const verdict = score >= 0.75 ? "Strong" : score >= 0.55 ? "Good" : score >= 0.3 ? "Partial" : "Weak";
    return { verdict, score: Math.round(score * 100), matched, gaps, reason: "" };
  }

  // ------------------------------------------------------------------ exports for tests
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { tokenize, Index, answer, analyzeJD, stem, hasTerm, MIN_SCORE };
  }
  if (typeof document === "undefined") return;

  // ------------------------------------------------------------------ DOM
  const DATA = JSON.parse(document.getElementById("data").textContent);
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const el = (tag, attrs, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") n.className = v; else if (k === "text") n.textContent = v; else n.setAttribute(k, v);
    }
    kids.flat().forEach((k) => n.append(k));
    return n;
  };

  function issueUrl(template, params) {
    const q = new URLSearchParams(Object.assign({ template }, params || {}));
    return `https://github.com/${DATA.repo}/issues/new?${q.toString()}`;
  }

  // counters: final values are already in the HTML; this only adds a count-up when JS runs
  function initCounters() {
    const items = $$("[data-count]");
    if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        const n = e.target;
        const end = Number(n.dataset.count), suffix = n.dataset.suffix || "";
        const t0 = performance.now(), dur = 1100;
        const tick = (t) => {
          const p = Math.min(1, (t - t0) / dur), v = Math.round(end * (1 - Math.pow(1 - p, 3)));
          n.textContent = v.toLocaleString() + suffix;
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });
    }, { threshold: 0.4 });
    items.forEach((i) => io.observe(i));
  }

  // contribution heatmap with hover details
  function initHeatmap() {
    const host = $("#heatmap");
    const s = DATA.stats;
    if (!s || !s.weeks || !s.weeks.length) { host.append(el("p", { class: "muted", text: "Contribution data syncs daily - check back soon." })); return; }
    const tip = $("#tip");
    const colors = ["#1b222c", "#0e4429", "#006d32", "#26a641", "#39d353"];
    s.weeks.forEach((w, wi) => {
      const col = el("div", { class: "hm-col" });
      for (let d = 0; d < 7; d++) {
        const day = w.find((x) => x[3] === d);
        const cell = el("i", { class: "hm-cell" });
        if (day) {
          cell.style.background = colors[day[2]];
          cell.style.animationDelay = `${wi * 22}ms`;
          const label = `${day[1]} contribution${day[1] === 1 ? "" : "s"} on ${day[0]}`;
          cell.setAttribute("aria-label", label);
          cell.addEventListener("mouseenter", () => { tip.textContent = label; tip.hidden = false; });
          cell.addEventListener("mousemove", (e) => { tip.style.left = e.pageX + 12 + "px"; tip.style.top = e.pageY - 34 + "px"; });
          cell.addEventListener("mouseleave", () => { tip.hidden = true; });
        } else cell.style.visibility = "hidden";
        col.append(cell);
      }
      host.append(col);
    });
  }

  // skills explorer: filter by category/level/search, click for evidence from the knowledge base
  function initSkills() {
    const cats = DATA.categories;
    const state = { cat: "all", level: "all", q: "" };
    const catBar = $("#cat-filter"), grid = $("#skill-grid"), detail = $("#skill-detail");
    const levels = ["all", "core", "working", "familiar"];

    const mkBtn = (label, on, active) => { const b = el("button", { type: "button", class: "pill" + (active ? " on" : ""), text: label }); b.addEventListener("click", on); return b; };
    function drawBars() {
      catBar.replaceChildren(
        mkBtn("All", () => { state.cat = "all"; render(); }, state.cat === "all"),
        ...cats.map((c) => mkBtn(c.name, () => { state.cat = c.id; render(); }, state.cat === c.id)));
      $("#level-filter").replaceChildren(...levels.map((l) =>
        mkBtn(l === "all" ? "Any depth" : l, () => { state.level = l; render(); }, state.level === l)));
    }
    function evidence(name) {
      const idx = DATA.chunks.filter((c) => (c.title + " " + c.lines.join(" ")).toLowerCase().includes(name.toLowerCase().split(" ")[0]) && c.kind !== "skills");
      return idx.slice(0, 3);
    }
    function show(skill, cat) {
      const meaning = { core: "Shipped in real project work.", working: "Used it and comfortable.", familiar: "Exposure; not a headline strength." }[skill.level];
      const ev = evidence(skill.name);
      detail.replaceChildren(
        el("div", { class: "sd-head" }, el("strong", { text: skill.name }), el("span", { class: "tag lv-" + skill.level, text: skill.level })),
        el("p", { class: "muted", text: `${cat.name} - ${meaning}` }),
        ev.length ? el("ul", {}, ev.map((c) => el("li", {}, el("b", { text: c.title + ": " }), c.lines.find((l) => l.toLowerCase().includes(skill.name.toLowerCase().split(" ")[0])) || c.lines[0])))
                  : el("p", { class: "muted", text: "No dedicated project evidence listed yet." }));
      detail.hidden = false;
    }
    function render() {
      drawBars();
      grid.replaceChildren();
      const q = state.q.trim().toLowerCase();
      let n = 0;
      for (const c of cats) {
        if (state.cat !== "all" && state.cat !== c.id) continue;
        for (const s of c.skills) {
          if (state.level !== "all" && s.level !== state.level) continue;
          if (q && !s.name.toLowerCase().includes(q)) continue;
          const chip = el("button", { type: "button", class: "chip lv-" + s.level, style: `--c:${c.color}`, title: `${c.name} - ${s.level}` },
            el("i", { class: "dot" }), s.name);
          chip.addEventListener("click", () => show(s, c));
          grid.append(chip); n++;
        }
      }
      if (!n) grid.append(el("p", { class: "muted", text: "No skills match - try clearing the filters." }));
      $("#skill-count").textContent = `${n} skill${n === 1 ? "" : "s"}`;
    }
    $("#skill-search").addEventListener("input", (e) => { state.q = e.target.value; render(); });
    render();
  }

  // Ask: in-browser RAG
  function initAsk() {
    const index = new Index(DATA.chunks);
    const log = $("#chat-log"), form = $("#ask-form"), input = $("#ask-input"), trace = $("#trace");
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

    async function ask(q) {
      q = q.trim(); if (!q) return;
      log.append(el("div", { class: "msg me", text: q }));
      const bot = el("div", { class: "msg bot" }, el("span", { class: "typing", text: "retrieving..." }));
      log.append(bot); log.scrollTop = log.scrollHeight;
      await sleep(350);
      const r = answer(q, index);
      trace.replaceChildren(el("b", { text: "Retrieval trace " }),
        ...(r.trace.length ? r.trace.map((t) => el("span", { class: "tr" }, `${t.title} `, el("em", { text: t.score.toFixed(1) }))) : [el("span", { class: "muted", text: "no matching chunks" })]));
      bot.replaceChildren();
      if (!r.found) {
        bot.append(el("p", { text: "That's not in my profile data, so I won't guess." }),
          el("p", { class: "muted" }, "Try the deeper AI answer on GitHub, or ", el("a", { href: "mailto:" + DATA.email, text: "email me" }), "."));
      } else {
        bot.append(el("p", { class: "muted", text: "From my profile:" }));
        const ul = el("ul"); bot.append(ul);
        for (const l of r.lines) { ul.append(el("li", { text: l.replace(/^- /, "") })); await sleep(180); log.scrollTop = log.scrollHeight; }
        bot.append(el("p", { class: "src" }, "Sources: ", ...r.sources.map((s) => el("span", { class: "tag", text: s }))));
      }
      bot.append(el("a", { class: "deep", href: issueUrl("ask-ai.yml", { title: "Ask: " + q.slice(0, 60), question: q }), target: "_blank", rel: "noopener", text: "Get a generated (LLM) answer on GitHub ->" }));
      log.scrollTop = log.scrollHeight;
    }
    form.addEventListener("submit", (e) => { e.preventDefault(); const q = input.value; input.value = ""; ask(q); });
    $$(".suggest button").forEach((b) => b.addEventListener("click", () => ask(b.textContent)));
    // deep link from the GitHub README: ...?q=What+did+you+build#ask
    const preset = new URLSearchParams(location.search).get("q");
    if (preset) { ask(preset.slice(0, 300)); $("#ask").scrollIntoView(); }
  }

  // Fit check
  function initFit() {
    const btn = $("#fit-run"), area = $("#fit-text"), out = $("#fit-out");
    btn.addEventListener("click", () => {
      const r = analyzeJD(area.value, DATA.categories);
      out.replaceChildren();
      if (r.score === null) { out.append(el("p", { class: "muted", text: r.reason + " Paste the full requirements section." })); return; }
      out.append(
        el("div", { class: "verdict v-" + r.verdict.toLowerCase() }, el("strong", { text: r.verdict }), el("span", { text: ` fit - ${r.score}% weighted coverage` })),
        el("h4", { text: "Matches (shaded by depth)" }),
        el("div", { class: "chips" }, r.matched.length ? r.matched.map((m) => el("span", { class: "chip lv-" + m.level, title: m.level }, el("i", { class: "dot" }), m.name)) : [el("span", { class: "muted", text: "none found" })]),
        el("h4", { text: "Gaps - asked for, not in my profile" }),
        el("div", { class: "chips" }, r.gaps.length ? r.gaps.map((g) => el("span", { class: "chip gap", text: g })) : [el("span", { class: "muted", text: "no gaps detected from the common-tech list" })]),
        el("p", { class: "muted small", text: "Runs entirely in your browser: keyword matching against my skill levels. Deep, reasoned analysis is available via the GitHub job-fit check." }),
        el("a", { class: "deep", href: issueUrl("jd-match.yml"), target: "_blank", rel: "noopener", text: "Get a generated (LLM) fit report on GitHub ->" }));
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.documentElement.classList.add("js");
    initCounters(); initHeatmap(); initSkills(); initAsk(); initFit();
  });
})();
