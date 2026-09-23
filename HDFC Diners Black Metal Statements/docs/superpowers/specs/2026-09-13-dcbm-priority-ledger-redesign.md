# HDFC DCBM Priority Ledger Redesign

Date: 2026-09-13
Status: Approved design
Approved direction: Direction A - Priority Ledger
Approved deployment access: Streamlit Community Cloud private sharing

## Objective

Redesign the HDFC Diners Club Black Metal rewards dashboard as a compact personal financial command center. Within 10-15 seconds, the owner must be able to identify the nearest actionable milestone, the additional spend and pace required, accelerated-reward headroom, available reward value, freshness/evidence quality, and the transactions or redemptions supporting the figures.

## Product boundary

- `dcbm_engine.py`, `benefits_config.json`, tracker outputs, and generated JSON remain the calculation and evidence sources of truth.
- The UI may prioritize, group, label, mask, and explain engine outputs. It must not independently recalculate reward, cap, eligibility, milestone, or date rules.
- Gmail access remains read-only. The explicit sync action remains available and keeps the current sync contract.
- No bank API, second transaction database, or production sample data is introduced.
- HDFC activity remains newest-first.
- The existing HDFC/HSBC card router remains available unless a verified compatibility problem requires a separately approved change.

## Security and access contract

The production app must use Streamlit Community Cloud private sharing. Viewer access is managed by email in Streamlit Cloud and is not implemented as an application password.

- Private sharing must be enabled and verified before the redesigned app is considered production-safe.
- The existing `DASHBOARD_PASSWORD` gate may remain temporarily during rollout, but it is not the chosen production access boundary and must not be presented as equivalent to private sharing.
- No secret, password, cookie, OAuth credential, message ID, or full booking/order reference may be committed, logged, rendered, or exported.
- DataFrames are constructed only from explicit privacy-safe dictionaries. Hiding a source column with `column_config` is prohibited.
- Transaction and redemption exports use explicit allowlists. Native DataFrame download is disabled when a sanitized application export is available.
- The card ending may be rendered as a masked last-four identifier because it is operationally useful; all other identifiers are omitted.

## Trust and freshness contract

The presentation layer must derive a trust envelope from existing engine output plus `sync_metadata.json`, `validation_report.json`, and the evidence metadata already present in tracker/config outputs.

Every screen must distinguish:

- **Data effective through**: latest represented transaction/evidence date.
- **Last successful sync**: timezone-aware timestamp converted to Asia/Kolkata and labelled IST.
- **Freshness**: Current, Aging, Stale, or Unknown using a documented threshold.
- **Evidence**: Confirmed, Estimated, Provisional, Mixed, or Unavailable.

The initial thresholds are:

- Current: successful sync age is at most 24 hours.
- Aging: more than 24 and at most 72 hours.
- Stale: more than 72 hours.
- Unknown: missing or invalid timestamp.

These labels do not alter calculations. Stale, unknown, unavailable, or invalid source states suppress imperative recommendations and explain that cached values are reference-only.

Timestamp parsing failure must render `Unknown`; it must never render `Live`. The interface must not claim real-time behavior.

## Information architecture

### Utility header

The header contains only card identity/router, masked last four, private-access indicator, sync action/state, and a compact theme control. The full freshness details live directly below it, not in an ambiguous timestamp pill.

### Trust strip

A full-width trust strip shows:

- freshness word and non-color icon;
- data effective date;
- last successful sync in IST;
- evidence quality;
- a disclosure with source and limitation details.

### Priority hero and Deadline Rail

The hero selects the nearest active unmet milestone from engine-provided milestone data. It shows:

- milestone name and benefit/consequence;
- deadline and days remaining;
- current progress and target;
- remaining eligible spend;
- daily and weekly pace;
- a labelled semantic progress indicator;
- a Deadline Rail representing elapsed and remaining time.

If all milestones are complete, the hero becomes a success summary and the next calendar cap reset becomes the primary operational date. If data is not decision-safe, the hero remains visible but changes from recommendation to factual reference wording.

### Capacity panel

The companion panel shows monthly accelerated points remaining, daily points remaining, and safe flight/hotel spend headroom. Numbers come directly from `dcbm_engine.py` output.

### Reward balance strip

The strip contains lifetime estimated/confirmed points, estimated currently available points, usable SmartBuy value, and effective reward rate. Each value displays its evidence qualifier.

### Milestone timeline

Active milestones appear before completed milestones. Completed milestones are moved into a collapsed `Achieved` disclosure rather than occupying equal visual space.

### Activity navigation

Four primary views remain:

1. Overview
2. Monthly history
3. Transactions
4. Redemptions

The Overview ends with recent decision-relevant activity. History, Transactions, and Redemptions retain the current functional coverage.

## Responsive behavior

- Desktop, at least 1100px: priority hero and capacity panel form a 2:1 row; balance metrics form a compact strip.
- Tablet, 640-1099px: hero is full width; capacity and balances use a two-column grid; milestones use two columns.
- Mobile, below 640px: all sections use one column; controls wrap without clipping; transaction and redemption tables become stacked records.
- Tabs remain readable without hiding their scroll affordance. Essential navigation does not depend on horizontal swiping.
- At 200% zoom, content remains operable without two-dimensional page scrolling.

