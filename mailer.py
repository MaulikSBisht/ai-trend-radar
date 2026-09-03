"""Send the PDF report via the Resend API with a styled HTML body."""
import os
import datetime as dt
import resend

# Palette mirrors the PDF report (report.py).
NAVY = "#172A45"
ACCENT = "#266EC3"
INK = "#2D3340"
MUTED = "#6E6E6E"
BG = "#EEF2F7"
CARD = "#FFFFFF"
LINE = "#E3E9F1"


def _stat_cell(label, value):
    """One source stat as a table cell: big number over a small label."""
    return f"""
              <td align="center" style="padding:14px 8px;">
                <div style="font-family:Helvetica,Arial,sans-serif;font-size:30px;font-weight:700;line-height:1;color:{ACCENT};">{value}</div>
                <div style="font-family:Helvetica,Arial,sans-serif;font-size:11px;letter-spacing:0.6px;text-transform:uppercase;color:{MUTED};padding-top:6px;">{label}</div>
              </td>"""


def _build_html(counts, today, pretty_date):
    total = sum(counts.values()) if counts else 0
    stats = (
        _stat_cell("GitHub", counts.get("github", 0))
        + _stat_cell("Hacker News", counts.get("hackernews", 0))
        + _stat_cell("Reddit", counts.get("reddit", 0))
    ) if counts else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Trend Radar</title>
</head>
<body style="margin:0;padding:0;background-color:{BG};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{BG};">
    <tr>
      <td align="center" style="padding:32px 16px;">

        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:600px;background-color:{CARD};border-radius:12px;overflow:hidden;border:1px solid {LINE};">

          <!-- Header -->
          <tr>
            <td style="background-color:{NAVY};padding:36px 40px;">
              <div style="font-family:Helvetica,Arial,sans-serif;font-size:13px;letter-spacing:3px;text-transform:uppercase;color:#7FA8D6;">Autonomous Intelligence Report</div>
              <div style="font-family:Helvetica,Arial,sans-serif;font-size:30px;font-weight:700;letter-spacing:0.5px;color:#FFFFFF;padding-top:8px;">AI Trend Radar</div>
              <div style="font-family:Helvetica,Arial,sans-serif;font-size:14px;color:#B9CBE3;padding-top:6px;">{pretty_date}</div>
            </td>
          </tr>

          <!-- Intro -->
          <tr>
            <td style="padding:34px 40px 8px 40px;">
              <p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:1.6;color:{INK};">
                Here's your latest scan of the AI landscape. We tracked
                <strong style="color:{NAVY};">{total} trends</strong> across three sources today.
              </p>
            </td>
          </tr>

          <!-- Stats -->
          <tr>
            <td style="padding:18px 32px 8px 32px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{BG};border-radius:10px;">
                <tr>{stats}
                </tr>
              </table>
            </td>
          </tr>

          <!-- Call to action -->
          <tr>
            <td style="padding:20px 40px 8px 40px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-left:4px solid {ACCENT};background-color:#F4F8FD;border-radius:0 8px 8px 0;">
                <tr>
                  <td style="padding:18px 22px;">
                    <div style="font-family:Helvetica,Arial,sans-serif;font-size:14px;font-weight:700;color:{NAVY};">Your full breakdown is attached</div>
                    <div style="font-family:Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;color:{INK};padding-top:4px;">
                      Open the attached PDF for the complete report &mdash; rising repositories, front-page discussions, and the community pulse, with links to every source.
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:28px 40px 36px 40px;">
              <div style="border-top:1px solid {LINE};padding-top:18px;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.6;color:{MUTED};">
                Generated automatically by <strong style="color:{INK};">AI Trend Radar</strong> on {today}.<br>
                Sources: GitHub &middot; Hacker News &middot; Reddit (r/LocalLLaMA, r/MachineLearning)
              </div>
            </td>
          </tr>

        </table>

        <div style="font-family:Helvetica,Arial,sans-serif;font-size:11px;color:#9AA7B8;padding-top:18px;">AI Trend Radar &middot; Autonomous Weekly Intelligence</div>

      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_text(summary_line, today):
    return (
        f"Your autonomous AI Trend Radar report for {today} is attached.\n\n"
        f"{summary_line}\n\n"
        "Open the attached PDF for the full breakdown.\n\n-- AI Trend Radar"
    )


def send_report(pdf_path, summary_line="", counts=None):
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")
    recipient = os.getenv("RECIPIENT_EMAIL")

    if not all([api_key, sender, recipient]):
        raise RuntimeError("Email config incomplete in .env (need RESEND_API_KEY, SENDER_EMAIL, RECIPIENT_EMAIL)")

    resend.api_key = api_key

    today = dt.date.today().isoformat()
    pretty_date = dt.date.today().strftime("%B %d, %Y")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    params = {
        "from": sender,
        "to": [recipient],
        "subject": f"AI Trend Radar - {today}",
        "html": _build_html(counts, today, pretty_date),
        # Plain-text fallback for clients that don't render HTML.
        "text": _build_text(summary_line, today),
        "attachments": [{
            "filename": os.path.basename(pdf_path),
            "content": list(pdf_bytes),
        }],
    }

    resend.Emails.send(params)
    return recipient


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    demo = {"github": 10, "hackernews": 10, "reddit": 8}
    to = send_report("output/ai_trend_radar.pdf", "Test send.", counts=demo)
    print("Sent to", to)
