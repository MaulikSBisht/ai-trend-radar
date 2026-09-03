# AI Trend Radar — Deploy to GitHub Actions

**Date:** 2026-09-03
**Status:** Approved, ready for implementation planning
**Scope:** Get the existing pipeline running unattended on a weekly schedule.

---

## 1. Goal

The pipeline is built and works locally. It has never run in CI, because the
project directory is not a git repository. This spec covers everything needed
to take it from "runs when I run it" to "runs every Monday without me."

### Definition of done

All five must hold:

1. A `workflow_dispatch` run completes green.
2. The email arrives in the real inbox with the PDF attached.
3. **The PDF contains real content in all three source sections** — GitHub,
   Hacker News, and Reddit. Not just "the run succeeded."
4. `.env` is absent from git history.
5. `.env.example` and `README.md` accurately describe the current design.

### Explicitly out of scope

LLM/NLP categorization, a test suite, deduplication or run history, and Reddit
engagement-metric enrichment. These remain on the backlog. Adding any of them
during this work is scope creep — the goal is deployment, not features.

---

## 2. Context a fresh session needs

- Full project background: `PROJECT_OVERVIEW.md` in the repo root.
- Deliberate deviations from the original spec: Resend API instead of `smtplib`,
  Reddit public RSS instead of PRAW. Both intentional. Do not "fix" them.
- `SENDER_EMAIL` is a Resend-verified domain, so there is no recipient
  restriction and delivery from CI should work.
- Repo will be **private**. Weekly ~2-minute runs sit far inside the 2,000
  free monthly Actions minutes.

---

## 3. The central risk: silent degradation

**This is the most important part of this spec.**

`aggregate.collect()` wraps each source in try/except, and `report.py` renders a
"source unavailable" note rather than failing. This graceful degradation is a
genuine feature locally. In CI it becomes a liability, because it means a broken
source produces a **green run and a delivered email**.

The specific concern: **Reddit blocks datacenter IPs.** GitHub Actions runs on
Azure ranges that are frequently blocked. `sources/reddit.py` works today from a
residential connection; from CI it may return 403 or an empty feed. If it does,
every weekly report silently ships with one third of its content missing, and
the configured failure-detection strategy (GitHub's automatic
workflow-failure email) will never fire, because nothing fails.

### Required response

**Verification gate.** The first green run is not sufficient evidence of
success. Download the workflow artifact PDF and confirm all three sections
contain real entries. Treat an empty Reddit section as a failed deployment, not
a minor blemish.

**Make degradation loud in CI.** Add an opt-in strict mode: when the environment
variable `STRICT_SOURCES` is set, `main.py` exits non-zero if `data["errors"]`
is non-empty. Set it in the workflow only. Local runs keep today's forgiving
behaviour; CI runs convert a dead source into a workflow failure, which GitHub
then emails about. This is what makes the chosen alerting strategy actually work.

**If Reddit is in fact blocked from CI,** do not silently accept it. Options, in
rough order of preference: set a more realistic browser `User-Agent` on the RSS
request and retry; switch to Reddit's public JSON endpoints; or consciously drop
Reddit to two sources and update the report and README to match. Record whichever
is chosen. What must not happen is a permanently empty section nobody decided on.

---

## 4. Work, in order

### Step 1 — Pre-commit safety audit

The only irreversible step in this spec. No git history exists yet, so this is a
clean slate; the sole opportunity to leak credentials is now.

- Confirm `.gitignore` covers `.env`, `__pycache__/`, and `output/`.
- Run `git init`, then run `git status` and **read the untracked list before
  staging anything**.
- `.env`, `__pycache__/`, and `output/` must not appear. If they do, fix
  `.gitignore` and re-check.
- Only then stage and make the initial commit.

### Step 2 — Resolve the `GITHUB_TOKEN` collision

GitHub reserves the secret name `GITHUB_TOKEN` and will reject any attempt to
create a repository secret with that name. `sources/github.py` reads
`os.getenv("GITHUB_TOKEN")`.

