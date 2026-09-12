"""AI Trend Radar - end-to-end pipeline: fetch -> PDF -> email."""
import os
import sys
from dotenv import load_dotenv
from aggregate import collect
from report import build_pdf
from mailer import send_report

SOURCES = ("github", "hackernews", "reddit")

# Per-source floor for STRICT_SOURCES. Hacker News is allowed to hit 0: the
# keyword filter (see sources/hackernews.py) can legitimately find no AI
# stories on a quiet news day, and fetch_hackernews's own failed-fetch guard
# is what distinguishes that from the Firebase item API being down.
MIN_ITEMS = {"github": 1, "hackernews": 0, "reddit": 1}


def strict_failures(data, counts):
    """Reasons this run should be treated as failed under STRICT_SOURCES.

    There are two distinct failure shapes, and the second is the one that
    bites in CI: a source that throws lands in data["errors"], but a source
    that is merely blocked or throttled can return an empty list without
    raising anything at all. Checking only data["errors"] would wave that
    through as a green run with a third of the report missing.
    """
    reasons = [f"{k} raised: {v}" for k, v in data["errors"].items()]
    reasons += [f"{k} returned {counts[k]} items (minimum {MIN_ITEMS[k]})"
                for k in SOURCES
                if k not in data["errors"] and counts[k] < MIN_ITEMS[k]]
    return reasons


def run(send=True):
    load_dotenv()
    strict = bool(os.getenv("STRICT_SOURCES"))

    print("[1/3] Collecting trends...")
    data = collect()
    counts = {k: len(data[k]) for k in SOURCES}
    print("      ", counts)

    # Locally this stays forgiving: a dead source degrades the report but
    # still delivers it. In CI STRICT_SOURCES turns that into a hard failure,
    # which is what makes GitHub's workflow-failure email actually fire.
    if strict:
        reasons = strict_failures(data, counts)
        if reasons:
            print("\nSTRICT_SOURCES set: refusing to ship an incomplete report.")
            for r in reasons:
                print(f"  - {r}")
            sys.exit(1)

    print("[2/3] Building PDF...")
    pdf = build_pdf(data)
    print("       wrote", pdf)

    if not send:
        print("[3/3] Skipped email (--no-send)")
        return

    print("[3/3] Emailing report...")
    summary = (f"GitHub: {counts['github']} repos | "
               f"HN: {counts['hackernews']} stories | "
               f"Reddit: {counts['reddit']} posts")
    to = send_report(pdf, summary, counts=counts)
    print("       sent to", to)


if __name__ == "__main__":
    run(send="--no-send" not in sys.argv)
