# Credit Card Milestone Days-Left Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a deterministic calendar-day countdown in every active credit-card milestone block across the six individual tracker workflows.

**Architecture:** Extend the pure shared Markdown renderer in `card_progress.py` with a tested deadline formatter, then pass real deadline and as-of dates from the three cashback generators and the shared premium-card generator. Unknown or variant-gated dates render Pending; combined reports reuse individual report text and do not calculate dates independently.

**Tech Stack:** Python 3.12, pytest, unittest, plain Markdown report generation, JSON tracker configuration.

## Global Constraints

- Deadline day displays `Days left: 0`; preceding dates use `deadline - as_of` calendar days.
- Completed milestones display `Days left: Not applicable — milestone met`.
- Expired unmet milestones display `Deadline passed: N days ago`.
- Missing deadlines display `Days left: Pending`.
- Existing 20-character bars, percentages, values, evidence states, freshness gates, and source data remain unchanged.
- Only canonical non-numbered files may be edited; preserve all pre-existing user changes and duplicate artifacts.
- Use `/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3` for tests, validation, and report rebuilds.
- Report rebuilds use existing cached inputs and must not mutate Gmail.

---

## File Map

- `card_progress.py`: normalize date inputs and render the shared countdown line.
- `tests/test_card_progress.py`: define the complete shared countdown contract.
- `Airtel Axis Statements/update_report.py`: supply active cycle and waiver-year deadlines.
- `Flipkart Axis Statements/update_report.py`: supply active quarter and waiver-year deadlines.
- `SBI Cashback Statements/update_report.py`: supply active cycle and waiver-year deadlines.
- `card_benefit_tracker.py`: supply premium-card quarterly deadlines and Pending dates for unsupported fee/welcome windows.
- `test_card_benefit_workflows.py`: verify HDFC, HSBC, and SBI New report output.
- Card-specific report-shape tests: verify countdowns survive report generation.
- Eight installed `SKILL.md` files: preserve the countdown contract for future individual and aggregate refreshes.

### Task 1: Shared countdown contract

**Files:**
- Modify: `/Users/ejazanwar/Documents/Gmail Automations/tests/test_card_progress.py`
- Modify: `/Users/ejazanwar/Documents/Gmail Automations/card_progress.py`

**Interfaces:**
- Produces: `render_days_left(*, deadline: date | datetime | None, as_of: date | datetime, milestone_met: bool) -> str`
- Extends: `render_milestone(..., deadline=None, as_of=None) -> str`

- [ ] **Step 1: Write failing shared-helper tests**

Add `from datetime import date, datetime` and import `render_days_left`. Add these tests:

```python
@pytest.mark.parametrize(
    ("deadline", "as_of", "met", "expected"),
    [
        (date(2026, 7, 20), date(2026, 7, 14), False, "Days left: 6"),
        (date(2026, 7, 14), date(2026, 7, 14), False, "Days left: 0"),
        (date(2026, 7, 12), date(2026, 7, 14), False, "Deadline passed: 2 days ago"),
        (date(2026, 7, 20), date(2026, 7, 14), True, "Days left: Not applicable — milestone met"),
        (None, date(2026, 7, 14), False, "Days left: Pending"),
        (datetime(2026, 7, 20, 23, 59), datetime(2026, 7, 14, 9, 0), False, "Days left: 6"),
    ],
)
def test_render_days_left_contract(deadline, as_of, met, expected):
    assert render_days_left(deadline=deadline, as_of=as_of, milestone_met=met) == expected


def test_render_days_left_rejects_unsupported_date_values():
    with pytest.raises(TypeError, match="deadline must be a date, datetime, or None"):
        render_days_left(deadline="2026-07-20", as_of=date(2026, 7, 14), milestone_met=False)


def test_render_milestone_includes_countdown_line():
    text = render_milestone(
        current=25,
        target=100,
        format_value=money,
        deadline=date(2026, 7, 20),
        as_of=date(2026, 7, 14),
    )
    assert "- Days left: 6" in text
```

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```bash
cd '/Users/ejazanwar/Documents/Gmail Automations'
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest tests/test_card_progress.py -q
```

Expected: collection fails because `render_days_left` is not defined.

- [ ] **Step 3: Implement the pure helper and renderer integration**

In `card_progress.py`, import `date` and `datetime`, then add:

```python
def _calendar_date(value, *, name: str, allow_none: bool = False) -> date | None:
    if value is None and allow_none:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    allowed = "date, datetime, or None" if allow_none else "date or datetime"
    raise TypeError(f"{name} must be a {allowed}")


def render_days_left(*, deadline, as_of, milestone_met: bool) -> str:
    if milestone_met:
        return "Days left: Not applicable — milestone met"
    deadline_date = _calendar_date(deadline, name="deadline", allow_none=True)
    if deadline_date is None:
        return "Days left: Pending"
    as_of_date = _calendar_date(as_of, name="as_of")
    delta = (deadline_date - as_of_date).days
    if delta >= 0:
        return f"Days left: {delta}"
    elapsed = abs(delta)
    unit = "day" if elapsed == 1 else "days"
    return f"Deadline passed: {elapsed} {unit} ago"
```

