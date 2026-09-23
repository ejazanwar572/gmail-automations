# HDFC DCBM Priority Ledger Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current HDFC Diners Black Metal card grid with the approved Priority Ledger command center while closing the public-data, privacy, dark-theme, freshness, accessibility, and responsive-layout gaps.

**Architecture:** Preserve `dcbm_engine.py` as the reward and milestone calculation source. Add a pure `dashboard_view_model.py` adapter that combines engine output with validation/evidence metadata, selects the priority milestone, converts timestamps to IST, and emits only privacy-safe presentation/export records; keep Streamlit composition in `hdfc_dcbm_app.py` and semantic visual tokens in `dashboard_styles.py`. Production access is enforced by Streamlit Community Cloud private sharing, with verification that unauthenticated viewers cannot reach app content.

**Tech Stack:** Python 3.12.2, Streamlit 1.56.0, pandas 2.x, standard-library `dataclasses`, `datetime`, `enum`, `csv`, `io`, `json`, `pathlib`, `zoneinfo`, `unittest`, Streamlit AppTest, Playwright browser verification.

**Spec:** `docs/superpowers/specs/2026-09-13-dcbm-priority-ledger-redesign.md`

## Global Constraints

- Work in an isolated git worktree created with `superpowers:using-git-worktrees` before modifying product code.
- Use `/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3` for Python commands.
- Preserve `dcbm_engine.py`, `benefits_config.json`, generated JSON, tracker reports, and validation artifacts as the source of truth.
- Do not independently calculate reward, cap, eligibility, milestone, or date rules in Streamlit rendering code.
- Do not mutate Gmail beyond the existing read-only sync path.
- Never commit or render passwords, OAuth credentials, cookies, tokens, Gmail message IDs, full booking/order references, application references, or unmasked card numbers.
- Construct display and export records from explicit allowlists; hiding a source DataFrame column is not privacy protection.
- Preserve newest-first transaction ordering.
- Display data-effective and last-successful-sync times in Asia/Kolkata and label them IST.
- Preserve light/dark modes, sync, monthly and daily caps, flight/hotel headroom, rewards balance/value/rate, all three milestones, monthly history, transaction filtering/search/export, redemption history/totals, card routing, and all explicit system states.
- Use native Streamlit widgets and `width="stretch"`; do not introduce a custom component or third-party UI library.
- Keep `unsafe_allow_html` limited to static, developer-authored structure and styles; escape every dynamic string that reaches HTML.
- Do not change Streamlit Cloud sharing settings until the user confirms the final permission-changing action at action time.

## File map

- Create `dashboard_view_model.py`: trust/freshness/evidence mapping, IST formatting, priority selection, privacy-safe records, and sanitized CSV exports.
- Create `dashboard_styles.py`: complete semantic token maps and minimal stable CSS.
- Modify `dcbm_engine.py`: provide daily and weekly required pace for every active milestone, without changing eligibility or target rules.
- Rewrite `hdfc_dcbm_app.py`: small composition functions for header, trust strip, priority hero, capacity, balances, milestones, history, transactions, redemptions, and state handling.
- Create repository-root `../.streamlit/config.toml`: disable native DataFrame export after sanitized app exports are present, including root-router deployments.
- Modify repository-root `../requirements.txt`: pin the locally verified Streamlit minor version and a compatible pandas major range.
- Create `tests/test_dashboard_view_model.py`: pure privacy, trust, freshness, ordering, priority, and CSV tests.
- Create `tests/test_dashboard_app.py`: AppTest coverage for structure, themes, states, filtering, routing, and secret absence.
- Modify `tests/test_dcbm_engine.py`: required-pace regression coverage.
- Modify `README.md`: local use, trust labels, sanitized exports, and private-sharing deployment runbook.

---

### Task 1: Privacy-Safe Trust and Activity View Model

**Files:**
- Create: `dashboard_view_model.py`
- Create: `tests/test_dashboard_view_model.py`

**Interfaces:**
- Consumes: `dcbm_engine.compute_all_dashboard_data(card_dir: Path, as_of: date | None) -> dict[str, Any]`, `sync_metadata.json`, `validation_report.json`, and `dashboard_summary.json`.
- Produces: `FreshnessState`, `EvidenceState`, `TrustEnvelope`, `SafeTransactionRow`, `SafeRedemptionRow`, `SafeHistoryRow`, `DashboardViewModel`, `build_dashboard_view_model()`, `transaction_csv_bytes()`, and `redemption_csv_bytes()`.

- [ ] **Step 1: Write failing privacy and timezone tests**

Create `tests/test_dashboard_view_model.py` with temporary fixture files and these assertions:

