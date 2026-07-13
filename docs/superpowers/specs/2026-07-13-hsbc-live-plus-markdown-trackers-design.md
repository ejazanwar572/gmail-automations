# HSBC Live+ Markdown Trackers Design

## Goal

Replace the fee-waiver and welcome-benefit summary tables in the generated HSBC Live+ Markdown report with compact tracker views that make progress immediately visible.

## Scope

- Keep the existing spend, target, remaining, and status calculations unchanged.
- Render each milestone as a 20-character plain-Markdown progress bar using filled and empty block characters.
- Show percentage, tracked spend versus target, remaining amount, and status beside each tracker.
- Cap the visual bar and displayed percentage at 100% when spending exceeds a target.
- Preserve setup-safe output when a target is unavailable.
- Update the shared report generator so future HSBC workflow refreshes preserve the format.
- Add focused regression tests for partial, completed, and unavailable-target states.
- Update the HSBC workflow skill to require the tracker format when generating or rebuilding its report.

## Output Shape

Each section will use this structure:

```markdown
## 2. Fee and Waiver Tracker

`███░░░░░░░░░░░░░░░░░ 16.5%`

- Progress: INR 3,301.13 of INR 20,000.00
- Remaining: INR 16,698.87
- Status: In progress
```

The fee-waiver and welcome-benefit sections remain separate because their targets and time horizons differ.

## Data Flow

`benefits_config.json` and parsed transactions continue to feed the existing summary calculations. A small rendering helper converts the calculated spend and target into the Markdown bar. `run_workflow.py` continues to rebuild `benefit_tracker_report.md` through the existing shared generator.

## Verification

- Run the new focused report-shape tests and observe the expected failure before implementation.
- Run the focused tests after implementation and then the existing card-benefit workflow tests.
- Rebuild the HSBC report with `--sync-source none` so Gmail data is not re-synced.
- Run HSBC validation and inspect the generated tracker sections.
- Validate the updated skill file using the skill validation tooling available in the skill-creator package.

## Non-goals

- No Streamlit or HTML dashboard.
- No changes to cashback, fee-waiver, or welcome-benefit calculations.
- No regeneration or redesign of other card reports.
- No cleanup of unrelated existing untracked files.