Add optional `deadline=None` and `as_of=None` keyword parameters to `render_milestone`. After its Period line, append:

```python
if as_of is not None:
    milestone_met = target is not None and float(target) > 0 and float(current or 0) >= float(target)
    lines.extend(["", f"- {render_days_left(deadline=deadline, as_of=as_of, milestone_met=milestone_met)}"])
```

This keeps legacy callers unchanged until they explicitly supply an as-of date.

- [ ] **Step 4: Run shared tests and confirm GREEN**

Run the Task 1 pytest command. Expected: all tests pass.

- [ ] **Step 5: Commit the shared contract**

```bash
git add card_progress.py tests/test_card_progress.py
git commit -m "feat: add shared milestone deadline countdown"
```

### Task 2: Cashback-card deadline propagation

**Files:**
- Modify: `/Users/ejazanwar/Documents/Gmail Automations/Airtel Axis Statements/update_report.py`
- Modify: `/Users/ejazanwar/Documents/Gmail Automations/Airtel Axis Statements/test_report_shape.py`
- Modify: `/Users/ejazanwar/Documents/Gmail Automations/Flipkart Axis Statements/update_report.py`
- Create: `/Users/ejazanwar/Documents/Gmail Automations/Flipkart Axis Statements/test_report_shape.py` only if no canonical test file exists at execution time
- Modify: `/Users/ejazanwar/Documents/Gmail Automations/SBI Cashback Statements/update_report.py`
- Modify: `/Users/ejazanwar/Documents/Gmail Automations/SBI Cashback Statements/tests/test_report_shape.py`

**Interfaces:**
- Consumes: `render_milestone(deadline=..., as_of=...)` from Task 1.
- Produces: generated cashback milestone blocks with cycle/quarter and waiver countdowns.

- [ ] **Step 1: Add failing generated-report assertions**

In Airtel and SBI report-shape tests, extend the active tracker test with:

```python
days_lines = [line for line in report.splitlines() if line.startswith("- Days left:")]
assert len(days_lines) >= 3
assert all(line != "- Days left: Pending" for line in days_lines)
```

For Flipkart, add a canonical report-shape test with the same pattern and assert at least four lines: one waiver tracker and three quarterly cap trackers.

- [ ] **Step 2: Run report-shape tests and confirm RED**

```bash
cd '/Users/ejazanwar/Documents/Gmail Automations'
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest \
  'Airtel Axis Statements/test_report_shape.py' \
  'Flipkart Axis Statements/test_report_shape.py' \
  'SBI Cashback Statements/tests/test_report_shape.py' -q
```

Expected: countdown assertions fail because generated reports contain no `Days left` lines.

- [ ] **Step 3: Preserve machine-readable waiver dates**

In each `decorate_*waiver_year` return mapping add:

```python
"deadline": end_date.date() if isinstance(end_date, datetime) else end_date,
```

In each `build_annual_fee_waiver_summary`, normalize the existing `as_of` once and return:

```python
"as_of": as_of.date() if isinstance(as_of, datetime) else as_of,
```

Pass `deadline=current["deadline"]` and `as_of=summary["as_of"]` to the fee-waiver `render_milestone` call.

- [ ] **Step 4: Pass cap deadlines from existing active windows**

For Airtel cap calls pass `deadline=end_date` and `as_of=today`. For Flipkart quarterly cap calls pass `deadline=quarter_end` and `as_of=as_of`. For SBI cap calls pass `deadline=end_date` and `as_of=today`. Do not parse the formatted Period text.

- [ ] **Step 5: Rebuild the three cashback reports**

Run each canonical `update_report.py` with the pinned interpreter from its own directory. Expected: each report is regenerated and contains countdown lines for every active cap and waiver milestone.

- [ ] **Step 6: Run the focused tests and verifier**

Run the Task 2 pytest command, then:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 verify_cashback_reports.py --scope cards
```

Expected: tests and card report verification pass.

- [ ] **Step 7: Commit cashback propagation**

Stage only the three canonical generators, their canonical tests, and their generated canonical reports. Do not stage numbered copies.

```bash
git commit -m "feat: show days left in cashback milestones"
```

### Task 3: Premium-card deadline propagation

**Files:**
- Modify: `/Users/ejazanwar/Documents/Gmail Automations/test_card_benefit_workflows.py`
- Modify: `/Users/ejazanwar/Documents/Gmail Automations/card_benefit_tracker.py`
- Regenerate canonical `benefit_tracker_report.md` under HSBC Live+, HDFC Diners Black Metal, and SBI New Card.

**Interfaces:**
- Consumes: Task 1 renderer contract.
- Produces: HDFC quarterly countdown and explicit Pending countdowns where verified fee/welcome dates do not exist.

- [ ] **Step 1: Write failing premium-report assertions**

In `test_hdfc_report_uses_progress_bars_for_fee_and_welcome`, add:

```python
assert report.count("- Days left: Pending") == 2
assert "- Days left: 91" in report
```

The test as-of date is July 1, 2026 and the Q3 deadline is September 30, 2026. In the HSBC operational report test, assert two Pending lines. Add a pending SBI report test asserting that fee and welcome milestones retain `Evidence: Pending` and `Days left: Pending`.

- [ ] **Step 2: Run premium tests and confirm RED**

```bash
cd '/Users/ejazanwar/Documents/Gmail Automations'
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest \
  test_card_benefit_workflows.ReportShapeTests -v
