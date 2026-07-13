# Individual Card Progress Trackers Design

## Goal

Standardize meaningful milestone tracking across every individual credit-card report with the same compact 20-character plain-Markdown progress bars already used by HSBC Live+, while preserving each card workflow's existing calculations, evidence rules, and report structure.

## Scope

Apply progress trackers only to individual card reports. Combined cashback reports, combined benefit reports, and dashboards remain unchanged.

The rollout covers:

- Airtel Axis: active annual fee-waiver progress and active monthly cashback-category caps.
- Flipkart Axis: active annual fee-waiver progress and active quarterly cashback caps.
- SBI Cashback: active annual fee-waiver progress and active monthly online/offline cashback caps.
- HDFC Diners Black Metal: active annual fee-waiver, welcome-spend, and quarterly-bonus progress.
- HSBC Live+: migrate the existing fee-waiver and welcome-benefit bars to the shared renderer without changing their visible contract.
- SBI card ending 3366: render disabled or pending milestones only until the exact product variant and official numeric targets are confirmed. Reward recommendations remain disabled.

Only milestones with an official numeric target and sufficient workflow evidence receive an active progress bar. Historical completed periods remain in compact tables unless an existing report already presents them differently.

## Architecture

Create one small shared Markdown presentation utility for milestone progress. It will format already-calculated values; it will not decide transaction eligibility, calculate spend, interpret statements, or encode card benefit rules.

Each card's existing report generator remains responsible for:

- Selecting eligible transactions and exclusions.
- Calculating spend, cashback, caps, fee-waiver years, welcome windows, and quarterly periods.
- Applying freshness and reconciliation gates.
- Supplying evidence status and card-specific explanatory text.

This boundary centralizes visual consistency without forcing materially different card models into a shared calculation engine.

## Shared Renderer Contract

The renderer accepts:

- A label.
- Current numeric value.
- Numeric target.
- Unit or amount formatter.
- Optional measurement period.
- Evidence state: `verified`, `provisional`, `stale`, or `pending`.
- Optional supporting values such as qualifying spend or an exceeded amount.

Active output uses exactly 20 filled and empty characters, followed by a one-decimal percentage:

```markdown
`███░░░░░░░░░░░░░░░░░ 16.5%`

- Progress: INR 3,301.13 of INR 20,000.00
- Remaining: INR 16,698.87
- Status: In progress
```

The renderer follows these rules:

- Visual fill and displayed percentage are capped at 100%.
- Reaching the target shows `Met`; exceeding it shows the excess separately.
- Zero targets and unavailable targets never cause division errors.
- Pending trackers do not imply zero progress.
- Provisional or stale states are explicit and cannot look verified.
- Output is plain Markdown with no raw HTML.

## Data and Evidence Rules

- Fee-waiver bars use the eligible annual spend already calculated by each card after its exclusions.
- Cashback-cap bars measure cashback earned against the applicable cap. Qualifying spend remains visible as supporting context.
- Welcome and quarterly-bonus bars use eligible spend inside the workflow's defined time window.
- Live Gmail and parsed statement inputs remain subject to each workflow's existing freshness and reconciliation gate.
- A failed freshness gate blocks a trusted current-progress claim and renders the tracker stale or blocked according to the existing report contract.
- Missing fee or transaction evidence is not treated as definitive zero activity.
- No unofficial target is added merely to make a visual tracker possible.

## Report Integration

Each report keeps its current filename, transaction detail, historical tables, evidence notes, recommendations, and source notes. The new bars replace or augment only active-period summary rows where visual progress materially improves readability.

Card skills will be updated to require the standardized tracker contract when their reports are generated or rebuilt. Existing output-link and full-report response rules remain unchanged.

## Rollout Order

1. Add and test the shared Markdown progress renderer.
2. Migrate HSBC Live+ as the reference implementation and confirm no visible regression.
3. Add the HDFC Diners Black Metal milestone trackers.
4. Add active fee-waiver and cashback-cap trackers to Airtel Axis, Flipkart Axis, and SBI Cashback.
5. Add pending-only rendering for SBI card 3366 without bypassing its variant gate.
6. Rebuild and validate every affected individual report.

## Verification

Focused tests will cover:

- Exactly 20 bar characters.
- Partial, zero, met, and exceeded states.
- Correct percentage, remaining amount, and exceeded amount.
- Missing or zero targets.
- Verified, provisional, stale, and pending evidence states.
- Card-specific targets, periods, and supporting spend values.
- Preservation of existing transaction tables, historical sections, recommendations, and source notes.
- Absence of raw HTML.
- No generated changes to combined reports or dashboards.

Implementation will use test-first changes for the shared renderer and focused report-shape regressions for each card. Final verification will run every affected card's existing validation and report-generation workflow.

## Non-goals

- No combined-report or dashboard changes.
- No shared cross-card calculation engine.
- No changes to reward rates, eligibility, exclusions, statement periods, or reconciliation policy.
- No activation of SBI 3366 rewards before official variant confirmation.
- No broad refactor of the existing card workflow structure.
- No cleanup or overwrite of unrelated user files.
