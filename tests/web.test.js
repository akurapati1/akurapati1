// node tests/web.test.js  (run after `python src/build_assets.py`, which writes docs/index.html)
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { Index, answer, analyzeJD, tokenize, MIN_SCORE } = require("../src/web/app.js");

const html = fs.readFileSync(path.join(__dirname, "../docs/index.html"), "utf8");
const DATA = JSON.parse(/<script type="application\/json" id="data">(.*?)<\/script>/s.exec(html)[1].replace(/<\\\//g, "</"));
const index = new Index(DATA.chunks);
let n = 0;
const test = (name, fn) => { fn(); n++; console.log("ok -", name); };

test("tokenizer drops stopwords and stems", () => {
  assert.deepStrictEqual(tokenize("What did the agents build?"), ["agent", "build"]);
});

const top = (q) => answer(q, index);
test("J&J question retrieves the J&J experience", () => {
  const r = top("What did you build at Johnson & Johnson?");
  assert.ok(r.found); assert.match(r.sources.join("|"), /Johnson/);
  assert.match(r.lines.join(" "), /2-3 weeks/);
});
test("J&J abbreviation works", () => {
  assert.match(top("tell me about your J&J work").sources.join("|"), /Johnson/);
});
test("multi-agent question finds the Market Researcher", () => {
  const r = top("Have you built multi-agent LLM systems?");
  assert.ok(r.found); assert.match(r.sources.join("|"), /Agentic Market Researcher/);
});
test("SQL question finds the SQL agent", () => {
  assert.match(top("do you have experience with SQL and natural language queries").sources.join("|"), /SQL Data Retrieval/);
});
test("contact question returns contact info", () => {
  assert.match(top("how can I reach you?").lines.join(" "), /@|linkedin/i);
});
test("trustworthy AI question finds HITL material", () => {
  assert.match(top("how do you make AI output trustworthy?").lines.join(" "), /human-in-the-loop/i);
});
test("off-topic questions are refused, not guessed", () => {
  for (const q of ["what is your favourite food", "who won the world cup", "asdf qwer zxcv"]) {
    const r = top(q); assert.strictEqual(r.found, false, q);
  }
});
test("answers only quote knowledge-base lines", () => {
  const all = new Set(DATA.chunks.flatMap((c) => c.lines));
  for (const q of ["what projects have you built", "what is your stack for MLOps", "tell me about RAG"]) {
    for (const l of top(q).lines) assert.ok(all.has(l), "not from KB: " + l);
  }
});

const JD = `We need an AI engineer with strong Python, LangGraph and RAG experience on Google Cloud (GCP).
Experience with Kubernetes, Docker and CI/CD. Nice to have: Terraform, Spark, Snowflake and AWS.`;
test("fit check matches skills and aliases, lists gaps", () => {
  const r = analyzeJD(JD, DATA.categories);
  const names = r.matched.map((m) => m.name);
  for (const s of ["Python", "LangGraph", "RAG Pipelines", "Google Cloud", "Kubernetes", "Docker", "CI/CD"]) assert.ok(names.includes(s), s);
  for (const g of ["terraform", "spark", "snowflake", "aws"]) assert.ok(r.gaps.includes(g), g);
  assert.ok(["Good", "Partial"].includes(r.verdict), "3 gaps in ~9 asks must not read as Strong: " + r.verdict);
});
test("fit check says Strong only when there are no meaningful gaps", () => {
  const r = analyzeJD("Python, LangGraph, RAG, Google Cloud, Kubernetes and Docker experience required.", DATA.categories);
  assert.strictEqual(r.verdict, "Strong"); assert.strictEqual(r.gaps.length, 0);
});
test("fit check is honest about a mismatched role", () => {
  const r = analyzeJD("Looking for a Swift and Kotlin mobile developer, with Ruby, PHP and Salesforce.", DATA.categories);
  assert.ok(["Weak", "Partial"].includes(r.verdict), r.verdict);
  assert.ok(r.gaps.length >= 4);
});
test("fit check refuses to judge thin text", () => {
  assert.strictEqual(analyzeJD("We are a friendly team.", DATA.categories).score, null);
});
test("single-letter skill R does not match 'R&D'", () => {
  const r = analyzeJD("R&D team with Python, GCP and Docker", DATA.categories);
  assert.ok(!r.matched.some((m) => m.name === "R"));
});
test("page is static-first: counters and text are in the HTML", () => {
  assert.match(html, /<div class="big"[^>]*>&lt;1 min<\/div>/);
  assert.match(html, /assets\/hero\.svg/);
  assert.ok(!/\{\{[A-Z]+\}\}/.test(html), "unfilled template placeholder");
});
console.log(`\n${n} passed`);
