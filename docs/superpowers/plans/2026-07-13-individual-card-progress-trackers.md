# Individual Card Progress Trackers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add consistent 20-character Markdown progress trackers for active fee-waiver, cashback-cap, welcome, and premium-card milestones in every individual credit-card report.

**Architecture:** Extract the existing bar formatting from `card_benefit_tracker.py` into a presentation-only `card_progress.py` module. Each card generator continues to own eligibility, periods, caps, exclusions, freshness, and evidence state, and passes calculated values to the shared renderer. Combined reports and dashboards are not modified.

**Tech Stack:** Python 3.12, standard library, Markdown, pytest/unittest, existing card workflow scripts.

## Global Constraints

- Render exactly 20 filled/empty characters for active progress bars.
- Cap displayed fill and percentage at 100%; show excess separately.
- Use only official numeric targets already encoded in the workflows or verified from official issuer sources.
- Never render missing evidence as verified zero progress.
- Preserve all existing report filenames, calculation rules, transaction tables, recommendations, freshness gates, and response-link contracts.
- Do not modify combined reports or dashboards.
- Keep SBI card ending 3366 reward recommendations disabled until the exact variant is officially confirmed.
- Do not use raw HTML in generated Markdown.
- Preserve unrelated user changes and untracked files.

---

## File Map

- Create `card_progress.py`: shared presentation-only milestone renderer.
- Create `tests/test_card_progress.py`: isolated renderer contract tests.
- Modify `card_benefit_tracker.py`: consume the renderer for HSBC, HDFC, and pending SBI 3366 milestone sections.
- Modify `test_card_benefit_workflows.py`: shared-generator report regressions.
- Modify `HDFC Diners Black Metal Statements/benefits_config.json`: encode the officially verified quarterly bonus target and period.
- Modify `Airtel Axis Statements/update_report.py` and `Airtel Axis Statements/test_report_shape.py`: active waiver and cashback bars.
- Modify `Flipkart Axis Statements/update_report.py` and `Flipkart Axis Statements/test_update_report_dynamic_cycle.py`: active waiver and quarterly cashback bars.
- Modify `SBI Cashback Statements/update_report.py` and `SBI Cashback Statements/tests/test_report_shape.py`: active waiver and monthly cashback bars.
- Modify the six individual tracker `SKILL.md` files under `/Users/ejazanwar/.codex/skills/`: preserve the standardized output contract.
- Regenerate only individual card reports and validation artifacts.

---

### Task 1: Shared Markdown Milestone Renderer

**Files:**
- Create: `card_progress.py`
- Create: `tests/test_card_progress.py`
- Modify: `card_benefit_tracker.py:65-77`

**Interfaces:**
- Produces: `render_progress_bar(current: float | int | None, target: float | int | None, *, width: int = 20) -> str`
- Produces: `render_milestone(*, current, target, format_value, evidence_state="verified", period=None, supporting_lines=()) -> str`
- Evidence states: `verified`, `provisional`, `stale`, `pending`.
- Consumed by: every later task.

- [ ] **Step 1: Write failing renderer tests**

Create `tests/test_card_progress.py` with focused tests:

