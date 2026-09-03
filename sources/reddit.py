"""Reddit posts from AI subreddits via public RSS feeds (no API needed)."""
import re
import time
import feedparser

FEEDS = {
    "LocalLLaMA": "https://www.reddit.com/r/LocalLLaMA/.rss",
    "MachineLearning": "https://www.reddit.com/r/MachineLearning/.rss",
}

# Reddit blocks the default urllib user agent outright, and throttles
# datacenter IPs (GitHub Actions runs on Azure ranges) harder than
# residential ones. A realistic browser UA measurably improves the odds.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

# Measured 2026-09-03: a throttled IP cleared in ~90s, so the backoff has to
# be generous to be worth anything. A weekly job can afford to wait.
# Reddit's public JSON endpoints (top.json, api.reddit.com) now return 403 to
# anonymous clients, so RSS is the only unauthenticated route left.
RETRIES = 4
BACKOFF = 20  # seconds, multiplied by attempt number -> 20s, 40s, 60s
PAUSE = 5     # seconds between feeds; back-to-back requests draw a 429

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _clean(html, limit=300):
    """Strip HTML tags/whitespace from an RSS description into plain text."""
    text = _TAG.sub(" ", html or "")
    text = _WS.sub(" ", text).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def _parse_feed(sub, url):
    """Fetch one feed, retrying on throttle/block.

    feedparser never raises on an HTTP error - it returns an empty feed with
    a status code. Left alone that turns a blocked Reddit into a silently
    empty report section, so translate it into a real exception that
    aggregate.collect() can record.
    """
    last = None
    for attempt in range(1, RETRIES + 1):
        feed = feedparser.parse(url, agent=UA)
        status = getattr(feed, "status", None)

        if feed.entries:
            return feed.entries

        last = f"r/{sub}: HTTP {status}, 0 entries"
        if attempt < RETRIES:
            print(f"[retry {attempt}/{RETRIES}] {last}")
            time.sleep(BACKOFF * attempt)

    raise RuntimeError(
        f"Reddit feed unavailable after {RETRIES} attempts ({last}). "
        "Datacenter IPs are frequently rate-limited or blocked by Reddit."
    )


def fetch_reddit(limit=8):
    out = []
    for i, (sub, url) in enumerate(FEEDS.items()):
        if i:
            time.sleep(PAUSE)  # be a polite anonymous client
        for entry in _parse_feed(sub, url)[:limit]:
            desc = _clean(entry.get("summary", ""))
            out.append({
                "sub": sub,
                "title": entry.get("title", "(untitled)"),
                "url": entry.get("link", ""),
                "desc": desc,
            })
    return out


if __name__ == "__main__":
    for p in fetch_reddit():
        print(f"[{p['sub']}] {p['title'][:70]}")
        print(f"   {p['url']}")
