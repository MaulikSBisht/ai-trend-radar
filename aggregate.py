"""Run all source fetchers, tolerate individual failures."""
import matplotlib
matplotlib.use("Agg")  # headless backend, no display required
import matplotlib.pyplot as plt

from sources.github import fetch_github
from sources.hackernews import fetch_hackernews
from sources.reddit import fetch_reddit

# Palette matches the navy title page in report.py.
_NAVY = "#172A45"
_ACCENT = "#4A8FD6"
_LIGHT = "#D2DCEB"


def build_github_chart(repos, path="output/github_chart.png", top=8):
    """Render a horizontal bar chart of top GitHub repos by stars.

    Returns the image path, or None if there is nothing to plot.
    Styled to blend into the navy title page of the report.
    """
    if not repos:
        return None

    # Highest-starred at the top of the chart.
    top_repos = sorted(repos, key=lambda r: r["stars"], reverse=True)[:top]
    names = [r["name"].split("/")[-1] for r in reversed(top_repos)]
    stars = [r["stars"] for r in reversed(top_repos)]

    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=150)
    fig.patch.set_facecolor(_NAVY)
    ax.set_facecolor(_NAVY)

    bars = ax.barh(names, stars, color=_ACCENT, height=0.62)
    ax.set_title("Top GitHub Repositories by Stars", color="white",
                 fontsize=13, fontweight="bold", pad=12, loc="left")

    # Value labels at the end of each bar.
    for bar, value in zip(bars, stars):
        ax.text(bar.get_width() + max(stars) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{value:,}", va="center", ha="left",
                color=_LIGHT, fontsize=9)

    ax.tick_params(colors=_LIGHT, labelsize=9, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.margins(x=0.12)

    fig.tight_layout(pad=0.6)
    fig.savefig(path, facecolor=_NAVY, bbox_inches="tight")
    plt.close(fig)
    return path


def collect():
    data = {"github": [], "hackernews": [], "reddit": [], "errors": {}}

    for key, fn in (("github", fetch_github),
                    ("hackernews", fetch_hackernews),
                    ("reddit", fetch_reddit)):
        try:
            data[key] = fn()
        except Exception as e:
            data["errors"][key] = str(e)
            print(f"[warn] {key} failed: {e}")

    return data


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    d = collect()
    for k in ("github", "hackernews", "reddit"):
        print(f"{k}: {len(d[k])} items")
    if d["errors"]:
        print("errors:", d["errors"])