```python
import pytest

from card_progress import render_milestone, render_progress_bar


def money(value):
    return f"INR {value:,.2f}" if value is not None else "Pending"


@pytest.mark.parametrize(
    ("current", "target", "expected"),
    [
        (0, 100, "`░░░░░░░░░░░░░░░░░░░░ 0.0%`"),
        (16.5, 100, "`███░░░░░░░░░░░░░░░░░ 16.5%`"),
        (100, 100, "`████████████████████ 100.0%`"),
        (125, 100, "`████████████████████ 100.0%`"),
    ],
)
def test_render_progress_bar_contract(current, target, expected):
    assert render_progress_bar(current, target) == expected


@pytest.mark.parametrize("target", [None, 0, -1])
def test_render_progress_bar_handles_unavailable_targets(target):
    assert render_progress_bar(10, target) == "`Progress unavailable`"


def test_render_milestone_partial_verified():
    text = render_milestone(current=3301.13, target=20000, format_value=money)
    assert "- Progress: INR 3,301.13 of INR 20,000.00" in text
    assert "- Remaining: INR 16,698.87" in text
    assert "- Status: In progress" in text
    assert "Evidence:" not in text


def test_render_milestone_exceeded():
    text = render_milestone(current=25000, target=20000, format_value=money)
    assert "- Remaining: INR 0.00" in text
    assert "- Exceeded by: INR 5,000.00" in text
    assert "- Status: Met" in text


@pytest.mark.parametrize("state", ["provisional", "stale", "pending"])
def test_render_milestone_labels_non_verified_evidence(state):
    text = render_milestone(
        current=None if state == "pending" else 10,
        target=None if state == "pending" else 100,
        format_value=money,
        evidence_state=state,
    )
    assert f"- Evidence: {state.title()}" in text


def test_render_milestone_rejects_unknown_evidence_state():
    with pytest.raises(ValueError, match="Unsupported evidence state"):
        render_milestone(current=1, target=2, format_value=money, evidence_state="guessed")
```

- [ ] **Step 2: Run tests and verify the import fails**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest tests/test_card_progress.py -q
```

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'card_progress'`.

- [ ] **Step 3: Implement the presentation-only module**

Create `card_progress.py`:

```python
from __future__ import annotations

from collections.abc import Callable, Iterable


EVIDENCE_STATES = {"verified", "provisional", "stale", "pending"}


def render_progress_bar(
    current: float | int | None,
    target: float | int | None,
    *,
    width: int = 20,
) -> str:
    if target is None or float(target) <= 0 or width <= 0:
        return "`Progress unavailable`"
    ratio = min(1.0, max(0.0, float(current or 0) / float(target)))
    filled = int(ratio * width + 0.5)
    return f"`{'█' * filled}{'░' * (width - filled)} {ratio * 100:.1f}%`"


def render_milestone(
    *,
    current: float | int | None,
    target: float | int | None,
    format_value: Callable[[float | int | None], str],
    evidence_state: str = "verified",
    period: str | None = None,
    supporting_lines: Iterable[str] = (),
) -> str:
    if evidence_state not in EVIDENCE_STATES:
        raise ValueError(f"Unsupported evidence state: {evidence_state}")

    lines = [render_progress_bar(current, target)]
    if period:
        lines.extend(["", f"- Period: {period}"])

    if target is None or float(target) <= 0:
        lines.extend(["", "- Progress: Pending", "- Remaining: Pending", "- Status: Pending"])
    else:
        current_value = max(0.0, float(current or 0))
        target_value = float(target)
        remaining = max(0.0, target_value - current_value)
        exceeded = max(0.0, current_value - target_value)
        lines.extend([
            "",
            f"- Progress: {format_value(current_value)} of {format_value(target_value)}",
            f"- Remaining: {format_value(remaining)}",
        ])
        if exceeded:
            lines.append(f"- Exceeded by: {format_value(exceeded)}")
        lines.append(f"- Status: {'Met' if current_value >= target_value else 'In progress'}")

    if evidence_state != "verified":
        lines.append(f"- Evidence: {evidence_state.title()}")
    lines.extend(f"- {line}" for line in supporting_lines)
    return "\n".join(lines)
```

Replace the implementation in `card_benefit_tracker.py` with an import:

```python
from card_progress import render_milestone, render_progress_bar
```

