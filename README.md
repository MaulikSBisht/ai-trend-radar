# AI Trend Radar

An autonomous weekly intelligence report on the AI landscape. It pulls trending
activity from three sources, renders a designed PDF, and emails it to you.

Runs itself every Monday on GitHub Actions. No server, no babysitting.

## What it collects

| Source | What | How |
| --- | --- | --- |
| **GitHub** | Top-starred repos created in the last 7 days, `topic:ai` | REST Search API |
| **Hacker News** | Front-page stories filtered for AI/LLM/agent keywords | Firebase API |
| **Reddit** | Top posts from r/LocalLLaMA and r/MachineLearning | Public RSS feeds |

Output is a multi-page PDF: a navy title page with a bar chart of the top repos
by stars, an executive summary, then a detailed section per source with links.
It's emailed as an attachment with an HTML summary in the body.

## Local setup

```bash
pip install -r requirements.txt
cp .env.example .env     # then fill in the values
```

### Required configuration

Three values in `.env`:

| Variable | Required | Notes |
| --- | --- | --- |
| `RESEND_API_KEY` | yes | From <https://resend.com/api-keys> |
| `SENDER_EMAIL` | yes | Must be on a **Resend-verified domain** |
| `RECIPIENT_EMAIL` | yes | Where the report is delivered |
| `GITHUB_TOKEN` | no | Raises the Search API rate limit. See the note below. |
| `STRICT_SOURCES` | no | Leave unset locally. See [Failure handling](#failure-handling). |

`.env` is gitignored and must never be committed.

## Running it

```bash
python main.py --no-send   # fetch + build the PDF, skip the email
python main.py             # full pipeline, sends the email
```

The PDF lands at `output/ai_trend_radar.pdf`. The `output/` directory is
gitignored and created at runtime, so a fresh checkout works.

Individual sources can be run standalone for debugging:

```bash
python sources/github.py
python sources/hackernews.py
python sources/reddit.py
python aggregate.py          # fetch all three, print counts
```

## Deployment (GitHub Actions)

The workflow is [`.github/workflows/run_radar.yml`](.github/workflows/run_radar.yml).

### Repository secrets

Add three secrets under **Settings → Secrets and variables → Actions**:

- `RESEND_API_KEY`
- `SENDER_EMAIL`
- `RECIPIENT_EMAIL`

**Do not add `GITHUB_TOKEN`.** The name is reserved and GitHub will reject it.
Actions provides that token automatically, and the workflow already maps it into
the environment, so `sources/github.py` picks it up with no code change and gets
the authenticated rate limit.

### Schedule

Every Monday at 08:00 UTC:

```yaml
schedule:
  - cron: "0 8 * * 1"
```

A run takes roughly two minutes, so a weekly cadence sits far inside the 2,000
free monthly Actions minutes on a private repo.

### Manual run

**Actions → AI Trend Radar → Run workflow.** Use this rather than waiting for
Monday to find out whether a change works.

Every run uploads the PDF as a build artifact (`ai-trend-radar-report`),
downloadable from the run summary page.

### After any deployment change, verify the contents

A green run is *not* sufficient evidence of success — see below. Download the
run's artifact PDF and confirm **all three source sections contain real
entries**. An empty section is a failed deployment, not a blemish.

## Failure handling

`aggregate.collect()` wraps each source in try/except and the report renders a
"source unavailable" note rather than crashing. Locally that's a feature: one
flaky API shouldn't cost you the whole report.

In CI it's a liability, because a broken source produces a **green run and a
delivered email** — the report quietly ships missing a third of its content, and
nothing ever alerts you.

So the workflow sets `STRICT_SOURCES=1`, which makes `main.py` exit non-zero
before building or sending anything if any source failed **or returned zero
items**. That turns a dead source into a failed workflow run, which GitHub
emails you about. Local runs leave it unset and keep the forgiving behaviour.

Both conditions matter. A source that throws lands in `data["errors"]`, but a
source that is merely blocked can return an empty list without raising at all —
checking only for exceptions would wave that case straight through.

### The Reddit caveat

Reddit throttles datacenter IPs harder than residential ones, and GitHub Actions
runs on Azure ranges. `sources/reddit.py` therefore sends a realistic browser
User-Agent, paces requests between feeds, and retries with backoff (20s, 40s,
60s) before giving up. A throttled IP was measured clearing in about 90 seconds,
which is what those numbers are sized for.

Reddit's public JSON endpoints (`top.json`, `api.reddit.com`) now return **403**
to anonymous clients, so RSS is the only unauthenticated route left. If RSS is
ever blocked outright from CI, the options are to authenticate, or to
consciously drop to two sources and update the report and this README to match.
Thanks to `STRICT_SOURCES` this will surface as a failed run rather than a
silently short report.

## Python version

CI pins **3.12**, which has prebuilt wheels for `matplotlib` and `fpdf2`. Local
development is on **3.14**; nothing in the code is version-specific, and the pin
exists purely to avoid a source build on a runner.

## Known limitation: the 60-day schedule pause

**GitHub disables scheduled workflows after 60 days of repository inactivity.**

On a private repo that gets pushed once and then left alone, the cron fires for
about two months and then stops. This produces **no failure email**, because
nothing failed — the schedule is simply no longer registered. The signal you'll
notice is a Monday with no report.

This is accepted rather than worked around. The usual trick (a second workflow
that periodically commits a timestamp to reset the clock) is a moving target
GitHub has tightened before, and a missing weekly email is a noticeable enough
signal on its own.

**To re-enable:** go to **Actions → AI Trend Radar**, and click the button in
the banner to re-enable the workflow. Any push to the repo also resets the
60-day clock.

## Design notes

Two deliberate deviations from the original spec, both intentional:

- **Resend API instead of `smtplib`.** No app passwords, no SMTP/TLS handling,
  and deliverability is somebody else's problem.
- **Reddit public RSS instead of PRAW.** No OAuth app registration, no client
  credentials to rotate, two fewer secrets to manage.

In `report.py`, `_san()` strips characters outside latin-1 (the fpdf core fonts
can't render them) and `_wrap_tokens()` hard-breaks long tokens so `multi_cell`
can wrap URLs. Both exist because real-world data broke the report without them.
