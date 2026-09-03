"""AI Trend Radar - end-to-end pipeline: fetch -> PDF -> email."""
import sys
from dotenv import load_dotenv
from aggregate import collect
from report import build_pdf
from mailer import send_report


def run(send=True):
    load_dotenv()
    print("[1/3] Collecting trends...")
    data = collect()
    counts = {k: len(data[k]) for k in ("github", "hackernews", "reddit")}
    print("      ", counts)

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
