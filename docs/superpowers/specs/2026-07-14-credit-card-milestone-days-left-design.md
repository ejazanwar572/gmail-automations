# Credit Card Milestone Days-Left Design

## Goal

Add a consistent calendar-day countdown to every active progress tracker in the six individual credit-card workflows without changing milestone amounts, evidence rules, or source-of-truth data.

## Scope

The change covers the canonical reports for Airtel Axis, Flipkart Axis, SBI Cashback, HSBC Live+, HDFC Diners Black Metal, and SBI New Card. It applies to statement-cycle cashback caps, quarterly caps or bonuses, welcome-spend windows, and annual fee-waiver periods wherever a real deadline is available. Combined cashback and benefit reports will consume the individual-card output and must not calculate an independent countdown.

Numbered duplicate files and unrelated expense, statement-parsing, Gmail-sync, dashboard, or redemption logic are out of scope.

## Day-Count Contract

The shared renderer receives an explicit milestone deadline and report as-of date. It compares calendar dates, not timestamps.

- Before the deadline: `Days left: N`, where `N = deadline - as_of`.
- On the deadline: `Days left: 0`.
- After the deadline while the milestone remains unmet: `Deadline passed: N days ago`.
- When the milestone is met: `Days left: Not applicable — milestone met`.
- When no reliable deadline exists: `Days left: Pending`.
- Provisional deadlines retain the existing evidence label; the countdown does not make provisional dates verified.

The deadline day therefore displays zero days left, as explicitly selected by the user. All generators pass date objects derived in their existing Asia/Kolkata reporting context. Tests inject `as_of` dates so results do not depend on the machine clock.

## Architecture

`card_progress.render_milestone()` remains the single Markdown formatting boundary. It gains optional `deadline` and `as_of` parameters and delegates countdown wording to a small pure helper in the same module. The helper validates and normalizes `date` and `datetime` inputs, returns deterministic wording, and does not infer deadlines from formatted period strings.

Each canonical report generator passes the deadline it already computes:

- Cashback-cap trackers pass the current statement or quarter end.
- Fee-waiver trackers pass the active waiver-year end.
- Welcome trackers derive the end from the configured start or issuance date plus the configured window only when that start date is supported by tracker evidence.
- Quarterly bonus trackers pass the current calendar-quarter end.
- Variant-gated or unconfigured milestones pass no deadline and remain pending.

No report post-processing is introduced. This keeps dates coupled to the milestone data and prevents wording drift among cards.

## Report Behavior

The countdown appears as a Markdown bullet inside every milestone block, adjacent to Period, Progress, Remaining, and Status. Existing 20-character progress bars, percentages, evidence states, milestone values, and recommendations remain unchanged.

Historical or closed summaries that are not rendered as active milestone blocks remain unchanged. A completed active block displays the not-applicable wording rather than a misleading zero-day countdown. An expired unmet block calls out elapsed days so stale or missed milestones are visible.

## Error Handling

Unsupported date values raise a clear `TypeError` in the shared helper during report generation. A missing deadline is a supported state and renders `Days left: Pending`. Existing evidence and freshness validation remains authoritative; countdown logic must not suppress stale, provisional, or reconciliation failures.

## Testing and Verification

Test-first coverage will establish the shared contract for a future deadline, deadline day, expired deadline, completed milestone, missing deadline, and datetime normalization. Generator-level report-shape tests will verify that each card supplies the correct deadline for its active milestone types.

Verification will run the focused shared-helper and report-shape tests, the existing card-benefit workflow tests, and the canonical report verifier. Reports will then be rebuilt without a Gmail refresh so the change remains presentation-only. The final review will confirm no numbered duplicate artifacts or unrelated files were modified.

## Success Criteria

Every active, date-bounded progress tracker across the six card reports shows a deterministic days-left line using the shared convention. Deadline-day output is zero, completed milestones are not presented as time remaining, unknown dates remain pending, existing milestone/evidence contracts are preserved, and focused plus aggregate verification passes.