- [ ] **Step 4: Run renderer and existing shared tests**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest tests/test_card_progress.py test_card_benefit_workflows.py -q
```

Expected: PASS with no renderer or existing shared workflow regressions.

- [ ] **Step 5: Commit the renderer**

```bash
git add card_progress.py tests/test_card_progress.py card_benefit_tracker.py
git commit -m "feat: add shared card progress renderer"
```

---

### Task 2: HSBC Reference Migration and Shared-Generator Milestones

**Files:**
- Modify: `card_benefit_tracker.py:286-365`
- Modify: `test_card_benefit_workflows.py`
- Modify: `HDFC Diners Black Metal Statements/benefits_config.json`

**Interfaces:**
- Consumes: `render_milestone(...)` from Task 1.
- Produces: `milestone_evidence_state(config: dict, freshness_text: str) -> str`.
- Produces: report sections with bars for HSBC/HDFC and pending output for SBI 3366.

- [ ] **Step 1: Add failing report-shape tests**

Extend `ReportShapeTests` in `test_card_benefit_workflows.py`:

```python
def _build_milestone_report(self, config, alerts=None, as_of="2026-07-01"):
    with tempfile.TemporaryDirectory() as tmp:
        card_dir = Path(tmp) / "Card Statements"
        write_json(card_dir / "benefits_config.json", config)
        write_json(card_dir / "gmail_alerts.json", alerts or [])
        card_freshness.write_sync_metadata(
            card_dir,
            card_name=config["card_name"],
            card_ending=config["card_ending"],
            source="gmail-connector-live",
            query="fixture",
            alerts=alerts or [],
            message_ids=["m1"],
        )
        return tracker.build_report(card_dir, as_of=tracker.parse_date(as_of))


def test_hsbc_uses_shared_tracker_contract(self):
    report = self._build_milestone_report({
        "card_name": "HSBC Live+ Credit Card",
        "card_ending": "8690",
        "variant_status": "confirmed",
        "cycle": {"start": "2026-06-29", "end": "2026-07-28"},
        "annual_fee": {"amount": 999, "waiver_spend": 200000},
        "welcome": {"spend_target": 20000, "window_days": 30},
        "benefit_rules": [],
    }, [{"date": "2026-07-01", "amount": 1000, "subject": "HSBC purchase"}])
    self.assertIn("- Status: In progress", report)
    bars = [line for line in report.splitlines() if line.startswith("`") and line.endswith("%`")]
    self.assertEqual(2, len(bars))


def test_hdfc_renders_fee_welcome_and_quarterly_trackers(self):
    report = self._build_milestone_report({
        "card_name": "HDFC Diners Black Metal Credit Card",
        "card_ending": "2360",
        "variant_status": "confirmed",
        "cycle": {
            "start": "2026-06-29",
            "end": "2026-07-28",
            "source": "Provisional setup cycle until first statement PDF confirms the card cycle.",
        },
        "annual_fee": {"amount": 10000, "waiver_spend": 800000},
        "welcome": {"spend_target": 150000, "window_days": 90},
        "quarterly_bonus": {
            "spend_target": 400000,
            "bonus_points": 10000,
            "period_type": "calendar_quarter",
        },
        "benefit_rules": [],
    }, [{"date": "2026-07-01", "amount": 10000, "subject": "HDFC purchase"}])
    self.assertIn("## 2. Fee and Waiver Tracker", report)
    self.assertIn("## 3. Welcome Benefit Tracker", report)
    self.assertIn("## 4. Quarterly Bonus Tracker", report)
    self.assertIn("INR 400,000.00", report)
    self.assertIn("- Evidence: Provisional", report)


def test_pending_sbi_variant_has_no_numeric_progress_claim(self):
    report = self._build_milestone_report({
        "card_name": "SBI Card ending 3366",
        "card_ending": "3366",
        "variant_status": "pending",
        "cycle": {"start": "2026-06-29", "end": "2026-07-28"},
        "annual_fee": {"amount": None, "waiver_spend": None},
        "welcome": {"spend_target": None, "window_days": None},
        "benefit_rules": [],
    })
    self.assertEqual(2, report.count("`Progress unavailable`"))
    self.assertIn("- Progress: Pending", report)
    self.assertIn("- Evidence: Pending", report)
    self.assertNotIn("## 4. Quarterly Bonus Tracker", report)
