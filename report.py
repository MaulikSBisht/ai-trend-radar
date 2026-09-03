"""Generate PDF report from aggregated trend data."""
import datetime as dt
from fpdf import FPDF

NAVY = (23, 42, 69)
ACCENT = (38, 110, 195)
GREY = (110, 110, 110)
LIGHT = (240, 244, 248)


def _san(text):
    """Drop chars outside latin-1 (fpdf core fonts can't render them)."""
    return (text or "").encode("latin-1", "replace").decode("latin-1")


def _wrap_tokens(text, n=70):
    """Hard-break any token longer than n chars so multi_cell can wrap it."""
    out = []
    for tok in (text or "").split(" "):
        while len(tok) > n:
            out.append(tok[:n])
            tok = tok[n:]
        out.append(tok)
    return " ".join(out)


def _url(pdf, text):
    """Render a URL line safely at left margin with hard token wrapping."""
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, _san(_wrap_tokens(text)))


class Report(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, "AI Trend Radar", align="L")
        self.cell(0, 8, dt.date.today().isoformat(), align="R")
        self.ln(10)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _title_page(pdf, data, chart_path=None):
    pdf.add_page()
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_y(55)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 34)
    pdf.cell(0, 16, "AI TREND RADAR", align="C")
    pdf.ln(18)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(150, 190, 230)
    pdf.cell(0, 10, "Autonomous Weekly Intelligence Report", align="C")
    pdf.ln(14)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(210, 220, 235)
    pdf.cell(0, 8, dt.date.today().strftime("%B %d, %Y"), align="C")
    pdf.ln(8)
    total = len(data["github"]) + len(data["hackernews"]) + len(data["reddit"])
    pdf.cell(0, 8, f"{total} trends across 3 sources", align="C")

    # Chart sits below the header block on the title page.
    if chart_path:
        chart_w = 170
        pdf.image(chart_path, x=(210 - chart_w) / 2, y=140, w=chart_w)


def _section_head(pdf, title, subtitle):
    pdf.ln(2)
    pdf.set_fill_color(*LIGHT)
    pdf.set_text_color(*NAVY)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, _san(f"  {title}"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 6, _san(f"  {subtitle}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _summary(pdf, data):
    pdf.add_page()
    pdf.set_text_color(*NAVY)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(50, 50, 50)
    rows = [
        ("GitHub", f"{len(data['github'])} new AI repos (last 7 days, top-starred)"),
        ("Hacker News", f"{len(data['hackernews'])} AI/LLM front-page stories"),
        ("Reddit", f"{len(data['reddit'])} top posts (r/LocalLLaMA, r/MachineLearning)"),
    ]
    for label, desc in rows:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*ACCENT)
        pdf.cell(35, 8, _san(label))
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 8, _san(desc), new_x="LMARGIN", new_y="NEXT")
    if data["errors"]:
        pdf.ln(4)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(180, 60, 60)
        for k, v in data["errors"].items():
            pdf.multi_cell(0, 5, _san(f"Note: {k} source unavailable - {v}"))


def _github_section(pdf, repos):
    if not repos:
        return
    pdf.add_page()
    _section_head(pdf, "GitHub: Rising AI Repositories",
                  "Top-starred repos created in the last 7 days, topic:ai")
    for r in repos:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*ACCENT)
        pdf.multi_cell(0, 6, _san(f"* {r['name']}  ({r['stars']} stars, {r['lang']})"),
                       new_x="LMARGIN", new_y="NEXT")
        if r["desc"]:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 5, _san(r["desc"]))
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*GREY)
        _url(pdf, r["url"])
        pdf.ln(2)


def _hn_section(pdf, stories):
    if not stories:
        return
    pdf.add_page()
    _section_head(pdf, "Hacker News: AI Discussions",
                  "Front-page stories filtered for AI/LLM/agent keywords")
    for s in stories:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*NAVY)
        pdf.multi_cell(0, 6, _san(f"* {s['title']}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*ACCENT)
        pdf.cell(0, 5, _san(f"  {s['score']} points | {s['comments']} comments"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*GREY)
        _url(pdf, f"  {s['url']}")
        pdf.ln(2)


def _reddit_section(pdf, posts):
    if not posts:
        return
    pdf.add_page()
    _section_head(pdf, "Reddit: Community Pulse",
                  "Top daily posts from r/LocalLLaMA and r/MachineLearning")
    for p in posts:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*NAVY)
        pdf.multi_cell(0, 6, _san(f"* [{p['sub']}] {p['title']}"),
                       new_x="LMARGIN", new_y="NEXT")
        if p.get("desc"):
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 5, _san(p["desc"]))
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*GREY)
        _url(pdf, f"  {p['url']}")
        pdf.ln(2)


def build_pdf(data, path="output/ai_trend_radar.pdf"):
    import os
    from aggregate import build_github_chart
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Generate the chart before building, then clean up the temp image after.
    chart_path = build_github_chart(data["github"])
    try:
        pdf = Report()
        pdf.set_auto_page_break(auto=True, margin=18)
        _title_page(pdf, data, chart_path)
        _summary(pdf, data)
        _github_section(pdf, data["github"])
        _hn_section(pdf, data["hackernews"])
        _reddit_section(pdf, data["reddit"])
        pdf.output(path)
    finally:
        if chart_path and os.path.exists(chart_path):
            os.remove(chart_path)
    return path


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    from aggregate import collect
    out = build_pdf(collect())
    print("PDF written:", out)
