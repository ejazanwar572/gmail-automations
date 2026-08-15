# HSBC Live+ Markdown Trackers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the HSBC fee-waiver and welcome tables with durable 20-character Markdown progress trackers.

**Architecture:** Add a pure progress-bar renderer to the shared card benefit module and use it only when rendering HSBC Live+ milestone sections. Preserve all existing calculations and report sections. Lock the behavior with focused unit tests, rebuild the report from existing fresh data, and update the HSBC skill contract.

**Tech Stack:** Python 3.12 standard library, `unittest`, Markdown, Codex skill validation.

## Global Constraints

- Keep existing spend, target, remaining, and status calculations unchanged.
- Use exactly 20 filled/empty block characters and cap visual/displayed progress at 100%.
- Preserve setup-safe output when a target is unavailable.
- Do not regenerate or redesign other card reports.
- Do not touch unrelated untracked files.

---

### Task 1: Progress rendering and HSBC report shape

**Files:**
- Modify: `test_card_benefit_workflows.py`
- Modify: `card_benefit_tracker.py`

**Interfaces:**
- Produces: `render_progress_bar(spend: float | int | None, target: float | int | None, width: int = 20) -> str`
- Consumes: existing `calculate_benefits()` output fields for annual fee and welcome milestones.

- [x] **Step 1: Write failing tests**

Add focused assertions for partial (`16.5%` and 3 filled blocks), completed (100%, 20 filled blocks), unavailable-target (`Progress unavailable`), and HSBC report sections that contain tracker bullets rather than metric tables.

- [x] **Step 2: Verify RED**

Run: `/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest test_card_benefit_workflows.ReportShapeTests -v`

Expected: failures because `render_progress_bar` and tracker-shaped milestone output do not exist.

- [x] **Step 3: Implement minimal renderer and section output**

Implement a pure helper that clamps progress to `[0, 1]`, rounds the filled cell count from the clamped ratio, formats one decimal percentage, and returns setup-safe text for missing/non-positive targets. Replace only the fee-waiver and welcome tables with the approved bar plus Progress, Remaining, and Status bullets.

- [x] **Step 4: Verify GREEN and regression suite**

Run the focused test command, then:

`/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest test_card_benefit_workflows -v`

Expected: all tests pass.

### Task 2: Generated report and reusable skill contract

**Files:**
- Modify: `HSBC Live Plus Statements/benefit_tracker_report.md` (generated)
- Modify: `/Users/ejazanwar/.codex/skills/hsbc-live-plus-benefit-tracker/SKILL.md`

**Interfaces:**
- Consumes: updated shared report renderer.
- Produces: future HSBC rebuilds that retain the tracker shape.

- [x] **Step 1: Rebuild without Gmail sync**

Run: `/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 "HSBC Live Plus Statements/run_workflow.py" --sync-source none`

Expected: validation passes and the report is regenerated.

- [x] **Step 2: Update skill contract**

Add one concise guardrail requiring 20-character plain-Markdown bars for fee-waiver and welcome progress whenever the report is generated or rebuilt.

- [x] **Step 3: Validate skill and final artifacts**

Run the skill-creator `quick_validate.py` against the HSBC skill directory, rerun `HSBC Live Plus Statements/validate_statements.py`, and inspect the generated report for both progress bars, percentages, amounts, remaining values, and statuses.

- [x] **Step 4: Review diff and keep unrelated files untouched**

Run `git diff -- card_benefit_tracker.py test_card_benefit_workflows.py "HSBC Live Plus Statements/benefit_tracker_report.md" docs/superpowers/plans/2026-07-13-hsbc-live-plus-markdown-trackers.md` and inspect the external skill diff separately.
