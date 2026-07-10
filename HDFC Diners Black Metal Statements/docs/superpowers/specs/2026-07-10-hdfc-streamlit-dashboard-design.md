# HDFC Diners Black Metal Streamlit Dashboard Design

Date: 2026-07-10
Status: Approved design, pending spec review

## Objective

Build a small local Streamlit dashboard for HDFC Diners Black Metal card ending 2360. The dashboard will make milestone progress, reward value, and planned-spend decisions interactive while preserving the existing validated tracker files as the source of truth.

## Product Boundary

The dashboard is a read-only presentation and projection layer inside `HDFC Diners Black Metal Statements`. It must not query or mutate Gmail, change transaction records, or create a second transaction database. The existing workflow remains responsible for Gmail sync, parsing, freshness validation, and report generation.

## Data Sources

The dashboard reads:

- `gmail_alerts.json` for tracked transactions.
- `sync_metadata.json` for freshness, query, connector evidence, counts, and cached total.
- `validation_report.json` for the reconciliation gate.
- `benefits_config.json` for benefit rules, targets, dates, and source links.
- `statements_data.json` when statement-derived evidence becomes available.

Optional manual values such as actual posted reward points and membership claim status will live in one small dashboard-state JSON file. This file must not override transaction totals or freshness status.

## Trust Model

The dashboard must visibly distinguish:

- Confirmed: supported by validated tracker or statement evidence.
- Estimated: calculated from transaction amount and configured reward rules.
- Uncertain: missing MCC, merchant category, posting data, or eligibility evidence.
- Stale: freshness validation failed or connector evidence is missing.

When `validation_report.json` is not OK, trusted recommendations and milestone-completion claims must be disabled. The dashboard may display cached data only with a prominent stale-data warning.

## Configuration Additions

Extend `benefits_config.json` with:

- Card issuance or upgrade date.
- Welcome-period end date derived from 90 days.
- Welcome target of INR 150,000 net eligible retail spend.
- Calendar-quarter milestone target of INR 400,000.
- Quarterly bonus of 10,000 reward points.
- Annual fee-waiver target of INR 800,000.
- Membership names and claim states for Club Marriott, Amazon Prime, and Swiggy One.
- Reward rates and caps required by the projection engine.

If issuance date is not proven, the welcome deadline must be labelled provisional and the UI must request evidence rather than inventing a date.

## Dashboard Layout

### Status Header

Show card ending, freshness timestamp, latest transaction date, validation state, current provisional statement cycle, and evidence warnings.

### Progress Section

Display three native progress bars:

1. Welcome benefit: eligible net retail spend toward INR 150,000, amount remaining, percentage, days remaining, and deadline.
2. Quarterly milestone: eligible spend in the current calendar quarter toward INR 400,000, amount remaining, and projected 10,000-point unlock.
3. Annual fee waiver: eligible spend in the applicable 12-month period toward INR 800,000 and amount remaining.

Progress values must be clamped visually to 100%, while the underlying amount may show overspend beyond the target.

### Welcome Membership Checklist

Show Club Marriott, Amazon Prime, and Swiggy One as locked, unlocked, claimed, or evidence needed. The app must not infer claimed status merely because the spend target was met.

### Spend Shifter

Provide controls for:

- Planned additional spend.
- Spend category: regular, SmartBuy flight, SmartBuy hotel, weekend dining, voucher, or uncertain/excluded.
- Portal markup or processing fee.
- Intended redemption method.

Update projected base points, accelerated points, net value, welcome progress, quarterly progress, and annual-waiver progress without changing tracker files.

The shifter must clearly label calculations as projections. Excluded or uncertain categories must not be presented as confirmed reward earning.

### Reward Value Comparison

For an estimated or manually entered point balance, compare:

- SmartBuy flight/hotel value at up to INR 1 per point.
- Airmiles at up to 1 mile per point.
- Products/vouchers at up to INR 0.50 per point.
- Cashback at up to INR 0.30 per point.

Show the 70% SmartBuy booking-payment limit and avoid presenting nominal value as guaranteed realized value.

### Reward Reconciliation

Show estimated base points, estimated accelerated points, expected posting period when known, actual posted points if manually supplied, and the difference. Missing actual points should display as pending, not zero.

### Transaction Review

Display included transactions and a separate exceptions view for declined, reversed, refunded, duplicate, or uncertain transactions when evidence is available. Preserve original merchant names and dates.

## Markdown Report Changes

Keep `benefit_tracker_report.md` as the portable report. Replace the welcome table with a generated text progress bar and concise deadline/action text. Replace the generic zero-value benefit table with reward-value estimates, milestone progress, and a pointer to the Streamlit dashboard.

The Markdown report remains non-interactive; the shifter exists only in Streamlit.

## Architecture

- `dashboard.py`: Streamlit composition and widgets only.
- `dashboard_model.py`: pure loading, validation, progress, projection, and redemption calculations.
- `dashboard_state.json`: optional manual posted-points and claim-state inputs.
- Existing tracker modules: unchanged source-of-truth calculations unless a focused shared fix is required.

The calculation module must not import Streamlit, enabling fast unit tests.

## Error Handling

- Missing file: show which source is missing and disable dependent panels.
- Invalid JSON: show a non-sensitive error without crashing the entire app.
- Validation failure: show cached values as stale and disable trusted recommendations.
- Missing issuance date: show provisional welcome progress without a definitive countdown.
- Missing MCC/category: label reward eligibility estimated or uncertain.
- Negative/refund transactions: net them according to tracker evidence; do not silently count them as spend.

## Verification

Unit tests must cover:

- Welcome percentage, remaining spend, and 90-day boundary.
- Calendar-quarter selection and INR 400,000 crossing.
- Annual INR 800,000 waiver progress.
- Progress clamping above target.
- Refund and reversal exclusion or netting.
- Reward rounding per INR 150.
- SmartBuy cap handling where configured.
- Redemption-value comparison.
- Portal markup reducing net value.
- Stale validation disabling recommendations.
- Missing actual points rendering as pending.

Completion verification requires unit tests, a Streamlit startup check, and a browser smoke test of the progress bars, shifter, stale-state warning, and responsive layout.

## Out of Scope

- Direct Gmail access from Streamlit.
- Editing tracker transactions in the dashboard.
- Automatic card routing across all cards.
- Hosting on the public internet.
- Treating Reddit anecdotes as benefit rules.
- Confirming reward eligibility without MCC or posted statement evidence.

## Success Criteria

The user can open one local dashboard and immediately see what is achieved, what remains, what expires next, and how a planned spend changes points and milestone outcomes. All trusted figures trace back to validated tracker files, and every projection or uncertain eligibility judgment is visibly labelled.