```

Place `_build_milestone_report` inside `ReportShapeTests`; it supplies current connector metadata while the HDFC cycle source deliberately exercises the provisional state.

- [ ] **Step 2: Run the focused tests and verify missing sections fail**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest test_card_benefit_workflows.py -q
```

Expected: FAIL because HDFC still uses tables, SBI pending output lacks explicit evidence labels, and the quarterly section does not exist.

- [ ] **Step 3: Encode the official HDFC quarterly milestone**

After rechecking the official HDFC Diners Black Metal product page, add this object to `HDFC Diners Black Metal Statements/benefits_config.json`:

```json
"quarterly_bonus": {
  "spend_target": 400000,
  "bonus_points": 10000,
  "period_type": "calendar_quarter",
  "notes": [
    "10,000 bonus reward points require INR 4 lakh eligible spend in a calendar quarter."
  ]
}
```

If the official source no longer confirms these exact values, stop this sub-step and leave the quarterly tracker pending rather than substituting a secondary-source target.

- [ ] **Step 4: Add shared-generator milestone rendering**

In `card_benefit_tracker.py`:

```python
def milestone_evidence_state(config: dict[str, Any], freshness_text: str) -> str:
    if config.get("variant_status") != "confirmed":
        return "pending"
    if freshness_text.startswith("Stale cache"):
        return "stale"
    if "Provisional" in str(config.get("cycle", {}).get("source", "")):
        return "provisional"
    return "verified"
```

Use `render_milestone` for fee and welcome sections for all cards handled by this generator. Keep SBI 3366 pending because both targets are `None`. For HDFC, calculate calendar-quarter spend only from alerts inside that quarter and render:

```python
quarterly = config.get("quarterly_bonus")
if quarterly and summary["variant_status"] == "confirmed":
    quarter_start_month = ((as_of.month - 1) // 3) * 3 + 1
    quarter_start = date(as_of.year, quarter_start_month, 1)
    quarter_end_month = quarter_start_month + 2
    quarter_end = date(
        as_of.year,
        quarter_end_month,
        calendar.monthrange(as_of.year, quarter_end_month)[1],
    )
    quarter_spend = sum(
        alert["amount"]
        for alert in alerts
        if (parsed := parse_date(alert["date"])) and quarter_start <= parsed <= quarter_end
    )
```

Because the current HDFC cache may not cover the complete quarter, pass `evidence_state="provisional"` until sync metadata or statement coverage proves the full period. Renumber later HDFC sections deterministically; do not add a quarterly section to HSBC or SBI 3366.

- [ ] **Step 5: Run shared tests and rebuild the three reports**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest tests/test_card_progress.py test_card_benefit_workflows.py -q
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 "HSBC Live Plus Statements/run_workflow.py" --sync-source none
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 "HDFC Diners Black Metal Statements/run_workflow.py" --sync-source none
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 "SBI New Card Statements/run_workflow.py" --sync-source none
```

Expected: tests PASS; all three reports rebuild; validation may remain blocked only where existing freshness/variant gates intentionally block trust.

- [ ] **Step 6: Commit shared-generator integration**

```bash
git add card_benefit_tracker.py test_card_benefit_workflows.py \
  "HDFC Diners Black Metal Statements/benefits_config.json" \
  "HSBC Live Plus Statements/benefit_tracker_report.md" \
  "HDFC Diners Black Metal Statements/benefit_tracker_report.md" \
  "SBI New Card Statements/benefit_tracker_report.md"