```

Expected: new countdown assertions fail.

- [ ] **Step 3: Pass as-of and supported deadlines**

In `build_report`, pass `as_of=as_of` to fee and welcome milestone calls with `deadline=None`. This deliberately renders Pending until an evidence-backed fee-year or welcome-window start is configured. Pass `deadline=quarter_end` and `as_of=as_of` to the quarterly bonus call.

Do not infer issuance dates from the first transaction or provisional statement cycle. Do not add unsupported config dates.

- [ ] **Step 4: Run premium tests and confirm GREEN**

Run the Task 3 unittest command. Expected: all report-shape tests pass.

- [ ] **Step 5: Rebuild premium reports without Gmail sync**

For each of HSBC Live+, HDFC Diners Black Metal, and SBI New Card, run its canonical `run_workflow.py --sync-source none` with the pinned interpreter. Expected: canonical reports regenerate; validation behavior remains unchanged.

- [ ] **Step 6: Commit premium propagation**

Stage only `card_benefit_tracker.py`, `test_card_benefit_workflows.py`, and the three canonical generated reports.

```bash
git commit -m "feat: show days left in benefit milestones"
```

### Task 4: Make the contract durable in all card skills

**Files:**
- Modify: `/Users/ejazanwar/.codex/skills/airtel-axis-cashback-tracker/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/flipkart-axis-cashback-tracker/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/sbi-cashback-tracker/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/hsbc-live-plus-benefit-tracker/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/hdfc-diners-black-metal-benefit-tracker/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/sbi-new-card-benefit-tracker/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/card-benefit-tracker-all-cards/SKILL.md`
- Modify: `/Users/ejazanwar/.codex/skills/aggregate-cashback-tracker/SKILL.md`

**Interfaces:**
- Documents the report contract implemented in Tasks 1–3.

- [ ] **Step 1: Add the individual-skill guardrail**

Append this sentence to the existing milestone guardrail in each individual skill:

```markdown
Every active milestone must also show calendar days left to its evidence-backed deadline; show `0` on the deadline day, elapsed days after an unmet deadline, `Not applicable — milestone met` when complete, and `Pending` when the deadline is not verified.
```

For SBI New Card, retain the variant gate and require Pending until the variant and deadline are proven.

- [ ] **Step 2: Add aggregate-skill preservation wording**

In both aggregate skills add:

```markdown
- Preserve card-level days-left lines from individual milestone blocks; do not recalculate deadlines in the aggregate report.
```

- [ ] **Step 3: Verify all skill contracts**

```bash
rg -l "days left|days-left" \
  /Users/ejazanwar/.codex/skills/{airtel-axis-cashback-tracker,flipkart-axis-cashback-tracker,sbi-cashback-tracker,hsbc-live-plus-benefit-tracker,hdfc-diners-black-metal-benefit-tracker,sbi-new-card-benefit-tracker,card-benefit-tracker-all-cards,aggregate-cashback-tracker}/SKILL.md
```

Expected: all eight skill files are listed.

### Task 5: Full regression and workspace hygiene

**Files:**
- Verify only; no planned production edits.

**Interfaces:**
- Confirms all individual and aggregate contracts remain valid.

- [ ] **Step 1: Run shared and workflow tests**

```bash
cd '/Users/ejazanwar/Documents/Gmail Automations'
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest tests/test_card_progress.py -q
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest test_card_benefit_workflows -v
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pytest \
  'Airtel Axis Statements/test_report_shape.py' \
  'Flipkart Axis Statements/test_report_shape.py' \
  'SBI Cashback Statements/tests/test_report_shape.py' -q
```

Expected: all focused suites pass.

- [ ] **Step 2: Rebuild aggregate reports without refreshing source data**

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 build_combined_cashback_report.py
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 build_combined_card_benefits_report.py
```

Expected: both canonical aggregate reports regenerate from individual reports.

- [ ] **Step 3: Run deterministic verification**

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 verify_cashback_reports.py --scope all
```

Expected: all individual and aggregate report checks pass, subject only to pre-existing freshness blockers that are reported verbatim.

- [ ] **Step 4: Inspect the exact diff and artifact hygiene**

```bash
git status --short
git diff --check
git diff -- card_progress.py tests/test_card_progress.py card_benefit_tracker.py test_card_benefit_workflows.py \
  'Airtel Axis Statements/update_report.py' \
  'Flipkart Axis Statements/update_report.py' \
  'SBI Cashback Statements/update_report.py'
```

Confirm no numbered duplicate, cache, temporary, database, Gmail source, or unrelated user file was changed or staged by this work.

- [ ] **Step 5: Commit aggregate outputs if they changed**

Stage only the two canonical aggregate Markdown reports and commit them separately:

```bash
git commit -m "docs: refresh card milestone countdown reports"
```