**Chosen approach — no source change.** In `run_radar.yml`, map the
auto-provided token into the environment:

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Referencing that token is legal even though creating a secret by that name is
not. It authenticates Search API calls at a substantially higher rate limit than
anonymous access.

*Rejected alternative:* renaming to `GH_API_TOKEN` throughout. Cleaner
semantically, but touches source files for no functional gain.

### Step 3 — Diagnose the `run_radar.yml` warning

VS Code shows a `!` marker on the workflow file. Cause unknown until opened.

This matters more than it looks: a workflow file that fails to parse does not
appear in the Actions tab at all and produces no error notification. It simply
does not exist as far as GitHub is concerned. Diagnose and resolve before
pushing, and after pushing confirm the workflow is actually listed.

### Step 4 — Ensure `output/` exists at runtime

`output/` is gitignored, so a fresh CI checkout will not contain it. If
`report.py` writes `output/ai_trend_radar.pdf` into a directory that does not
exist, CI fails with `FileNotFoundError` while the local machine works fine,
because the directory is already there.

Add `os.makedirs("output", exist_ok=True)` before the first write. Cheap, and
removes a guaranteed first-run failure.

### Step 5 — Confirm the Python version

Local `.pyc` files are `cpython-314`, indicating Python 3.14. Wheel availability
for `matplotlib` and `fpdf2` on 3.14 should be confirmed rather than assumed.

Pin an explicit version in the workflow. If wheel builds fail, dropping the CI
pin to 3.12 is the low-drama fix — note the divergence from local in the README.

### Step 6 — Rewrite `.env.example`

Currently documents an SMTP and PRAW design the code abandoned. Anyone setting
up fresh from it configures the project wrong. This is being fixed *before*
secret configuration, deliberately: the canonical list of required secrets must
not be wrong at the moment someone is entering secrets.

Correct contents:

- `RESEND_API_KEY` — required
- `SENDER_EMAIL` — required, Resend-verified domain address
- `RECIPIENT_EMAIL` — required
- `GITHUB_TOKEN` — optional locally, auto-provided in CI

Delete: `SMTP_HOST`, `SMTP_PORT`, `SENDER_APP_PASSWORD`, `REDDIT_CLIENT_ID`,
`REDDIT_CLIENT_SECRET`, and the dead `REDDIT_USER_AGENT`.

### Step 7 — Write `README.md`

Cover: what the project does; local setup; the three required secrets; how to
run (`--no-send` and full); how the weekly schedule works; how to trigger a
manual run; and the 60-day inactivity caveat from section 5.

### Step 8 — Push and configure

- Create the private repo, push.
- Add three repository secrets: `RESEND_API_KEY`, `SENDER_EMAIL`,
  `RECIPIENT_EMAIL`. Do **not** attempt to add `GITHUB_TOKEN` — see step 2.
- Confirm the workflow appears in the Actions tab.

### Step 9 — Iterate to green via manual dispatch

Use `workflow_dispatch`. Do not wait for Monday to discover a typo. Iterate
until green, then apply the section 3 verification gate: download the artifact
PDF and confirm **all three sections have real content**.

---

## 5. Known limitation to document, not solve

**GitHub disables scheduled workflows after 60 days of repository inactivity.**
On a private repo pushed once and then left alone, the cron runs for roughly two
months and then stops. Critically, this produces **no failure email**, because
nothing failed — the schedule is simply no longer registered.

**Decision: accept and document.** The common workaround (a second workflow that
commits a timestamp periodically to reset the clock) is a moving target that
GitHub has tightened before, and a missing weekly email is a noticeable signal.
Record the caveat in the README, including how to re-enable the schedule from
the Actions tab.

---

## 6. Constraints for the implementing session

- Do not refactor beyond the steps above. `report.py`'s `_san()` and
  `_wrap_tokens()` exist because real data broke without them — leave them alone.
- Do not migrate Resend back to SMTP, or RSS back to PRAW.
- Do not add the LLM categorization feature, however tempting once the pipeline
  is live. It is the next project, not this one.
- Step 1 gates everything. Do not stage a commit before the `git status` audit
  has been read.
