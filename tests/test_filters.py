"""Regression tests locking in two Tier-1 bug fixes:

1. sources/hackernews.py::_is_ai - word-boundary regex replacing substring
   matching (which let "ai" inside "chair"/"email"/"Ukraine"/"campaign",
   "rag" inside "storage", and "ml" inside "yaml" false-positive), plus the
   "agentic" keyword that review found had been dropped.
2. main.py::strict_failures - must flag a source that silently returns 0
   items (no exception) in addition to one that raised, without treating a
   single failing source as two reasons.

These import and call the real functions - no logic is duplicated here.
No network calls are made anywhere in this file.
"""
import pytest

from sources.hackernews import _is_ai, fetch_hackernews, _FAILED
import sources.hackernews as hackernews
import main


# ---------------------------------------------------------------------------
# _is_ai
# ---------------------------------------------------------------------------

# (title, expected) - false positives the old substring match produced,
# plurals and the "agentic" keyword the word-boundary regex must still
# catch, ordinary positives, and the None/empty edge cases.
IS_AI_CASES = [
    # Old substring bugs -> must now be False.
    ("Show HN: I built a comfy chair", False),          # "ai" inside chair
    ("How we cut email latency in half", False),        # "ai" inside email
    ("Ukraine war logistics update", False),            # "ai" inside Ukraine
    ("A campaign against dark patterns", False),        # "ai" inside campaign
    ("The fragile state of storage hardware", False),   # "rag" inside storage
    ("YAML parsing is harder than it looks", False),    # "ml" inside yaml

    # Plurals must still match via the optional trailing "s".
    ("Why LLMs still hallucinate", True),
    ("Building agents that actually work", True),

    # "agentic" was dropped and re-added after review.
    ("Agentic workflows for developers", True),

    # Ordinary positives.
    ("Anthropic ships Claude Opus 5", True),
    ("GPT-4 architecture leaked", True),
    ("An AI-powered code reviewer", True),

    # Common joined forms the old "s?" suffix regex missed (no word boundary
    # between a bare "ai"/"gpt" and letters glued onto it, e.g. "ChatGPT",
    # "GenAI") - fixed by adding explicit keywords.
    ("ChatGPT is down", True),
    ("GenAI hype", True),
    ("LLMOps at scale", True),
    ("Mistral7B fine-tune", True),
    ("MLOps is dead", True),

    # Version-suffixed product names the old "s?" suffix regex missed (no
    # word boundary between the name and a following digit run) - fixed by
    # replacing the suffix with "(?:s|\\d[\\w.]*)?".
    ("Llama3 released", True),
    ("GPT4 benchmarks", True),
    ("Gemini2.5 Pro", True),

    # Edge cases.
    (None, False),
    ("", False),
]


@pytest.mark.parametrize("title, expected", IS_AI_CASES)
def test_is_ai(title, expected):
    assert _is_ai(title) is expected


# ---------------------------------------------------------------------------
# main.strict_failures
# ---------------------------------------------------------------------------

def _data(github=None, hackernews_=None, reddit=None, errors=None):
    return {
        "github": github or [],
        "hackernews": hackernews_ or [],
        "reddit": reddit or [],
        "errors": errors or {},
    }


def _counts(data):
    return {k: len(data[k]) for k in main.SOURCES}


def test_strict_failures_all_healthy_no_reasons():
    data = _data(github=["r1"], hackernews_=["s1"], reddit=["p1"])
    assert main.strict_failures(data, _counts(data)) == []


def test_strict_failures_errored_source_gives_exactly_one_reason():
    # github both raised AND would be below its minimum (0 < 1) - must
    # produce one reason (the error), not two.
    data = _data(hackernews_=["s1"], reddit=["p1"],
                 errors={"github": "boom"})
    reasons = main.strict_failures(data, _counts(data))
    assert len(reasons) == 1
    assert "github raised: boom" in reasons[0]


def test_strict_failures_github_silently_empty_fails():
    data = _data(github=[], hackernews_=["s1"], reddit=["p1"])
    reasons = main.strict_failures(data, _counts(data))
    assert len(reasons) == 1
    assert "github returned 0 items" in reasons[0]


def test_strict_failures_reddit_silently_empty_fails():
    data = _data(github=["r1"], hackernews_=["s1"], reddit=[])
    reasons = main.strict_failures(data, _counts(data))
    assert len(reasons) == 1
    assert "reddit returned 0 items" in reasons[0]


def test_strict_failures_hackernews_empty_no_error_passes():
    data = _data(github=["r1"], hackernews_=[], reddit=["p1"])
    assert main.strict_failures(data, _counts(data)) == []


# ---------------------------------------------------------------------------
# fetch_hackernews - outage guard (more-than-half failed item fetches)
# ---------------------------------------------------------------------------

def _patch_fetch(monkeypatch, ids, failing_ids):
    monkeypatch.setattr(hackernews, "_fetch_top", lambda scan: list(ids))

    def fake_get_item(sid):
        if sid in failing_ids:
            return _FAILED
        # A legitimate but uninteresting item: not a story, so it is
        # skipped without needing to satisfy _is_ai.
        return {"type": "comment"}

    monkeypatch.setattr(hackernews, "_get_item", fake_get_item)


def test_fetch_hackernews_raises_when_more_than_half_fail(monkeypatch):
    ids = [1, 2, 3, 4]
    _patch_fetch(monkeypatch, ids, failing_ids={1, 2, 3})  # 3/4 failed
    with pytest.raises(RuntimeError):
        fetch_hackernews(scan=4)


def test_fetch_hackernews_does_not_raise_at_exactly_half(monkeypatch):
    ids = [1, 2, 3, 4]
    _patch_fetch(monkeypatch, ids, failing_ids={1, 2})  # 2/4 failed
    assert fetch_hackernews(scan=4) == []
