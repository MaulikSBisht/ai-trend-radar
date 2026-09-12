"""Regression tests for the HN outage guard missing HTTP error responses
(Task 4 / review finding F3).

Firebase returns non-2xx responses with a JSON body on some errors (e.g.
{"error": "Permission denied"}). Before this fix, _get_item and _fetch_top
only treated a raised exception as a failed fetch - a non-2xx response
that still parses as JSON slipped through as a "successful" item with no
"type", got silently skipped, and let fetch_hackernews return 0 results
without ever tripping the outage guard. raise_for_status() closes that gap
by turning any non-2xx response into an exception before it reaches .json().

These monkeypatch requests.get in the hackernews module namespace with a
fake response object - no network calls are made.
"""
import pytest
import requests

import sources.hackernews as hackernews
from sources.hackernews import _get_item, _FAILED, fetch_hackernews


class _FakeResponse:
    """Stand-in for requests.Response. A non-2xx status still has a JSON
    body (mirroring Firebase's error shape), but raise_for_status() must
    raise before that body is ever parsed."""

    def __init__(self, status_code=200, json_body=None):
        self.status_code = status_code
        self._json_body = json_body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self):
        return self._json_body


def test_get_item_http_error_response_is_treated_as_failed(monkeypatch):
    # Non-2xx status, but a parseable JSON error body - exactly the shape
    # that slipped through before raise_for_status() was added.
    monkeypatch.setattr(
        hackernews.requests, "get",
        lambda *a, **k: _FakeResponse(403, {"error": "Permission denied"}))
    assert _get_item(1) is _FAILED


def test_get_item_ok_response_is_returned_normally(monkeypatch):
    item = {"id": 1, "type": "story", "title": "An AI story"}
    monkeypatch.setattr(hackernews.requests, "get",
                         lambda *a, **k: _FakeResponse(200, item))
    assert _get_item(1) == item


def test_fetch_hackernews_raises_when_majority_of_items_are_http_errors(monkeypatch):
    ids = [1, 2, 3, 4]
    monkeypatch.setattr(hackernews, "_fetch_top", lambda scan: list(ids))

    def fake_get(url, timeout=None):
        sid = int(url.rsplit("/", 1)[-1].split(".")[0])
        if sid in (1, 2, 3):  # 3/4 item fetches come back as HTTP errors
            return _FakeResponse(500, {"error": "internal"})
        return _FakeResponse(200, {"id": sid, "type": "comment"})

    monkeypatch.setattr(hackernews.requests, "get", fake_get)

    with pytest.raises(RuntimeError):
        fetch_hackernews(scan=4)


def test_fetch_top_http_error_raises(monkeypatch):
    monkeypatch.setattr(hackernews.requests, "get",
                         lambda *a, **k: _FakeResponse(503, None))
    with pytest.raises(requests.HTTPError):
        hackernews._fetch_top(10)