git commit -m "feat: standardize benefit milestone trackers"
```

---

### Task 3: Airtel Axis Active Waiver and Cashback Bars

**Files:**
- Modify: `Airtel Axis Statements/update_report.py`
- Modify: `Airtel Axis Statements/test_report_shape.py`
- Modify: `Airtel Axis Statements/cashback_cap_report.md`

**Interfaces:**
- Consumes: `card_progress.render_milestone`.
- Inputs remain `current_waiver`, `airtel_cb`, `utility_cb`, `merchant_cb`, and existing cap constants.
- Output adds one active waiver bar and three active category-cap bars; historical tables remain unchanged.

- [ ] **Step 1: Add failing report-shape assertions**

Extend `Airtel Axis Statements/test_report_shape.py`:

```python
def test_active_periods_use_standard_progress_bars():
    report = REPORT.read_text()
    assert report.count("█") + report.count("░") >= 80
    assert "### Current Waiver Year" in report
    assert "### 25% Airtel Cashback Cap" in report
    assert "### 10% Utilities Cashback Cap" in report
    assert "### 10% Merchants Cashback Cap" in report
    for line in report.splitlines():
        if line.startswith("`") and line.endswith("%`"):
            bar = line.split(" ", 1)[0].strip("`")
            assert len(bar) == 20
    assert "<span" not in report
    assert "<br" not in report
```

- [ ] **Step 2: Run the test and verify headings are absent**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest "Airtel Axis Statements/test_report_shape.py" -q
```

Expected: FAIL on the new tracker headings.

- [ ] **Step 3: Render the active waiver and category caps**

Import the shared renderer at the top of `Airtel Axis Statements/update_report.py` after adding the repository root to `sys.path` using the same pattern as the other workflow scripts:

```python
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from card_progress import render_milestone
```

Before the report template, prepare:

```python
current_waiver_tracker = render_milestone(
    current=current_waiver["eligible_spend"],
    target=current_waiver["target"],
    format_value=format_amount,
    period=current_waiver["period"],
    supporting_lines=(f"Source: {current_waiver['source']}",),
)

cap_trackers = [
    ("25% Airtel Cashback Cap", airtel_cb, 250.00, airtel_spend),
    ("10% Utilities Cashback Cap", utility_cb, 250.00, utility_spend),
    ("10% Merchants Cashback Cap", merchant_cb, 500.00, merchant_spend),
]
current_cap_trackers = "\n\n".join(
    f"### {label}\n\n" + render_milestone(
        current=earned,
        target=cap,
        format_value=format_amount,
        period=cycle_period,
        supporting_lines=(f"Qualifying spend: {format_amount(spend)}",),
    )
    for label, earned, cap, spend in cap_trackers
)
```

Insert `### Current Waiver Year` plus `current_waiver_tracker` above the existing waiver-year table. Insert `current_cap_trackers` at the top of `## 4. Current Cycle Progress`. Do not remove the transaction or historical tables.

- [ ] **Step 4: Rebuild and run Airtel tests**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 "Airtel Axis Statements/update_report.py"
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest "Airtel Axis Statements/test_report_shape.py" -q
```

Expected: report rebuild succeeds and tests PASS.

- [ ] **Step 5: Commit Airtel changes**

```bash
git add "Airtel Axis Statements/update_report.py" \
  "Airtel Axis Statements/test_report_shape.py" \
  "Airtel Axis Statements/cashback_cap_report.md"
