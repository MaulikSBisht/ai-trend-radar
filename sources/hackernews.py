"""Hacker News top stories filtered for AI keywords."""
import re
import requests
from concurrent.futures import ThreadPoolExecutor

from sources._retry import retry

TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"

# Transient Firebase blips on the topstories call are worth a couple of
# quick retries rather than losing the whole section.
RETRIES = 3
BACKOFF = 5  # seconds, multiplied by attempt number -> 5s, 10s

KEYWORDS = ["ai", "llm", "gpt", "agent", "agentic", "openai", "anthropic", "claude",
            "gemini", "model", "neural", "machine learning", "ml",
            "transformer", "diffusion", "rag", "mistral", "llama"]

# Word-boundary match with an optional trailing "s" so plurals ("LLMs",
# "agents", "models") still hit. Bare substring matching let "ai"/"rag"/"ml"
# fire inside ordinary words (e.g. "chair", "storage", "yaml").
_AI_RE = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in KEYWORDS) + r")s?\b",
                    re.IGNORECASE)


class _FetchFailed:
    """Sentinel: the per-item request itself errored, as opposed to a
    legitimate null/missing item the API can also return."""


_FAILED = _FetchFailed()


def _get_item(sid):
    try:
        return requests.get(ITEM.format(sid), timeout=15).json()
    except Exception:
        return _FAILED


def _is_ai(title):
    return bool(_AI_RE.search(title or ""))


def _fetch_top(scan):
    return requests.get(TOP, timeout=30).json()[:scan]


def fetch_hackernews(scan=120, limit=10):
    ids = retry(lambda: _fetch_top(scan),
                attempts=RETRIES, backoff=BACKOFF, label="hn topstories")
    with ThreadPoolExecutor(max_workers=20) as ex:
        items = list(ex.map(_get_item, ids))

    # A quiet news day (0 AI-tagged stories) is a legitimate outcome for this
    # source under STRICT_SOURCES (see main.MIN_ITEMS), which makes it
    # important to distinguish from the Firebase item API being broken: that
    # would also silently yield 0 stories, since _get_item swallows per-item
    # exceptions. If most of the scanned items failed to fetch, treat it as
    # an outage rather than a quiet day.
    failed = sum(1 for it in items if it is _FAILED)
    if ids and failed > len(ids) / 2:
        raise RuntimeError(
            f"hackernews: {failed}/{len(ids)} item fetches failed")

    out = []
    for it in items:
        if it is _FAILED or not it or it.get("type") != "story":
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