## Table and export contract

Desktop transaction columns:

- Date
- Merchant
- Category
- Amount
- Base RP
- Accelerated RP
- Total RP
- Reward rate

Desktop redemption columns:

- Date
- Category
- Description with sensitive booking details removed or generalized
- Points burned
- Cash paid
- Total fare
- Value saved
- Redemption rate

Mobile records show date, merchant/category, amount, total points, and evidence first, with secondary fields in an expander.

CSV export uses the same privacy-safe fields and current filters. Message IDs, email subjects, full booking/order references, raw email dates, card numbers, application references, and hidden helper fields are never included.

## State model

The app has explicit states:

- **Idle**: normal data display and available sync action.
- **Syncing**: sync button disabled; persistent status text announces read-only Gmail retrieval.
- **Success**: refreshed data, IST timestamp, alert count, and non-blocking confirmation.
- **Partial/Aging/Stale**: cached values remain visible with limitations; decision recommendations are suppressed when unsafe.
- **Error**: last known safe snapshot remains visible when possible; sensitive exception text is logged server-side and the UI gives a concise recovery action.
- **Empty**: explains which source is absent and offers the permitted sync action; does not render a wall of zero metrics.

## Visual system

### Memorable idea

The Deadline Rail is the only distinctive visual motif. Other surfaces remain restrained and mostly divider-led.

### Light tokens

- `canvas`: `#F7F4EE`
- `surface`: `#FFFFFF`
- `surface-subtle`: `#F0ECE4`
- `text`: `#1A1613`
- `text-muted`: `#625B53`
- `border`: `#D8CFC2`
- `accent`: `#8A5712`
- `warning`: `#825000`
- `danger`: `#972F32`
- `success`: `#246B3D`
- `info`: `#205A7A`
- `focus`: `#075FCC`

### Dark tokens

- `canvas`: `#0B0F15`
- `surface`: `#151B24`
- `surface-subtle`: `#1D2530`
- `text`: `#F6F2EA`
- `text-muted`: `#B7B0A5`
- `border`: `#36404D`
- `accent`: `#E0B46C`
- `warning`: `#F2C067`
- `danger`: `#FF999B`
- `success`: `#83D3A0`
- `info`: `#7BC8EC`
- `focus`: `#A9D5FF`

Use the system font stack. Amounts use tabular numerals. Body text is at least 14px; metadata is at least 12px and used sparingly. Spacing follows 4, 8, 12, 16, 24, and 32px. Radii are limited to 6, 10, and 14px.

## Accessibility contract

- One programmatic H1 names the dashboard; H2/H3 headings follow the visual hierarchy.
- Native Streamlit controls are preferred and retain visible focus.
- Status always includes text and an icon; color is supplementary.
- Progress has an accessible label, current value, maximum, and textual equivalent.
- Touch targets are at least 44px where practical.
- Charts have adjacent text summaries and are not required to retrieve exact values.
- Light and dark text combinations meet WCAG 2.2 AA contrast.
- Motion is limited to Streamlit's native loading feedback and respects reduced-motion preferences.

## Implementation architecture

- `dcbm_engine.py`: unchanged calculation source, except a focused correctness fix may be made only when backed by existing benefit rules and tests.
- `dashboard_view_model.py`: reads engine output and evidence artifacts, creates trust/freshness state, selects the priority milestone, converts timestamps to IST, and emits only privacy-safe display/export rows.
- `dashboard_styles.py`: semantic light/dark tokens and minimal scoped CSS.
- `hdfc_dcbm_app.py`: Streamlit composition, widgets, routing, sync orchestration, and rendering only.
- Repository-root `../.streamlit/config.toml`: disables native DataFrame export after sanitized application exports exist, including when Community Cloud launches the root router.
- `tests/test_dashboard_view_model.py`: pure model, privacy, freshness, priority, sorting, and export tests.
- `tests/test_dashboard_app.py`: Streamlit AppTest coverage for structure, themes, states, filters, and routing.

No custom Streamlit component or third-party UI dependency is justified for this direction.

## Verification

Completion requires:

- existing engine and sync tests passing;
- new privacy/trust/view-model tests passing;
- Streamlit AppTest passing in light and dark themes;
- local startup without deprecation warnings;
- browser review at 1440x900, 768x1024, and 390x844;
- keyboard and visible-focus check;
- sanitized transaction and redemption export inspection;
- fresh unauthenticated-browser verification that Streamlit private sharing blocks the app before any financial data renders.

## Feature mapping

No existing feature is silently removed:

- Card routing stays in the utility header.
- Light/dark mode stays in the utility header.
- Sync and freshness move into the header and trust strip.
- Monthly/daily caps and flight/hotel headroom move into Capacity.
- Reward points, usable value, and effective rate move into the balance strip.
- Welcome, quarterly, and annual milestones move into the priority hero/timeline; completed items move to Achieved.
- Monthly history remains a dedicated view.
- Filters, merchant search, and export remain in Transactions.
- Redemption history and totals remain in Redemptions.
- Empty, stale, provisional, syncing, success, and error behavior become explicit states.
