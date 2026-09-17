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

---

## L-014 · Guard Against Sub-File Entrypoints & Handle Selectbox Routing via Callbacks
**Trigger**: When clicking the card switcher dropdown on Streamlit Cloud, the page did not change because Streamlit Cloud was configured to execute `HDFC Diners Black Metal Statements/hdfc_dcbm_app.py` directly rather than root `app.py`. Furthermore, relying on procedural `if selected != current:` checks without top-level routing gates failed on reruns.

**Rule**:
1. When supporting multi-dashboard / multi-card switching where sub-files might be invoked directly as entrypoints, **place top-level router gates in EVERY sub-file script**, not just in the root `app.py`. If `st.session_state["selected_card"]` indicates another view, immediately delegate via `runpy.run_path()` and `st.stop()`.
2. Use shared widget keys with native `on_change` callbacks (e.g. `key="active_card_switcher", on_change=on_card_change`) and dynamic `index=options.index(...)` rather than separate keys and procedural re-rerun blocks, ensuring state synchronizes instantaneously upon click.

---

## L-015 · Target BaseWeb Inner Child Divs & Always Inject Raw CSS with `st.html()`
**Trigger**: Custom CSS on `div[data-testid="stSelectbox"] div[data-baseweb="select"]` failed to remove Streamlit's default pale-blue fill (`#f0f2f6`), and segmented control active states failed to display in production because CSS comments were passed inside `st.markdown(..., unsafe_allow_html=True)`.

**Rule**:
1. Always use `st.html(f"""<style>...</style>""")` for CSS/HTML injection in Streamlit ≥ 1.40. `st.markdown` will parse CSS as markdown text and strip or corrupt style tags.
2. In BaseWeb inputs and selectboxes, always target the inner child div: `div[data-baseweb="select"] > div` to override Streamlit's hardcoded background color.

---

## L-016 · Support Multi-Format Email Drift & In-Process Sync for Cloud Secrets
**Trigger**: HSBC changed transaction alert subject line from `"You have used your HSBC Credit Card ending with 8690 for a purchase transaction"` to generic `"Credit Card Transaction Alert"` and body text format from `"Credit card no ending with 8690... on 15 Aug 2026"` to `"HSBC Credit Card xx8690 was used for a transaction of INR... on 16/09/26"`. The sync script missed all alerts sent after 15 August 2026. Furthermore, running `sync_alerts.py` in a separate subprocess under Streamlit Cloud broke access to `st.secrets["gmail_credentials"]`.

**Rule**:
1. When scraping/syncing bank alerts, never assume email subject or body templates remain static forever. Support multiple subject variations in Gmail queries and build multi-format parser branches (supporting `%d %b %Y`, `%d/%m/%Y`, `%d/%m/%y`).
2. When executing live sync in cloud environments (like Streamlit Cloud), execute sync routines **in-process** (`import sync_alerts; sync_alerts.run(...)`) rather than invoking `subprocess.run([sys.executable, ...])` so that `st.secrets` remains directly available to the credential loader.

---

## L-017 · Use Isolated `spec_from_file_location` When Dynamically Loading Homonymous Modules
**Trigger**: In a multi-dashboard application where both cards have a local file named `sync_alerts.py`, calling `import sync_alerts` dynamically after modifying `sys.path` returned the cached `sys.modules["sync_alerts"]` from the first card (HDFC), causing HSBC's sync routine to run HDFC's query and write HDFC transactions into HSBC's ledger.

**Rule**:
Never rely on `sys.path.insert(0, ...)` + `import <common_name>` to load card-specific or directory-specific scripts that share the same filename. Always use `importlib.util.spec_from_file_location(unique_module_name, script_path)` and execute with `spec.loader.exec_module(module)` to ensure strict namespace isolation.