```python
import csv
import io
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import dashboard_view_model as vm


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


class DashboardViewModelTests(unittest.TestCase):
    def test_sync_timestamp_is_rendered_in_ist(self):
        value = vm.format_ist_timestamp("2026-09-12T13:52:48+00:00")
        self.assertEqual("12 Sep 2026, 19:22 IST", value)

    def test_invalid_timestamp_is_unknown_not_live(self):
        self.assertEqual("Unknown", vm.format_ist_timestamp("not-a-date"))

    def test_safe_rows_omit_identifiers_and_generalize_redemption_description(self):
        tx = vm.safe_transaction_row({
            "date": "2026-09-12",
            "merchant": "Example merchant",
            "category": "General Retail",
            "amount": 1000,
            "base_points": 30,
            "raw_accelerated_points": 0,
            "total_multiplier": 1,
            "reward_rate_percent": 3.33,
            "message_id": "private-message-id",
            "subject": "private subject",
        })
        redemption = vm.safe_redemption_row({
            "date": "2026-09-11",
            "type": "SmartBuy Flight",
            "description": "Private route and passenger detail",
            "order_reference": "PRIVATE-ORDER-REFERENCE",
            "message_id": "private-redemption-message",
            "points_redeemed": 5000,
            "cash_paid": 2500,
            "total_fare": 7500,
            "value_saved_inr": 5000,
            "redemption_rate": 1.0,
        })
        self.assertNotIn("message_id", tx.as_dict())
        self.assertNotIn("subject", tx.as_dict())
        self.assertNotIn("order_reference", redemption.as_dict())
        self.assertEqual("SmartBuy flight redemption", redemption.description)

    def test_csv_exports_use_exact_allowlists(self):
        tx_payload = vm.transaction_csv_bytes((vm.SafeTransactionRow(
            date="2026-09-12", merchant="Example", category="General Retail",
            amount=1000.0, base_rp=30, accelerated_rp=0, total_rp=30,
            reward_rate_percent=3.33, evidence="Estimated",
        ),))
        headers = next(csv.reader(io.StringIO(tx_payload.decode("utf-8"))))
        self.assertEqual(list(vm.TRANSACTION_EXPORT_COLUMNS), headers)
        self.assertNotIn("Message ID", headers)
        self.assertNotIn("Order Reference", headers)
```

- [ ] **Step 2: Run the focused tests and verify the module is absent**

Run from `HDFC Diners Black Metal Statements`:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest tests.test_dashboard_view_model -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dashboard_view_model'`.

- [ ] **Step 3: Implement enums, records, and allowlists**

Create `dashboard_view_model.py` with these public types and constants:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo
import csv
import json

import dcbm_engine

IST = ZoneInfo("Asia/Kolkata")
TRANSACTION_EXPORT_COLUMNS = (
    "Date", "Merchant", "Category", "Amount", "Base RP",
    "Accelerated RP", "Total RP", "Reward Rate %", "Evidence",
)
REDEMPTION_EXPORT_COLUMNS = (
    "Date", "Category", "Description", "Points Burned", "Cash Paid",
    "Total Fare", "Value Saved", "Redemption Rate", "Evidence",
)


class FreshnessState(StrEnum):
    CURRENT = "Current"
    AGING = "Aging"
    STALE = "Stale"
    UNKNOWN = "Unknown"


class EvidenceState(StrEnum):
    CONFIRMED = "Confirmed"
    ESTIMATED = "Estimated"
    PROVISIONAL = "Provisional"
    MIXED = "Mixed"
    UNAVAILABLE = "Unavailable"


@dataclass(frozen=True)
class SafeTransactionRow:
    date: str
    merchant: str
    category: str
    amount: float
    base_rp: int
    accelerated_rp: int
    total_rp: int
    reward_rate_percent: float
    evidence: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SafeRedemptionRow:
    date: str
    category: str
    description: str
    points_burned: int
    cash_paid: float
    total_fare: float
    value_saved: float
    redemption_rate: float
    evidence: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SafeHistoryRow:
    month: str
    total_spend: float
    base_rp: int
    accelerated_rp: int
    cap_used_percent: float
    cap_left: int
    total_rp: int
    smartbuy_value: float
    smartbuy_transactions: str