git commit -m "feat: add Airtel Axis progress trackers"
```

---

### Task 4: Flipkart Axis Active Waiver and Quarterly Cashback Bars

**Files:**
- Modify: `Flipkart Axis Statements/update_report.py`
- Modify: `Flipkart Axis Statements/test_update_report_dynamic_cycle.py`
- Modify: `Flipkart Axis Statements/cashback_cap_report.md`

**Interfaces:**
- Consumes: `card_progress.render_milestone`.
- Inputs remain `waiver_summary["current_year"]` and the current quarter's Flipkart, Myntra, and Cleartrip cashback calculations.
- Output adds one active waiver bar and three active statement-quarter cap bars.

- [ ] **Step 1: Add failing dynamic-cycle assertions**

After `update_report.update_report()` in `test_report_uses_active_cycle_and_includes_current_alert`, add:

```python
assert "### Current Waiver Year" in report
assert "### Flipkart Cashback Cap" in report
assert "### Myntra Cashback Cap" in report
assert "### Cleartrip Cashback Cap" in report
assert "- Period: June 16, 2026 – September 15, 2026" in report
assert "- Qualifying spend: ₹3,739.00" in report
assert "- Qualifying spend: ₹15,405.00" in report
assert "<span" not in report
assert "<br" not in report
```

Also extract every backticked bar line and assert exactly 20 filled/empty characters.

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
cd "Flipkart Axis Statements"
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest test_update_report_dynamic_cycle.py -q
```

Expected: FAIL because the active tracker headings do not exist.

- [ ] **Step 3: Add active tracker rendering**

Import `render_milestone` through the repository-root path pattern used in Task 3. In `format_annual_fee_waiver_section`, render `summary["current_year"]` above the existing table:

```python
current_tracker = render_milestone(
    current=current["eligible_spend"],
    target=current["target"],
    format_value=format_amount,
    period=current["period"],
    supporting_lines=(f"Source: {current['source']}",),
)
```

Build the current statement-quarter trackers from the existing category variables:

```python
quarter_trackers = "\n\n".join(
    f"### {label} Cashback Cap\n\n" + render_milestone(
        current=cashback,
        target=4000.00,
        format_value=format_amount,
        period=f"{format_long_date(quarter_start)} – {format_long_date(quarter_end)}",
        supporting_lines=(f"Qualifying spend: {format_amount(spend)}",),
    )
    for label, cashback, spend in (
        ("Flipkart", prev_flipkart_cb + flipkart_cb_capped, flipkart_spend),
        ("Myntra", prev_myntra_cb + myntra_cb_capped, myntra_spend),
        ("Cleartrip", prev_cleartrip_cb + cleartrip_cb_capped, cleartrip_spend),
    )
)
```

Insert these trackers above the current statement-quarter summary table. Keep the historical quarter table unchanged.

- [ ] **Step 4: Rebuild and run Flipkart tests**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 "Flipkart Axis Statements/update_report.py"
cd "Flipkart Axis Statements"
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest test_update_report_dynamic_cycle.py test_parse_jan_2026.py test_parse_pdf.py -q
```

Expected: all tests PASS and the report contains four active bars.

- [ ] **Step 5: Commit Flipkart changes**

```bash
git add "Flipkart Axis Statements/update_report.py" \
  "Flipkart Axis Statements/test_update_report_dynamic_cycle.py" \
  "Flipkart Axis Statements/cashback_cap_report.md"
