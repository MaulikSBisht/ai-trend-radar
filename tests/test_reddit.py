"""Tests for sources/reddit.py:

1. An empty RSS feed (Reddit silently blocking/throttling an anonymous
   client) must, after retries are exhausted, raise with the original
   "Datacenter IPs are frequently rate-limited or blocked by Reddit." hint
   restored onto the final exception (review finding F10), with the
   underlying per-subreddit exception still chained via `from e`.
2. A normal feed still produces posts.

No network calls: feedparser.parse and both time.sleep call sites (the
module's own inter-feed pause and _retry's backoff sleep) are monkeypatched.
"""
import pytest

import sources._retry as _retry
import sources.reddit as reddit


class _EmptyFeed:
    entries = []
    status = 429


class _OkFeed:
    entries = [{
        "title": "A post",
        "link": "https://reddit.com/r/LocalLLaMA/x",
        "summary": "<p>hi</p>",
    }]
    status = 200


def test_fetch_reddit_raises_with_datacenter_hint_on_empty_feed(monkeypatch):
    monkeypatch.setattr(reddit.time, "sleep", lambda s: None)
    monkeypatch.setattr(_retry.time, "sleep", lambda s: None)
    monkeypatch.setattr(reddit.feedparser, "parse", lambda url, agent=None: _EmptyFeed())

    with pytest.raises(RuntimeError) as exc_info:
        reddit.fetch_reddit()

    message = str(exc_info.value)
    assert "Datacenter IPs are frequently rate-limited or blocked by Reddit." in message
    assert "HTTP 429" in message  # original _fetch_one detail preserved
    assert exc_info.value.__cause__ is not None  # original exception chained


def test_fetch_reddit_returns_posts_on_a_healthy_feed(monkeypatch):
    monkeypatch.setattr(reddit.time, "sleep", lambda s: None)
    monkeypatch.setattr(_retry.time, "sleep", lambda s: None)
    monkeypatch.setattr(reddit.feedparser, "parse", lambda url, agent=None: _OkFeed())

    posts = reddit.fetch_reddit(limit=8)

    assert len(posts) == 2  # one post per subreddit in FEEDS
    assert posts[0]["title"] == "A post"
    assert posts[0]["desc"] == "hi"
