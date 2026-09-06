"""Shared retry helper for source fetchers."""
import time


def retry(fn, *, attempts=3, backoff=5, label="request"):
    """Call fn(), retrying on exception with linear backoff. Re-raises the last."""
    last = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:
            last = e
            if attempt < attempts:
                print(f"[retry {attempt}/{attempts}] {label}: {e}")
                time.sleep(backoff * attempt)
    raise last
