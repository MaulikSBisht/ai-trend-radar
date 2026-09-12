"""Tests for sources/_retry.py::retry - the shared backoff helper used by
GitHub, Hacker News, and (wrapped with its own re-raise) Reddit.

No real sleeping and no network: time.sleep is monkeypatched in the
_retry module namespace.
"""
import pytest

import sources._retry as _retry
from sources._retry import retry


def test_retry_returns_result_after_transient_failures(monkeypatch):
    monkeypatch.setattr(_retry.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError(f"transient failure {calls['n']}")
        return "ok"

    assert retry(flaky, attempts=5, backoff=1) == "ok"
    assert calls["n"] == 3


def test_retry_reraises_the_last_exception(monkeypatch):
    monkeypatch.setattr(_retry.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise ValueError(f"attempt {calls['n']}")

    with pytest.raises(ValueError, match="attempt 3"):
        retry(always_fails, attempts=3, backoff=1)
    assert calls["n"] == 3  # exhausted all attempts, not just the first


def test_retry_does_not_sleep_after_the_final_attempt(monkeypatch):
    sleeps = []
    monkeypatch.setattr(_retry.time, "sleep", lambda s: sleeps.append(s))

    def always_fails():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        retry(always_fails, attempts=3, backoff=1)

    # 3 attempts -> a sleep after attempt 1 and after attempt 2, but never
    # after the 3rd (final) attempt.
    assert len(sleeps) == 2


def test_retry_rejects_attempts_below_one():
    with pytest.raises(ValueError):
        retry(lambda: "unreachable", attempts=0)