```

- [ ] **Step 4: Implement timezone and privacy helpers**

Add exact behavior:

```python
def parse_timestamp(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def format_ist_timestamp(value: object) -> str:
    parsed = parse_timestamp(value)
    return "Unknown" if parsed is None else parsed.astimezone(IST).strftime("%d %b %Y, %H:%M IST")


def safe_transaction_row(item: dict[str, Any]) -> SafeTransactionRow:
    base = int(item.get("base_points", 0) or 0)
    accelerated = int(item.get("raw_accelerated_points", 0) or 0)
    return SafeTransactionRow(
        date=str(item.get("date", "Unknown")),
        merchant=str(item.get("merchant", "Unknown merchant")),
        category=str(item.get("category", "Unclassified")),
        amount=float(item.get("amount", 0) or 0),
        base_rp=base,
        accelerated_rp=accelerated,
        total_rp=base + accelerated,
        reward_rate_percent=float(item.get("reward_rate_percent", 0) or 0),
        evidence="Estimated",
    )


def safe_redemption_row(item: dict[str, Any]) -> SafeRedemptionRow:
    category = str(item.get("type", "Reward redemption"))
    description = "SmartBuy flight redemption" if "flight" in category.lower() else (
        "SmartBuy hotel redemption" if "hotel" in category.lower() else "Reward points redemption"
    )
    return SafeRedemptionRow(
        date=str(item.get("date", "Unknown")), category=category, description=description,
        points_burned=int(item.get("points_redeemed", 0) or 0),
        cash_paid=float(item.get("cash_paid", 0) or 0),
        total_fare=float(item.get("total_fare", 0) or 0),
        value_saved=float(item.get("value_saved_inr", 0) or 0),
        redemption_rate=float(item.get("redemption_rate", 0) or 0),
        evidence="Confirmed",
    )
```

- [ ] **Step 5: Implement sanitized CSV serialization**

Map dataclass fields to the exact human-readable allowlists and write with `csv.DictWriter(extrasaction="raise")`. Return UTF-8 bytes. Do not accept arbitrary dictionaries at this boundary.

- [ ] **Step 6: Run the focused tests**

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest tests.test_dashboard_view_model -v
```

Expected: PASS.

- [ ] **Step 7: Commit the privacy boundary**

```bash
git add 'dashboard_view_model.py' 'tests/test_dashboard_view_model.py'
git commit -m 'feat(dcbm): add privacy-safe dashboard view model'
```

---

### Task 2: Trust Envelope, Priority Selection, and Engine-Owned Pace

**Files:**
- Modify: `dcbm_engine.py:459-615`
- Modify: `tests/test_dcbm_engine.py`
- Modify: `dashboard_view_model.py`
- Modify: `tests/test_dashboard_view_model.py`

**Interfaces:**
- Consumes: engine milestone dictionaries and sync/validation/evidence artifacts.
- Produces: `dcbm_engine.compute_required_pace()`, milestone `daily_runrate_needed` and `weekly_runrate_needed` fields, `TrustEnvelope`, `PriorityMilestone`, and complete `build_dashboard_view_model()`.

- [ ] **Step 1: Add failing pace tests to the engine suite**

```python
def test_required_pace_returns_daily_and_weekly_values(self):
    self.assertEqual(
        {"daily": 1000.0, "weekly": 7000.0},
        dcbm_engine.compute_required_pace(30000.0, 30),
    )

def test_required_pace_is_zero_when_met_or_expired(self):
    self.assertEqual({"daily": 0.0, "weekly": 0.0}, dcbm_engine.compute_required_pace(0, 30))
    self.assertEqual({"daily": 0.0, "weekly": 0.0}, dcbm_engine.compute_required_pace(30000, 0))
```

Extend `test_complete_dashboard_data_loading` to require daily and weekly pace keys for welcome, quarterly, and annual milestones, and `reward_rate_percent` on every processed transaction.

- [ ] **Step 2: Run the new engine tests and verify failure**

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest tests.test_dcbm_engine.DcbmEngineTests.test_required_pace_returns_daily_and_weekly_values -v
```

Expected: FAIL because `compute_required_pace` does not exist.

- [ ] **Step 3: Implement required pace in the engine**

Add beside the existing milestone helpers:

```python
def compute_required_pace(remaining: float, days_left: int) -> Dict[str, float]:
    if remaining <= 0 or days_left <= 0:
        return {"daily": 0.0, "weekly": 0.0}
    daily = round(remaining / days_left, 2)
    return {"daily": daily, "weekly": round(daily * 7, 2)}
```

Call this helper for each milestone and expose:

```python
"daily_runrate_needed": pace["daily"],
"weekly_runrate_needed": pace["weekly"],
```

Do not alter target, period, eligibility, or spend calculations.

In `process_transactions()`, add the existing nominal display rate to the engine-owned record so the view model never calculates it:

```python
"reward_rate_percent": round(cat.total_multiplier * 3.33, 1),
```

- [ ] **Step 4: Add failing view-model tests for freshness and priority**

Cover all boundaries with a fixed aware `now`:

```python
def test_freshness_boundaries(self):
    now = datetime(2026, 9, 13, 12, tzinfo=timezone.utc)
    self.assertEqual(vm.FreshnessState.CURRENT, vm.classify_freshness("2026-09-12T12:00:00Z", now))
    self.assertEqual(vm.FreshnessState.AGING, vm.classify_freshness("2026-09-11T12:00:00Z", now))
    self.assertEqual(vm.FreshnessState.STALE, vm.classify_freshness("2026-09-09T12:00:00Z", now))
    self.assertEqual(vm.FreshnessState.UNKNOWN, vm.classify_freshness(None, now))

def test_priority_prefers_nearest_active_unmet_milestone(self):
    milestones = {
        "welcome": {"met": True, "days_left": 10, "remaining": 0, "target": 150000, "spend": 160000},
        "quarterly": {"met": False, "days_left": 17, "remaining": 85000, "target": 400000, "spend": 315000,
                      "daily_runrate_needed": 5000, "weekly_runrate_needed": 35000, "bonus_points": 10000},
        "annual_waiver": {"met": False, "days_left": 280, "remaining": 475000, "target": 800000, "spend": 325000,
                          "daily_runrate_needed": 1696.43, "weekly_runrate_needed": 11875.01, "fee_amount": 10000},
    }
    selected = vm.select_priority_milestone(milestones)
    self.assertEqual("Quarterly bonus", selected.name)
    self.assertEqual(17, selected.days_left)
```

- [ ] **Step 5: Implement trust and priority dataclasses**

```python
@dataclass(frozen=True)
class TrustEnvelope:
    freshness: FreshnessState
    evidence: EvidenceState
    decision_safe: bool
    data_effective_date: str
    last_successful_sync_ist: str
    source_label: str
    limitation: str


@dataclass(frozen=True)
class PriorityMilestone:
    key: str
    name: str
    consequence: str
    current: float
    target: float
    remaining: float
    progress_percent: float
    deadline: str
    days_left: int
    daily_pace: float
    weekly_pace: float
    evidence: EvidenceState
```

`classify_freshness()` uses the approved 24-hour and 72-hour thresholds. `decision_safe` is true only when validation is explicitly OK, freshness is Current or Aging, and evidence is not Unavailable. `select_priority_milestone()` ignores completed milestones, sorts remaining candidates by valid non-negative `days_left`, and uses calendar cap reset only when every milestone is complete.

- [ ] **Step 6: Assemble the full DashboardViewModel**

Define:

Implement the immutable `DashboardViewModel` with these fields: `card_name: str`, `masked_card_ending: str`, `as_of: str`, `trust: TrustEnvelope`, `priority: PriorityMilestone`, `caps: dict[str, Any]`, `points: dict[str, Any]`, `active_milestones: tuple[dict[str, Any], ...]`, `achieved_milestones: tuple[dict[str, Any], ...]`, `transactions: tuple[SafeTransactionRow, ...]`, `redemptions: tuple[SafeRedemptionRow, ...]`, and `monthly_history: tuple[SafeHistoryRow, ...]`.

Implement this exact callable interface: `build_dashboard_view_model(card_dir: Path, *, as_of: date | None = None, now: datetime | None = None, engine_data: dict[str, Any] | None = None) -> DashboardViewModel`.

Implementation rules:

1. Call `compute_all_dashboard_data()` exactly once when `engine_data` is absent.
2. Load JSON with a helper that returns an explicit missing/invalid state; do not silently convert malformed validation evidence into success.
3. Preserve the engine transaction order and assert newest-first in tests.
4. Convert all transactions, redemptions, and history aggregates through safe row functions before returning.
5. Build history drilldowns by filtering `SafeTransactionRow` values by month; never retain the raw nested `transactions` value from engine history.
6. Convert evidence sources into generic labels such as `Statement evidence`, `Gmail alert tracking`, or `Configuration proxy`; never propagate application references or message identifiers.
7. Keep raw source dictionaries local to the builder; never store them on `DashboardViewModel`.

- [ ] **Step 7: Run focused and full engine/model tests**

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest tests.test_dcbm_engine tests.test_dashboard_view_model -v
```

Expected: PASS.

- [ ] **Step 8: Commit engine pacing and trust logic**

```bash
git add 'dcbm_engine.py' 'dashboard_view_model.py' 'tests/test_dcbm_engine.py' 'tests/test_dashboard_view_model.py'
git commit -m 'feat(dcbm): add evidence-aware priority planning'
```

---

### Task 3: Semantic Theme System and Stable App Shell

**Files:**
- Create: `dashboard_styles.py`
- Modify: `hdfc_dcbm_app.py`
- Create: `tests/test_dashboard_app.py`
- Modify: `../requirements.txt`

**Interfaces:**
- Consumes: `dashboard_view_model.build_dashboard_view_model()`.
- Produces: `ThemeTokens`, `theme_tokens(mode)`, `render_theme_css(mode)`, `render_header(model)`, `render_trust_strip(model)`, and `main(model: DashboardViewModel | None = None)`.

- [ ] **Step 1: Pin verified framework versions**

Change root `requirements.txt` to:

```text
streamlit==1.56.0
pandas>=2.0,<3.0
requests>=2.31.0
google-auth>=2.20.0
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.90.0
```

- [ ] **Step 2: Add failing complete-token tests**

In `tests/test_dashboard_app.py`:

```python
import unittest
import dashboard_styles


class DashboardStyleTests(unittest.TestCase):
    def test_light_and_dark_define_the_same_semantic_tokens(self):
        light = dashboard_styles.theme_tokens("Light")
        dark = dashboard_styles.theme_tokens("Dark")
        self.assertEqual(set(light), set(dark))
        self.assertIn("accent", light)
        self.assertIn("focus", dark)

    def test_css_has_visible_focus_and_reduced_motion_rules(self):
        css = dashboard_styles.render_theme_css("Dark")
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertNotIn("fonts.googleapis.com", css)
```

- [ ] **Step 3: Implement semantic tokens and scoped CSS**

Create `dashboard_styles.py` with immutable light/dark dictionaries copied exactly from the approved spec. `theme_tokens()` must raise `ValueError` for an unknown mode. `render_theme_css()` returns static CSS for:

- system font stack and tabular numerals;
- canvas, surface, border, text, and focus colors;
- `.priority-ledger`, `.trust-strip`, `.deadline-rail`, `.capacity-grid`, `.balance-strip`, `.mobile-record`, and `.evidence-label`;
- 640px and 1100px breakpoints;
- `:focus-visible` outline of at least 2px plus 2px offset;
- `@media (prefers-reduced-motion: reduce)` disabling transitions;
- no Google Fonts import and no generated-class selector.

Limit `data-testid` selectors to the top-level Streamlit container and DataFrame border if browser verification proves they are necessary.

- [ ] **Step 4: Refactor the app into an explicit main function**

Replace import-time composition with:

```python
def main(model: DashboardViewModel | None = None) -> None:
    configure_page()
    mode = st.session_state.setdefault("theme_mode", "Light")
    st.markdown(f"<style>{render_theme_css(mode)}</style>", unsafe_allow_html=True)
    active_model = model or load_view_model()
    render_header(active_model)
    render_trust_strip(active_model)
    render_overview(active_model)
    render_activity_views(active_model)


if __name__ == "__main__":
    main()
```

Preserve the existing HDFC-to-HSBC session-state router. Remove the in-app password form only after Task 7 verifies private sharing; until then keep it isolated in `render_legacy_password_gate()` and label it transitional in code comments.

- [ ] **Step 5: Replace the header with semantic native controls**

Use a visible `st.title("HDFC Diners Black Metal Command Center")`, a labelled card selectbox, `st.segmented_control("Theme", options=["Light", "Dark"], key="theme_mode")`, and `st.button("Sync Gmail", icon=":material/sync:", width="stretch")`. Render the masked ending as text, not a raw number. Replace “Real-Time” with “Gmail-backed rewards and spend tracker.”

- [ ] **Step 6: Add AppTest smoke and dark-theme tests**

Use `AppTest.from_function()` with an explicit model argument so tests never read personal local data:

```python
def run_fixture_app(model):
    import hdfc_dcbm_app
    hdfc_dcbm_app.main(model=model)


app = AppTest.from_function(run_fixture_app, args=(fixture_model,), default_timeout=15).run()
```

Assert:

- one H1/title is present;
- card switcher, theme control, and sync action exist;
- both light and dark reruns complete without exceptions;
- page text contains `Last successful sync` and `IST`;
- no source order reference or message ID fixture string appears in rendered text.

- [ ] **Step 7: Run style and AppTest suites**

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest tests.test_dashboard_app -v
```

Expected: PASS with no missing token error.

- [ ] **Step 8: Commit the stable shell**

```bash
git add '../requirements.txt' 'dashboard_styles.py' 'hdfc_dcbm_app.py' 'tests/test_dashboard_app.py'
git commit -m 'refactor(dcbm): add semantic command center shell'
```

---

### Task 4: Priority Hero, Deadline Rail, Capacity, Balances, and Milestones

**Files:**
- Modify: `hdfc_dcbm_app.py`
- Modify: `dashboard_styles.py`
- Modify: `tests/test_dashboard_app.py`

**Interfaces:**
- Consumes: `DashboardViewModel.priority`, `.trust`, `.caps`, `.points`, `.active_milestones`, and `.achieved_milestones`.
- Produces: `render_priority_hero()`, `render_deadline_rail()`, `render_capacity_panel()`, `render_balance_strip()`, and `render_milestone_timeline()`.

- [ ] **Step 1: Add failing hierarchy and copy tests**

Add AppTest assertions that the first content after the trust strip contains, in order:

1. `Next action`
2. the selected milestone name
3. `Remaining eligible spend`
4. `Daily pace`
5. `Weekly pace`
6. `Deadline`

Also assert that an achieved welcome milestone appears under an `Achieved` expander rather than as a peer of the priority hero.

- [ ] **Step 2: Run the new tests and verify failure**

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest tests.test_dashboard_app.DashboardAppTests.test_priority_hero_precedes_capacity_and_activity -v
```

Expected: FAIL because the Priority Ledger renderers do not exist.

- [ ] **Step 3: Implement the priority hero using view-model values only**

`render_priority_hero(model)` must not import `dcbm_engine` or perform arithmetic. It renders current, target, remaining, daily pace, weekly pace, deadline, days left, consequence, and evidence from `model.priority`.

When `model.trust.decision_safe` is false, replace imperative wording such as “Spend” with factual wording such as “Cached amount remaining,” and render the limitation immediately above the pace values.

- [ ] **Step 4: Implement the Deadline Rail**

Use native `st.progress(model.priority.progress_percent / 100.0, text=f"{model.priority.progress_percent:.1f}% complete")` as the semantic progress source. A static adjacent `.deadline-rail` may visually reinforce elapsed/remaining time, but it must include the same text and use escaped, developer-owned values only.

- [ ] **Step 5: Implement capacity and balance sections**

Capacity contains exact engine fields:

- calendar-month accelerated RP remaining and used;
- daily accelerated RP remaining and used;
- SmartBuy flight spend capacity;
- SmartBuy hotel spend capacity;
- next reset date and days remaining.

Balance contains:

- lifetime points with evidence qualifier;
- estimated available points and usable SmartBuy value;
- effective reward rate;
- redeemed points summary.

Use “Estimated available” unless statement evidence proves an actual current bank balance.

- [ ] **Step 6: Implement active and achieved milestone timeline**

Sort active milestones by days left. Render one H3 per milestone with textual status and `st.progress`. Place completed milestones in `st.expander("Achieved milestones")`. Keep welcome memberships inside the achieved welcome detail rather than deleting them.

- [ ] **Step 7: Test safe and unsafe decision wording**

Add one fixture with `decision_safe=True` and one with `False`. Assert the safe version shows daily/weekly planning language and the unsafe version shows the cached-data limitation without a spend recommendation.

- [ ] **Step 8: Run AppTest and existing engine tests**

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest tests.test_dashboard_app tests.test_dcbm_engine -v
```

Expected: PASS.

- [ ] **Step 9: Commit the Priority Ledger overview**

```bash
git add 'hdfc_dcbm_app.py' 'dashboard_styles.py' 'tests/test_dashboard_app.py'
git commit -m 'feat(dcbm): build priority ledger overview'
```

---

### Task 5: Responsive History, Transactions, Redemptions, and Sanitized Exports

**Files:**
- Modify: `hdfc_dcbm_app.py`
- Modify: `dashboard_styles.py`
- Modify: `tests/test_dashboard_app.py`
- Modify: `tests/test_dashboard_view_model.py`
- Create: `../.streamlit/config.toml`

**Interfaces:**
- Consumes: privacy-safe view-model collections and CSV helpers.
- Produces: `filter_transactions()`, `render_monthly_history()`, `render_transactions()`, `render_redemptions()`, and `render_mobile_activity_records()`.

- [ ] **Step 1: Add pure filter tests**

Move transaction filtering into `filter_transactions(rows: tuple[SafeTransactionRow, ...], *, period: str, categories: tuple[str, ...], search: str, cycle_start: date | None = None, cycle_end: date | None = None) -> tuple[SafeTransactionRow, ...]`. Test case-insensitive merchant search, category intersection, current-cycle boundaries, month selection, and preserved newest-first order.

```python
def test_filtered_transactions_remain_newest_first(self):
    rows = self.safe_rows_for_dates("2026-09-12", "2026-09-10", "2026-09-11")
    result = filter_transactions(rows, period="All", categories=(), search="")
    self.assertEqual(["2026-09-12", "2026-09-11", "2026-09-10"], [row.date for row in result])
```

- [ ] **Step 2: Render four explicit activity views**

Use `st.tabs(["Overview", "Monthly history", "Transactions", "Redemptions"])`. Overview shows at most five recent safe activities. Preserve the full monthly cap table and drilldown under Monthly history. Preserve period, category, and merchant controls under Transactions. Preserve totals and history under Redemptions.

- [ ] **Step 3: Replace all deprecated width arguments**

Replace every `use_container_width=True` in HDFC code with `width="stretch"`. Start the local app and confirm the Streamlit log contains no `use_container_width` warning.

- [ ] **Step 4: Add sanitized transaction and redemption downloads**

Use only:

```python
st.download_button(
    "Export filtered transactions",
    data=transaction_csv_bytes(filtered_rows),
    file_name=f"dcbm-transactions-{model.as_of}.csv",
    mime="text/csv",
    icon=":material/download:",
    width="stretch",
)
```

and the equivalent `redemption_csv_bytes()` call. Do not call `DataFrame.to_csv()` on an untyped source dictionary or source DataFrame.

- [ ] **Step 5: Disable native DataFrame export**

Create repository-root `../.streamlit/config.toml`:

```toml
[client]
disableDataExport = true
```

This removes the second, uncontrolled DataFrame download path after sanitized downloads are present.

- [ ] **Step 6: Implement mobile activity records**

Determine the mobile presentation through CSS breakpoint-specific containers, not user-agent detection. Each transaction record shows date, merchant, category, amount, total RP, and evidence. Each redemption record shows date, generalized category/description, points burned, value saved, and evidence. Secondary monetary fields are inside a native expander. No record contains raw identifiers.

- [ ] **Step 7: Add rendered/export privacy regressions**

Use fixture strings `PRIVATE-MESSAGE-ID`, `PRIVATE-ORDER-REFERENCE`, `PRIVATE-EMAIL-SUBJECT`, and `PRIVATE-BOOKING-DETAIL`. Assert none appears in:

- rendered app text;
- transaction CSV;
- redemption CSV;
- DataFrame column names.

- [ ] **Step 8: Run activity, privacy, and regression suites**

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest tests.test_dashboard_view_model tests.test_dashboard_app tests.test_dcbm_engine tests.test_reward_summary -v
```

Expected: PASS.

- [ ] **Step 9: Commit responsive safe activity views**

```bash
git add '../.streamlit/config.toml' 'hdfc_dcbm_app.py' 'dashboard_styles.py' 'tests/test_dashboard_app.py' 'tests/test_dashboard_view_model.py'
git commit -m 'feat(dcbm): add sanitized responsive activity views'
```

---

### Task 6: Explicit Sync, Empty, Stale, Partial, Error, and Router States

**Files:**
- Modify: `hdfc_dcbm_app.py`
- Modify: `dashboard_view_model.py`
- Modify: `tests/test_dashboard_app.py`
- Modify: `tests/test_dashboard_view_model.py`
- Inspect: `app.py`
- Inspect: `../HSBC Live Plus Statements/hsbc_live_plus_app.py`

**Interfaces:**
- Consumes: existing `dcbm_engine.trigger_live_sync()` and session-state card router.
- Produces: `DashboardState`, `SyncResultView`, `run_sync()`, `render_empty_state()`, and `render_error_state()`.

- [ ] **Step 1: Add state enums and failing state tests**

```python
class DashboardState(StrEnum):
    IDLE = "Idle"
    SYNCING = "Syncing"
    SUCCESS = "Success"
    PARTIAL = "Partial"
    STALE = "Stale"
    ERROR = "Error"
    EMPTY = "Empty"


@dataclass(frozen=True)
class SyncResultView:
    state: DashboardState
    message: str
    alert_count: int | None
    synced_at_ist: str
```

Test that missing source data yields Empty, validation failure with cached values yields Partial or Stale, invalid JSON yields Error, and valid current evidence yields Idle.

- [ ] **Step 2: Remove silent initial sync and silent file failures**

Delete the current behavior that automatically triggers Gmail sync when `gmail_alerts.json` is absent and swallows the exception. Empty data must render an explicit explanation and a user-invoked `Sync Gmail` action.

Change JSON loading so malformed files record filename-specific, non-sensitive limitations in the view model. Do not include paths, exception reprs, payload content, or credentials in rendered errors.

- [ ] **Step 3: Implement explicit sync lifecycle**

`run_sync()` calls `trigger_live_sync()` only after the user activates Sync. During the call:

- set session state to Syncing;
- disable duplicate submission;
- display `Reading Gmail alerts without modifying mailbox state`;
- on success, clear only the dashboard cache, rebuild the model, and show alert count plus IST timestamp;
- on failure, retain the last model if available and show `Sync failed. Cached values are unchanged.`;
- log the exception server-side without interpolating it into the UI.

- [ ] **Step 4: Add sync tests with patched engine calls**

Assert exactly one sync call per click, no call on ordinary rerun, cache clear on success, cached content retained on failure, and no exception details in visible text.

- [ ] **Step 5: Verify bidirectional card routing**

Run AppTest against both `hdfc_dcbm_app.py` and root `app.py`. Change the card switcher from HDFC to HSBC and back. Assert the selected card persists without recursion, duplicate `set_page_config`, or bypass of the production private-sharing boundary.

Do not refactor the HSBC application unless a failing routing test proves a minimal compatibility change is necessary. If changed, add the corresponding test in the same commit.

- [ ] **Step 6: Run all HDFC and routing tests**

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 7: Commit explicit state handling**

```bash
git add 'dashboard_view_model.py' 'hdfc_dcbm_app.py' 'tests/test_dashboard_view_model.py' 'tests/test_dashboard_app.py'
git commit -m 'feat(dcbm): make dashboard states explicit'
```

---

### Task 7: Accessibility, Responsive Browser Verification, Documentation, and Private Sharing

**Files:**
- Modify: `dashboard_styles.py`
- Modify: `hdfc_dcbm_app.py`
- Modify: `tests/test_dashboard_app.py`
- Modify: `README.md`
- Verify external setting: Streamlit Community Cloud sharing for `ejaz-dcbm-report.streamlit.app`

**Interfaces:**
- Consumes: completed Priority Ledger app and Streamlit Cloud deployment.
- Produces: verified WCAG-oriented keyboard/responsive behavior, deployment runbook, and a production-private app.

- [ ] **Step 1: Add automated semantic assertions**

AppTest must assert:

- one page title/H1 and ordered H2/H3 section labels;
- all controls have visible text labels or Streamlit Material icon plus accessible label;
- every status includes a word in addition to color;
- each progress indicator has adjacent current/target/remaining text;
- no body/meta copy is intentionally styled below 12px;
- no emoji-only functional control remains.

- [ ] **Step 2: Run the complete automated suite**

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest discover -s tests -v
```

Expected: every existing and new test passes.

- [ ] **Step 3: Start the local app and inspect logs**

Run from `HDFC Diners Black Metal Statements`:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m streamlit run hdfc_dcbm_app.py --server.port 8502 --server.headless true
```

Verify startup succeeds, no dark-token exception occurs, and no deprecated `use_container_width` warning appears.

- [ ] **Step 4: Capture and inspect responsive states**

Using Playwright against `http://localhost:8502`, capture full-page screenshots in both themes at:

- 1440x900
- 768x1024
- 390x844

At each size verify no page-level horizontal overflow, no clipped header controls, readable navigation, non-squashed cards, and privacy-safe activity records. Save screenshots under `output/playwright/dcbm-priority-ledger/`; remove failed or redundant captures before committing and do not commit screenshots containing real transaction data.

- [ ] **Step 5: Test keyboard and zoom behavior**

From a fresh page, use Tab and Shift+Tab through card selector, theme, sync, navigation, filters, expanders, and downloads. Verify a visible focus indicator in both themes. At 200% browser zoom, verify all controls remain reachable and the page does not require two-dimensional scrolling.

- [ ] **Step 6: Inspect sanitized downloads**

Download transaction and redemption CSVs from fixture/test data. Verify the exact headers match the allowlists and search the files for `message`, `subject`, `reference`, `card`, and fixture secret strings. Keep no downloaded CSV in the repository.

- [ ] **Step 7: Update the README deployment and privacy runbook**

Document:

1. local start command and required Python version;
2. source-of-truth files and trust labels;
3. read-only Gmail sync behavior;
4. sanitized export field lists;
5. Streamlit Community Cloud private-sharing setup by viewer email;
6. the rule that secrets belong only in Streamlit secrets and never git;
7. post-deploy verification from a fresh unauthenticated browser;
8. rollback instructions: keep the prior deployment commit available and never make the app public as a debugging workaround.

- [ ] **Step 8: Request action-time confirmation and enable private sharing on the current app**

Immediately before changing the Streamlit Cloud permission, request confirmation because this changes access to cloud data. After confirmation, set the current app to private and grant viewer access only to the approved owner email. Do not add unapproved viewers.

- [ ] **Step 9: Verify the current production privacy gate**

Use a fresh browser session not authenticated to Streamlit and visit `https://ejaz-dcbm-report.streamlit.app/`. Pass condition: Streamlit authentication appears before any dashboard title, amount, merchant, redemption, or card detail. Do not deploy redesigned code until this gate passes.

- [ ] **Step 10: Remove the transitional application-password UI**

Delete `render_legacy_password_gate()` and its call after private sharing is verified. Remove only the application password flow; do not remove the platform authentication expectation, local-development documentation, or card router. Add an AppTest assertion that no `DASHBOARD_PASSWORD` value is required to render a supplied fixture model locally.

- [ ] **Step 11: Commit verified product code and documentation**

```bash
git add 'dashboard_styles.py' 'hdfc_dcbm_app.py' 'tests/test_dashboard_app.py' 'README.md' 'docs/superpowers/specs/2026-09-13-dcbm-priority-ledger-redesign.md' 'docs/superpowers/plans/2026-09-13-dcbm-priority-ledger-redesign.md'
git commit -m 'docs(dcbm): finalize priority ledger deployment contract'
```

- [ ] **Step 12: Deploy the reviewed commit**

Push the reviewed branch and allow Streamlit Community Cloud to rebuild from that commit. Verify the deployed commit identifier in the app-management surface and confirm private sharing remains enabled.

- [ ] **Step 13: Verify the production privacy gate and final UI**

Use a fresh browser session not authenticated to Streamlit and visit `https://ejaz-dcbm-report.streamlit.app/`. Pass condition: Streamlit authentication appears before any dashboard title, amount, merchant, redemption, or card detail. Then authenticate as the approved owner and repeat light/dark and 1440/768/390 smoke checks.

- [ ] **Step 14: Final repository and artifact check**

Run:

```bash
git status --short
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest discover -s tests -v
```

Pass condition: intended source/doc changes only, no secrets, no downloaded CSVs, no screenshots containing real financial data, and the complete suite passes.

## Completion criteria

The work is complete only when:

- private sharing blocks unauthenticated production access before app rendering;
- full order references and message IDs are absent from DOM, tables, and exports;
- dark mode works;
- trust/freshness/evidence labels are accurate and in IST;
- the nearest active milestone is the first decision surface;
- desktop, tablet, mobile, keyboard, and 200% zoom checks pass;
- all existing and new tests pass;
- no Gmail or reward-rule source-of-truth contract has changed without a focused test and explicit explanation.
