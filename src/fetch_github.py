"""Fetch contribution calendar + repo stats via the GitHub GraphQL API.

Runs inside GitHub Actions with the built-in GITHUB_TOKEN (public activity) or a
PAT in PROFILE_TOKEN (if you also want private contributions counted).
Stdlib only. On any failure it leaves the previous JSON untouched and exits 0
so a hiccup never blanks the profile.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "data" / "github_stats.json"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER, isFork: false, first: 100,
                 orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes { stargazerCount primaryLanguage { name } }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def normalize(payload: dict) -> dict:
    user = payload["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = [{"days": [{"date": d["date"], "count": d["contributionCount"],
                        "level": LEVELS.get(d["contributionLevel"], 0), "weekday": d["weekday"]}
                       for d in w["contributionDays"]]} for w in cal["weeks"]]
    repos = user["repositories"]
    langs: dict[str, int] = {}
    for r in repos["nodes"]:
        if r.get("primaryLanguage"):
            langs[r["primaryLanguage"]["name"]] = langs.get(r["primaryLanguage"]["name"], 0) + 1
    return {
        "contributions": {"total": cal["totalContributions"], "weeks": weeks},
        "public_repos": repos["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos["nodes"]),
        "followers": user["followers"]["totalCount"],
        "languages": dict(sorted(langs.items(), key=lambda kv: -kv[1])),
    }


def fetch(login: str, token: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-refresh"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if payload.get("errors") or not payload.get("data", {}).get("user"):
        raise RuntimeError(f"GraphQL error: {payload.get('errors')}")
    return normalize(payload)


def main() -> int:
    login = os.environ.get("PROFILE_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "akurapati1"
    token = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("no token; skipping fetch", file=sys.stderr)
        return 0
    try:
        data = fetch(login, token)
    except Exception as exc:  # noqa: BLE001 - never blank the profile on a transient failure
        print(f"fetch failed, keeping previous stats: {exc}", file=sys.stderr)
        return 0
    OUT.write_text(json.dumps(data, indent=1) + "\n")
    print(f"wrote {OUT} ({data['contributions']['total']} contributions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
