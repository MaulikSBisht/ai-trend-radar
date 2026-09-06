"""GitHub trending AI repos via REST search API."""
import os
import datetime as dt
import requests

from sources._retry import retry

API = "https://api.github.com/search/repositories"

# Transient 5xx / secondary rate limit errors clear quickly; a weekly job can
# afford a few seconds of backoff to avoid losing the whole section to a blip.
RETRIES = 3
BACKOFF = 5  # seconds, multiplied by attempt number -> 5s, 10s


def _fetch(params, headers):
    r = requests.get(API, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json().get("items", [])


def fetch_github(limit=10):
    since = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    query = f"topic:ai created:>={since}"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": limit}
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    items = retry(lambda: _fetch(params, headers),
                  attempts=RETRIES, backoff=BACKOFF, label="github search")
    out = []
    for it in items:
        out.append({
            "name": it["full_name"],
            "url": it["html_url"],
            "stars": it["stargazers_count"],
            "desc": (it.get("description") or "").strip(),
            "lang": it.get("language") or "—",
        })
    return out


if __name__ == "__main__":
    for repo in fetch_github(5):
        print(f"{repo['stars']:>5}  {repo['name']}  ({repo['lang']})")
        print(f"        {repo['desc'][:80]}")