git commit -m "feat: add Flipkart Axis progress trackers"
```

---

### Task 5: SBI Cashback Active Waiver and Monthly Cashback Bars

**Files:**
- Modify: `SBI Cashback Statements/update_report.py`
- Modify: `SBI Cashback Statements/tests/test_report_shape.py`
- Modify: `SBI Cashback Statements/cashback_cap_report.md`

**Interfaces:**
- Consumes: `card_progress.render_milestone`.
- Inputs remain `waiver_summary["current_year"]`, `june_online_cb`, `june_offline_cb`, and their category spends.
- Output adds one active waiver bar and two active statement-cycle cashback bars.

- [ ] **Step 1: Add failing report-shape tests**

Extend `SBI Cashback Statements/tests/test_report_shape.py`:

```python
def test_active_waiver_and_cashback_trackers_use_standard_bars():
    report = REPORT.read_text()
    assert "### Current Waiver Year" in report
    assert "### 5% Online Cashback Cap" in report
    assert "### 1% Offline Cashback Cap" in report
    assert "Qualifying spend:" in report
    bars = [line for line in report.splitlines() if line.startswith("`") and line.endswith("%`")]
    assert len(bars) >= 3
    for line in bars:
        assert len(line.split(" ", 1)[0].strip("`")) == 20
    assert "<span" not in report
    assert "<br" not in report
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest "SBI Cashback Statements/tests/test_report_shape.py" -q
```

Expected: FAIL on the new headings.

- [ ] **Step 3: Render active waiver and category caps**

Import `render_milestone` using the repository-root path pattern. In `format_annual_fee_waiver_section`, add the current-year renderer above the existing historical/current table.

Before the report template, build:

```python
cashback_trackers = "\n\n".join(
    f"### {label} Cashback Cap\n\n" + render_milestone(
        current=earned,
        target=2000.00,
        format_value=format_amount,
        period=f"{format_long_date(start_date)} – {format_long_date(end_date)}",
        supporting_lines=(f"Qualifying spend: {format_amount(spend)}",),
    )
    for label, earned, spend in (
        ("5% Online", june_online_cb, june_online_spend),
        ("1% Offline", june_offline_cb, june_offline_spend),
    )
)
```

Insert `cashback_trackers` above the existing current-cycle status table. Keep the excluded category out of progress bars because it has no earnable cap.

- [ ] **Step 4: Rebuild and run SBI validation/tests**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 "SBI Cashback Statements/update_report.py"
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest \
  "SBI Cashback Statements/tests/test_report_shape.py" \
  "SBI Cashback Statements/tests/test_validate_accounting.py" -q
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 "SBI Cashback Statements/validate_statements.py"
```

Expected: report tests PASS; validator exits 0 or reports only an already-known external freshness/statement blocker, which must be reported rather than hidden.

- [ ] **Step 5: Commit SBI changes**

```bash
git add "SBI Cashback Statements/update_report.py" \
  "SBI Cashback Statements/tests/test_report_shape.py" \
  "SBI Cashback Statements/cashback_cap_report.md"
git commit -m "feat: add SBI Cashback progress trackers"
```

---

### Task 6: Individual Skill Contracts and Cross-Card Verification

**Files:**
- Modify: `/Users/ejazanwar/.codex/skills/airtel-axis-cashback-tracker/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/flipkart-axis-cashback-tracker/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/sbi-cashback-tracker/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/hdfc-diners-black-metal-benefit-tracker/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/hsbc-live-plus-benefit-tracker/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/sbi-new-card-benefit-tracker/SKILL.md`
- Verify only: combined-report and dashboard files.

**Interfaces:**
- Consumes: completed individual report contracts from Tasks 2-5.
- Produces: durable workflow instructions requiring 20-character bars and card-specific active milestones.

- [ ] **Step 1: Add the standardized contract to each skill**

Add a concise guardrail to every confirmed-card skill:

```markdown
- Preserve active milestone trackers when generating or rebuilding the report. Each active fee-waiver, cashback-cap, welcome, or premium-card milestone must use the shared 20-character plain-Markdown bar, percentage, current value versus target, remaining or exceeded amount, measurement period, and evidence state when not verified.
```

For SBI 3366, use this stricter text:

```markdown
- Preserve pending milestone trackers, but do not show numeric progress or enable reward recommendations until the exact card variant and official targets are confirmed. Pending trackers must use `Progress unavailable` and an explicit `Pending` evidence state.
```

Do not change each skill's Gmail query, report-link requirement, or validation workflow.

- [ ] **Step 2: Validate all six skills**

Use the validation command documented by `/Users/ejazanwar/.codex/skills/.system/skill-creator/SKILL.md` against each changed skill directory.

Expected: all six skill packages validate successfully. If the validator is unavailable, parse each frontmatter block and verify required `name` and `description` fields with the pinned Python interpreter, then state that the fallback was used.

