"""GitHub trending AI repos via REST search API."""
import os
import datetime as dt
import requests

API = "https://api.github.com/search/repositories"


def fetch_github(limit=10):
    since = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    query = f"topic:ai created:>={since}"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": limit}
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(API, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
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
