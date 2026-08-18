# Antigravity — Lessons Learned

Rules captured after user corrections in this session. These apply to all future work.

---

## L-001 · Always Screenshot Before Reporting UI Done
**Trigger**: Deployed CSS that rendered as raw text on screen; reported it as done without validating.

**Rule**: After *any* UI change:
1. Take a headless Chrome screenshot immediately
2. Visually inspect the rendered output
3. Only report done if the screenshot confirms the change looks correct

Never declare a UI task complete based on code alone.

---

## L-002 · Never Use `st.markdown()` for Raw HTML or CSS in Streamlit ≥ 1.40
**Trigger**: CSS block with `/* comments */` and `**bold**` syntax injected via `st.markdown(..., unsafe_allow_html=True)` — markdown parser ate the asterisks and broke the `<style>` tag.

**Rule**: Always use `st.html(...)` for any raw HTML or CSS. It bypasses the markdown parser entirely. `st.markdown` is only for actual markdown text content.

---

## L-003 · Never Use `**bold**` Markdown Inside `st.markdown()` HTML Blocks
**Trigger**: Budget status message like `f"Spent **₹{x:,.2f}**..."` was passed into a `st.markdown` that also contained HTML. The markdown bold rendered as literal `**₹1,361.00**`.

**Rule**: Inside any `st.markdown` or `st.html` block that is already HTML, use `<strong>...</strong>` for bold — never `**...**`.

---

## L-004 · Always Isolate Test Databases from Production Data
**Trigger**: `test_runner.py` called `os.remove(DB_PATH)` on the live production database, wiping 48 real synced transactions.

**Rule**: Every test file must override all config paths to `test_*` variants *before* any imports run. Always add a `tearDown` that deletes the test files.

---

## L-005 · Never Let Mock/Demo Data Silently Write to the Live Database
**Trigger**: The offline fallback mode inserted fabricated transactions into `expenses.db`.

**Rule**: Any demo or mock mode must write to a clearly named separate file (`demo_expenses.db`) or refuse to write and print a clear warning. Never use the production DB path.

---

## L-006 · Use Plotly for Charts in Dark-Themed Apps, Not `st.bar_chart`
**Trigger**: `st.bar_chart` rendered white backgrounds inside a dark slate dashboard.

**Rule**: Always use Plotly with explicit `plot_bgcolor` and `paper_bgcolor` matching the app background color. `st.bar_chart` is a prototype tool only.

---

## L-007 · Resolve All "Uncategorized" Merchants Before Session Ends
**Trigger**: 6+ real merchants logged as "Uncategorized" with no rules for them.

**Rule**: After the first live Gmail sync, always query uncategorized count and resolve to zero before closing the session.

---

## L-008 · Warn Clearly When Offline Fallback Mode Activates
**Trigger**: Sync button silently fell back to inserting mock data with no banner.

**Rule**: Any fallback/degraded mode must show a prominent `st.warning`, not a success message.

---

## L-009 · Keep Implementation Plan and Task List as Living Documents
**Trigger**: `implementation_plan.md` was never updated after scope evolved. It became stale.

**Rule**: Update the plan document every time a significant scope change or architectural decision happens mid-execution.

---

## L-010 · Verify launchd Schedules End-to-End, Not Just With `kickstart`
**Trigger**: The launchd plist was only tested with manual `launchctl kickstart`, not the actual timer.

**Rule**: To verify a launchd schedule, temporarily set `StartInterval` to 60s, wait 90s, check logs, then restore the intended interval.
---

## L-011 · Explicitly Distinguish Credit Cards with the Same Bank or Name
**Trigger**: User believed they paid all HDFC and Federal card bills, but had paid card HDFC 5436 and Federal 0321 while leaving HDFC 5146 and Federal 6411 unpaid.

**Rule**: Always explicitly check if there are multiple cards from the same issuer (e.g. HDFC, Federal).
1. Never report payment status or due alerts under a generic bank name (e.g. "Federal Bank") if multiple cards exist; always include the last 4 digits in all logs, tables, and warnings.
2. When the user asserts they have paid a bill but it shows as unpaid, check if they might have paid a different card from the same bank before declaring a mismatch.
 
---

## L-012 · Prevent Sleep Loops Under Persistent API Rate Limits (429) & Resolve Git Conflicts Programmatically
**Trigger**: A pipeline run encountered persistent Gemini 429 quota limits across 72 new jobs and wasted 5 hours sleeping (186s per job). Subsequent scheduled runs triggered concurrently, causing git pull/push failures due to merge conflicts on `scraped_jobs.json`.

**Rule**:
1. When calling APIs under a free-tier rate limit, always implement a `quota_exhausted` tracker. If retries on a single request fail continuously, flip the flag and skip all subsequent API calls in the queue immediately (avoiding massive cumulative sleep delay).
2. For cron-scheduled tasks that commit/push back to the repository, write a dedicated merge conflict resolution script (`git_push_retry.py`) that stashes changes, pulls/rebases, and programmatically merges JSON database arrays and prepended markdown log headers before retrying the push. Never rely on raw `git pull --rebase` to resolve automatically on concurrent pushes.

---

## L-013 · Never Generate Synthetic / Placeholder URLs in Research Briefings
**Trigger**: The Indian Stock Market Reddit Radar briefing included synthesized Reddit thread slug URLs (e.g. `reddit.com/r/.../comments/slug`) that failed with 404s.

**Rule**:
1. When citing external discussions or community posts in briefings and summaries, **NEVER** fabricate placeholder URLs or hypothetical permalink slugs.
2. If exact post permalinks cannot be verified, always construct functional, live targeted search URLs (e.g. `https://www.reddit.com/r/<subreddit>/search/?q=<query>&restrict_sr=1&sort=relevance`) or direct subreddit feeds.
3. Validate link structure before reporting completion.