- [ ] **Step 3: Run the complete focused test set**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest \
  tests/test_card_progress.py \
  test_card_benefit_workflows.py \
  "Airtel Axis Statements/test_report_shape.py" \
  "Flipkart Axis Statements/test_update_report_dynamic_cycle.py" \
  "Flipkart Axis Statements/test_parse_jan_2026.py" \
  "Flipkart Axis Statements/test_parse_pdf.py" \
  "SBI Cashback Statements/tests/test_report_shape.py" \
  "SBI Cashback Statements/tests/test_validate_accounting.py" -q
```

Expected: all focused tests PASS with zero failures.

- [ ] **Step 4: Rebuild and validate all individual reports**

Run the existing per-card workflows with `--sync-source none` only after confirming live Gmail refresh already occurred; otherwise perform each skill's required live read-only refresh first. Then run every card's validator.

Expected individual artifacts:

```text
Airtel Axis Statements/cashback_cap_report.md
Flipkart Axis Statements/cashback_cap_report.md
SBI Cashback Statements/cashback_cap_report.md
HDFC Diners Black Metal Statements/benefit_tracker_report.md
HSBC Live Plus Statements/benefit_tracker_report.md
SBI New Card Statements/benefit_tracker_report.md
```

Inspect each active tracker for exactly 20 bar characters, correct current/target/remaining values, correct period, and honest evidence state.

- [ ] **Step 5: Prove combined outputs are unchanged**

Before rebuilding individual reports, record hashes for:

```bash
shasum combined_cashback_report.md combined_card_benefits_report.md
```

After all individual rebuilds, rerun the same command.

Expected: identical hashes. Do not regenerate either combined report or any dashboard.

- [ ] **Step 6: Inspect repository scope and remove only new test artifacts**

Run:

```bash
git status --short
git diff --check
```

Remove only caches or scratch artifacts created by this implementation. Do not remove or modify pre-existing untracked files. Confirm the diff contains only the shared renderer, individual generators/tests/config, generated individual reports, skill contracts, and implementation documentation.

- [ ] **Step 7: Commit skill contracts and final verification artifacts**

Commit repository-owned changes first:

```bash
git add card_progress.py tests/test_card_progress.py card_benefit_tracker.py test_card_benefit_workflows.py \
  "Airtel Axis Statements/update_report.py" "Airtel Axis Statements/test_report_shape.py" "Airtel Axis Statements/cashback_cap_report.md" \
  "Flipkart Axis Statements/update_report.py" "Flipkart Axis Statements/test_update_report_dynamic_cycle.py" "Flipkart Axis Statements/cashback_cap_report.md" \
  "SBI Cashback Statements/update_report.py" "SBI Cashback Statements/tests/test_report_shape.py" "SBI Cashback Statements/cashback_cap_report.md" \
  "HDFC Diners Black Metal Statements/benefits_config.json" "HDFC Diners Black Metal Statements/benefit_tracker_report.md" \
  "HSBC Live Plus Statements/benefit_tracker_report.md" "SBI New Card Statements/benefit_tracker_report.md"
git commit -m "feat: standardize individual card milestone trackers"
```

The personal skill files live outside this repository. Report them separately in the handoff and do not imply they were included in the repository commit.

---

## Final Acceptance Checklist

- Every confirmed individual card shows active bars for all applicable official numeric milestones.
- HSBC retains its existing visible 20-character fee and welcome format through the shared renderer.
- HDFC shows fee, welcome, and quarterly-bonus milestones with provisional evidence when quarter coverage is incomplete.
- Airtel, Flipkart, and SBI Cashback show active fee-waiver and cashback-cap bars while preserving current tables.
- SBI 3366 remains pending with no invented numeric targets or enabled recommendations.
- Every active bar is exactly 20 characters and visually capped at 100%.
- Stale, provisional, and pending evidence cannot appear verified.
- All focused tests and card validators have fresh recorded results.
- Combined reports and dashboards are byte-for-byte unchanged.
- No unrelated user files are staged, overwritten, or removed.
