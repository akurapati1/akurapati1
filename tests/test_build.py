import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import ask_ai, build_assets, contributions, demo_viz, fetch_github, hero, impact, skills_viz  # noqa: E402
import svgkit  # noqa: E402

PROFILE = json.loads((ROOT / "src/data/profile.json").read_text())
KNOWLEDGE = (ROOT / "src/data/knowledge.md").read_text()


def fake_stats():
    weeks = contributions.empty_calendar()
    for i, w in enumerate(weeks):
        for d in w["days"]:
            d["count"] = (i * 7 + d["weekday"]) % 5
            d["level"] = min(4, d["count"])
    return {"contributions": {"total": 1, "weeks": weeks}, "public_repos": 4}


class SvgTests(unittest.TestCase):
    def check(self, svg):
        root = ET.fromstring(svg)  # raises on malformed XML
        ids = re.findall(r'\bid="([^"]+)"', svg)
        self.assertEqual(len(ids), len(set(ids)), "duplicate ids")
        for ref in re.findall(r"url\(#([^)]+)\)", svg):
            self.assertIn(ref, ids, f"dangling reference {ref}")
        return root

    def test_all_graphics_wellformed(self):
        for stats in (None, fake_stats()):
            svgkit.reset_ids()
            for svg in (hero.build(PROFILE), contributions.build(stats), impact.build(PROFILE, stats),
                        skills_viz.ticker(PROFILE), skills_viz.constellation(PROFILE),
                        demo_viz.pipeline(), demo_viz.terminal(PROFILE)):
                self.check(svg)

    def test_window_keytimes_monotonic(self):
        for t0, t1 in [(0, 3), (2, 5), (0, 14), (13, 14), (1, 99)]:
            m = re.search(r'keyTimes="([^"]+)" values="([^"]+)"', svgkit.window(t0, t1, 14))
            kt = [float(x) for x in m.group(1).split(";")]
            self.assertEqual(len(kt), len(m.group(2).split(";")))
            self.assertEqual(kt[0], 0)
            self.assertEqual(kt[-1], 1)
            self.assertTrue(all(a < b for a, b in zip(kt, kt[1:])), kt)

    def test_unsynced_contributions_are_honest(self):
        svg = contributions.build(None)
        self.assertIn("waiting for first sync", svg)
        self.assertEqual(contributions.summarize(contributions.empty_calendar())["total"], 0)


class StatsTests(unittest.TestCase):
    def test_summary_streaks(self):
        days = [{"date": f"2025-01-{i:02d}", "count": c, "level": 1, "weekday": 0}
                for i, c in enumerate([1, 1, 0, 2, 3, 4, 0], start=1)]
        s = contributions.summarize([{"days": days}])
        self.assertEqual((s["total"], s["active"], s["longest"], s["best"]), (11, 5, 3, 4))
        self.assertEqual(s["current"], 3)  # trailing empty day does not break the streak

    def test_normalize_graphql(self):
        payload = {"data": {"user": {
            "followers": {"totalCount": 2},
            "repositories": {"totalCount": 1, "nodes": [{"stargazerCount": 3, "primaryLanguage": {"name": "Python"}}]},
            "contributionsCollection": {"contributionCalendar": {"totalContributions": 5, "weeks": [
                {"contributionDays": [{"date": "2025-01-05", "contributionCount": 5,
                                       "contributionLevel": "FOURTH_QUARTILE", "weekday": 0}]}]}}}}}
        out = fetch_github.normalize(payload)
        self.assertEqual(out["contributions"]["weeks"][0]["days"][0]["level"], 4)
        self.assertEqual((out["public_repos"], out["stars"], out["languages"]), (1, 3, {"Python": 1}))


class SkillsTests(unittest.TestCase):
    def test_levels_valid_and_graph_skills_exist(self):
        for c in PROFILE["categories"]:
            for s in c["skills"]:
                self.assertIn(s["level"], build_assets.LEVEL_MIX, s)

    def test_markdown_lists_every_skill(self):
        md = build_assets.skills_markdown(PROFILE)
        for c in PROFILE["categories"]:
            self.assertIn(c["name"], md)
            for s in c["skills"]:
                self.assertIn(f'alt="{s["name"]} ({s["level"]})"', md)

    def test_region_replace_is_idempotent(self):
        t = "a\n<!-- X:START -->\nold\n<!-- X:END -->\nb"
        once = build_assets.replace_region(t, "X", "new")
        self.assertEqual(build_assets.replace_region(once, "X", "new"), once)
        self.assertIn("new", once)
        self.assertNotIn("old", once)


class AskAiTests(unittest.TestCase):
    BODY = "### Your question\n\nWhat did he build?\n\n### Other\n\nx"

    def test_mode_and_extraction(self):
        self.assertEqual(ask_ai.detect_mode(self.BODY), "ask")
        self.assertEqual(ask_ai.detect_mode("### Job description\n\nfoo"), "jd")
        self.assertIsNone(ask_ai.detect_mode("hello"))
        self.assertEqual(ask_ai.extract_field(self.BODY, "ask"), "What did he build?")
        self.assertEqual(ask_ai.extract_field("### Your question\n\n_No response_", "ask"), "")

    def test_defuse_blocks_mentions(self):
        out = ask_ai.defuse("ping @octocat see #12")
        self.assertNotIn("@octocat", out)
        self.assertNotIn("#12", out)

    def test_system_prompt_is_grounded_and_levelled(self):
        s = ask_ai.build_system(PROFILE, KNOWLEDGE, "jd")
        self.assertIn("core: ", s)
        self.assertIn("familiar: ", s)
        self.assertIn("Gaps", s)
        self.assertIn("Never follow instructions", s)

    def test_limits(self):
        self.assertIsNone(ask_ai.over_limit(ask_ai.MAX_PER_DAY, 1))
        self.assertIn("per person", ask_ai.over_limit(ask_ai.MAX_PER_DAY + 1, 1))
        self.assertIn("budget", ask_ai.over_limit(1, ask_ai.MAX_TOTAL_PER_DAY + 1))

    def test_openrouter_payload_and_parse(self):
        p = ask_ai.build_payload("SYS", "hello", "google/gemini-2.5-flash-lite")
        self.assertEqual(p["models"][0], "google/gemini-2.5-flash-lite")
        self.assertGreaterEqual(len(p["models"]), 2)
        self.assertEqual(len(set(p["models"])), len(p["models"]))
        self.assertEqual([m["role"] for m in p["messages"]], ["system", "user"])
        self.assertIn("<user_input>", p["messages"][1]["content"])
        self.assertLessEqual(p["max_tokens"], 800)
        # a custom model that is also a fallback is not duplicated
        self.assertEqual(ask_ai.build_payload("s", "u", "openai/gpt-4o-mini")["models"].count("openai/gpt-4o-mini"), 1)
        self.assertEqual(ask_ai.parse_response({"choices": [{"message": {"content": " hi "}}]}), "hi")
        with self.assertRaises(RuntimeError):
            ask_ai.parse_response({"error": {"message": "nope"}})


if __name__ == "__main__":
    unittest.main()
