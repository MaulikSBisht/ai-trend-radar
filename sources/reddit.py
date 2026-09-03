"""Reddit posts from AI subreddits via public RSS feeds (no API needed)."""
import re
import feedparser

FEEDS = {
    "LocalLLaMA": "https://www.reddit.com/r/LocalLLaMA/.rss",
    "MachineLearning": "https://www.reddit.com/r/MachineLearning/.rss",
}

# Reddit blocks the default urllib user agent; supply a browser-like one.
UA = "Mozilla/5.0 (compatible; ai-trend-radar/1.0)"

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _clean(html, limit=300):
    """Strip HTML tags/whitespace from an RSS description into plain text."""
    text = _TAG.sub(" ", html or "")
    text = _WS.sub(" ", text).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def fetch_reddit(limit=8):
    out = []
    for sub, url in FEEDS.items():
        feed = feedparser.parse(url, agent=UA)
        for entry in feed.entries[:limit]:
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
