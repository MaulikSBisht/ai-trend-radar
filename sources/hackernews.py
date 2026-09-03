"""Hacker News top stories filtered for AI keywords."""
import requests
from concurrent.futures import ThreadPoolExecutor

TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"

KEYWORDS = ["ai", "llm", "gpt", "agent", "openai", "anthropic", "claude",
            "gemini", "model", "neural", "machine learning", "ml ",
            "transformer", "diffusion", "rag", "mistral", "llama"]


def _get_item(sid):
    try:
        return requests.get(ITEM.format(sid), timeout=15).json()
    except Exception:
        return None


def _is_ai(title):
    t = (title or "").lower()
    return any(k in t for k in KEYWORDS)


def fetch_hackernews(scan=120, limit=10):
    ids = requests.get(TOP, timeout=30).json()[:scan]
    with ThreadPoolExecutor(max_workers=20) as ex:
        items = list(ex.map(_get_item, ids))
    out = []
    for it in items:
        if not it or it.get("type") != "story":
            continue
        if not _is_ai(it.get("title")):
            continue
        out.append({
            "title": it.get("title"),
            "url": it.get("url") or f"https://news.ycombinator.com/item?id={it['id']}",
            "score": it.get("score", 0),
            "comments": it.get("descendants", 0),
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:limit]


if __name__ == "__main__":
    for s in fetch_hackernews():
        print(f"{s['score']:>4} pts  {s['title']}")
