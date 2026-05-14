"""Walk the top 1,000 GitHub repositories by star count as a 3D world.

Requires a GITHUB_TOKEN env var (a personal access token; read-only public
scope is sufficient).
"""
import os
import sys
import time
from urllib.request import Request, urlopen
import json

from wander_around import Wander, Card


def fetch_top_repos(n: int = 1000) -> list[Card]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: set GITHUB_TOKEN environment variable", file=sys.stderr)
        sys.exit(1)
    cards: list[Card] = []
    page = 1
    while len(cards) < n:
        url = (f"https://api.github.com/search/repositories?"
                f"q=stars:>1000&sort=stars&order=desc&per_page=100&page={page}")
        req = Request(url, headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        })
        with urlopen(req) as resp:
            data = json.loads(resp.read())
        items = data.get("items", [])
        if not items:
            break
        for item in items:
            cards.append(Card(
                id=str(item["id"]),
                label=item["full_name"],
                category=item.get("language") or "Other",
                score=item["stargazers_count"] / 1000,
                link=item["html_url"],
            ))
            if len(cards) >= n:
                break
        page += 1
        time.sleep(2)  # be kind to the rate limit
    return cards


if __name__ == "__main__":
    print("fetching top 1,000 GitHub repos by stars...")
    cards = fetch_top_repos(1000)
    print(f"loaded {len(cards)} repos in "
          f"{len(set(c.category for c in cards))} languages")
    w = Wander(cards=cards, layout="ring",
                title="GitHub Top 1K (by stars)")
    print(f"\nopen http://localhost:8000/world")
    w.serve(host="127.0.0.1", port=8000)
