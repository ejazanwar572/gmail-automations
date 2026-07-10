# HDFC Diners Black Metal Streamlit Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small local Streamlit dashboard that reads the validated HDFC Diners Black Metal tracker, displays three milestone progress bars, and provides a non-mutating planned-spend shifter with transparent reward-value estimates.

**Architecture:** Keep all file loading and financial calculations in a Streamlit-free `dashboard_model.py`. Compose the UI in `dashboard.py`, with only optional posted-point and membership-claim inputs persisted in `dashboard_state.json`. Preserve the existing Gmail workflow as the sole transaction and freshness source, and give HDFC its own Markdown renderer so other card reports do not inherit HDFC-specific sections.

**Tech Stack:** Python 3.12, Streamlit 1.x, standard-library `dataclasses`, `datetime`, `json`, `pathlib`, and `unittest`; Streamlit `AppTest` for UI verification.

## Global Constraints

- Use `/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3` for all Python commands.
- The dashboard is read-only with respect to Gmail, `gmail_alerts.json`, `sync_metadata.json`, `validation_report.json`, `statements_data.json`, and transaction totals.
- `validation_report.json.ok != true` disables trusted recommendations and milestone-completion claims.
- Label calculated points and shifter results as `Estimated` or `Projection`; never present missing MCC/category or unposted points as confirmed.
- Missing issuance evidence produces a provisional welcome window without an invented deadline.
- Keep the Markdown report portable and non-interactive; the shifter exists only in Streamlit.
- Do not add a second transaction database or public hosting.

## File Map

- Create `HDFC Diners Black Metal Statements/dashboard_model.py`: typed loaders, trust gate, progress calculations, reward projection, redemption comparison, and dashboard snapshot assembly.
- Create `HDFC Diners Black Metal Statements/dashboard.py`: Streamlit layout, widgets, progress bars, status labels, and exception handling.
- Create `HDFC Diners Black Metal Statements/dashboard_state.json`: optional actual points and membership claim states only.
- Create `HDFC Diners Black Metal Statements/requirements-dashboard.txt`: isolated Streamlit dependency.
- Create `HDFC Diners Black Metal Statements/tests/test_dashboard_model.py`: pure model tests.
- Create `HDFC Diners Black Metal Statements/tests/test_dashboard_app.py`: Streamlit `AppTest` smoke and interaction tests.
- Create `HDFC Diners Black Metal Statements/hdfc_report.py`: HDFC-specific static progress-bar renderer.
- Create `HDFC Diners Black Metal Statements/tests/test_hdfc_report.py`: Markdown shape regression tests.
- Modify `HDFC Diners Black Metal Statements/benefits_config.json`: quarterly milestone, welcome memberships, reward multipliers, redemption values, and explicit unknown issuance date.
- Modify `HDFC Diners Black Metal Statements/update_report.py`: call the HDFC-specific renderer.
- Create `HDFC Diners Black Metal Statements/README_dashboard.md`: installation, launch, data trust, and refresh instructions.

---

### Task 1: Pure Dashboard Model and Milestone Progress

**Files:**
- Create: `HDFC Diners Black Metal Statements/dashboard_model.py`
- Create: `HDFC Diners Black Metal Statements/tests/test_dashboard_model.py`
- Modify: `HDFC Diners Black Metal Statements/benefits_config.json`

**Interfaces:**
- Produces: `load_dashboard(card_dir: Path, as_of: date | None = None) -> DashboardSnapshot`
- Produces: `build_progress(current: float, target: float) -> Progress`
- Produces: `calendar_quarter_window(as_of: date) -> tuple[date, date]`
- Produces: `eligible_transactions(alerts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]`
- Produces: immutable `Progress`, `TrustState`, and `DashboardSnapshot` dataclasses consumed by Tasks 2 and 3.

- [ ] **Step 1: Add failing tests for progress, quarter boundaries, refunds, provisional dates, and stale validation**

Create `tests/test_dashboard_model.py` with these fixtures and assertions:

```python
import json
import unittest
from datetime import date
from pathlib import Path

import dashboard_model as model


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class DashboardModelTests(unittest.TestCase):
    def make_card_dir(self, root: str, *, valid: bool = True) -> Path:
        card_dir = Path(root)
        write_json(card_dir / "benefits_config.json", {
            "card_name": "HDFC Diners Black Metal Credit Card",
            "card_ending": "2360",
            "issuance_date": None,
            "welcome": {"spend_target": 150000, "window_days": 90},
            "quarterly_milestone": {"spend_target": 400000, "bonus_points": 10000},
            "annual_fee": {"waiver_spend": 800000},
            "reward_model": {"base_points_per_150": 5},
        })
        write_json(card_dir / "gmail_alerts.json", [
            {"date": "2026-06-30", "amount": 10316, "merchant": "GOIBIBO"},
            {"date": "2026-07-02", "amount": 2716.5, "merchant": "ABFRL"},
            {"date": "2026-07-05", "amount": 88800, "merchant": "KAULESH CHANDRA"},
            {"date": "2026-07-08", "amount": 24334, "merchant": "YATRA"},
            {"date": "2026-07-08", "amount": 1399, "merchant": "ABFRL"},
            {"date": "2026-07-09", "amount": -2000, "merchant": "REFUND", "status": "refunded"},
        ])
        write_json(card_dir / "sync_metadata.json", {
            "source": "gmail-connector",
            "synced_at": "2026-07-10T15:13:00Z",
            "latest_alert_date": "2026-07-08",
            "cached_total": 127565.5,
            "unique_alert_count": 6,
        })
        write_json(card_dir / "validation_report.json", {"ok": valid, "failures": [] if valid else ["stale"]})
        write_json(card_dir / "dashboard_state.json", {"actual_posted_points": None, "memberships": {}})
        return card_dir

    def test_progress_clamps_display_but_preserves_actual_spend(self):
        progress = model.build_progress(175000, 150000)
        self.assertEqual(1.0, progress.ratio)
        self.assertEqual(175000, progress.current)
        self.assertEqual(0, progress.remaining)
        self.assertTrue(progress.met)

    def test_calendar_quarter_is_july_through_september(self):
        self.assertEqual(
            (date(2026, 7, 1), date(2026, 9, 30)),
            model.calendar_quarter_window(date(2026, 7, 10)),
        )

    def test_dashboard_separates_refunds_and_keeps_deadline_provisional(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = model.load_dashboard(self.make_card_dir(tmp), as_of=date(2026, 7, 10))
        self.assertEqual(127565.5, snapshot.annual_progress.current)
        self.assertEqual(117249.5, snapshot.quarterly_progress.current)
        self.assertEqual(1, len(snapshot.exceptions))
        self.assertIsNone(snapshot.welcome_deadline)
        self.assertTrue(snapshot.welcome_deadline_provisional)

    def test_stale_validation_disables_trusted_recommendations(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = model.load_dashboard(self.make_card_dir(tmp, valid=False), as_of=date(2026, 7, 10))
        self.assertFalse(snapshot.trust.ok)
        self.assertFalse(snapshot.trust.recommendations_enabled)
        self.assertEqual("Stale", snapshot.trust.label)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused tests and confirm the model is absent**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest discover -s tests -p 'test_dashboard_model.py' -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dashboard_model'`.

- [ ] **Step 3: Implement typed loading, trust state, transaction classification, and progress**

Create `dashboard_model.py` with immutable dataclasses and these exact public signatures:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Progress:
    current: float
    target: float
    remaining: float
    ratio: float
    met: bool


@dataclass(frozen=True)
class TrustState:
    ok: bool
    label: str
    recommendations_enabled: bool
    failures: tuple[str, ...]


@dataclass(frozen=True)
class DashboardSnapshot:
    card_name: str
    card_ending: str
    as_of: date
    synced_at: str
    latest_alert_date: str
    trust: TrustState
    welcome_progress: Progress
    welcome_deadline: date | None
    welcome_deadline_provisional: bool
    quarterly_progress: Progress
    quarter_start: date
    quarter_end: date
    quarterly_bonus_points: int
    annual_progress: Progress
    included_transactions: tuple[dict[str, Any], ...]
    exceptions: tuple[dict[str, Any], ...]
    config: dict[str, Any]
    dashboard_state: dict[str, Any]


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {path.name}: {exc}") from exc


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def build_progress(current: float, target: float) -> Progress:
    current = max(0.0, float(current))
    target = float(target)
    ratio = 0.0 if target <= 0 else min(1.0, current / target)
    return Progress(current, target, max(0.0, target - current), ratio, current >= target > 0)


def calendar_quarter_window(as_of: date) -> tuple[date, date]:
    start_month = ((as_of.month - 1) // 3) * 3 + 1
    start = date(as_of.year, start_month, 1)
    next_start = date(as_of.year + 1, 1, 1) if start_month == 10 else date(as_of.year, start_month + 3, 1)
    return start, next_start - timedelta(days=1)


def eligible_transactions(alerts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included, exceptions = [], []
    for alert in alerts:
        amount = float(alert.get("amount", 0) or 0)
        status = str(alert.get("status", "posted")).lower()
        if amount <= 0 or status in {"declined", "reversed", "refunded", "duplicate", "uncertain"}:
            exceptions.append(alert)
        else:
            included.append(alert)
    return included, exceptions


def load_dashboard(card_dir: Path, as_of: date | None = None) -> DashboardSnapshot:
    as_of = as_of or date.today()
    config = _load_json(card_dir / "benefits_config.json", {})
    alerts = _load_json(card_dir / "gmail_alerts.json", [])
    metadata = _load_json(card_dir / "sync_metadata.json", {})
    validation = _load_json(card_dir / "validation_report.json", {"ok": False, "failures": ["validation report missing"]})
    state = _load_json(card_dir / "dashboard_state.json", {"actual_posted_points": None, "memberships": {}})
    included, exceptions = eligible_transactions(alerts)
    annual_spend = sum(float(item.get("amount", 0) or 0) for item in included)
    quarter_start, quarter_end = calendar_quarter_window(as_of)
    quarter_spend = sum(
        float(item.get("amount", 0) or 0)
        for item in included
        if (parsed := _parse_date(item.get("date"))) and quarter_start <= parsed <= quarter_end
    )
    issuance_date = _parse_date(config.get("issuance_date"))
    welcome_deadline = issuance_date + timedelta(days=int(config.get("welcome", {}).get("window_days", 90)) - 1) if issuance_date else None
    welcome_spend = sum(
        float(item.get("amount", 0) or 0)
        for item in included
        if issuance_date is None or ((parsed := _parse_date(item.get("date"))) and issuance_date <= parsed <= welcome_deadline)
    )
    valid = validation.get("ok") is True
    trust = TrustState(valid, "Verified" if valid else "Stale", valid, tuple(validation.get("failures", [])))
    milestone = config.get("quarterly_milestone", {})
    return DashboardSnapshot(
        card_name=config.get("card_name", "HDFC Diners Black Metal Credit Card"),
        card_ending=config.get("card_ending", "2360"),
        as_of=as_of,
        synced_at=str(metadata.get("synced_at", "Unknown")),
        latest_alert_date=str(metadata.get("latest_alert_date", "Unknown")),
        trust=trust,
        welcome_progress=build_progress(welcome_spend, config.get("welcome", {}).get("spend_target", 150000)),
        welcome_deadline=welcome_deadline,
        welcome_deadline_provisional=welcome_deadline is None,
        quarterly_progress=build_progress(quarter_spend, milestone.get("spend_target", 400000)),
        quarter_start=quarter_start,
        quarter_end=quarter_end,
        quarterly_bonus_points=int(milestone.get("bonus_points", 10000)),
        annual_progress=build_progress(annual_spend, config.get("annual_fee", {}).get("waiver_spend", 800000)),
        included_transactions=tuple(included),
        exceptions=tuple(exceptions),
        config=config,
        dashboard_state=state,
    )
```

Update `benefits_config.json` by adding these top-level objects without changing existing fee, source, or cycle data:

```json
"issuance_date": null,
"quarterly_milestone": {
  "spend_target": 400000,
  "bonus_points": 10000,
  "period": "calendar_quarter"
},
"welcome_memberships": ["Club Marriott", "Amazon Prime", "Swiggy One"],
"projection_categories": {
  "Regular spend": 1,
  "SmartBuy flight": 5,
  "SmartBuy hotel": 10,
  "Weekend dining": 2,
  "SmartBuy voucher": 3,
  "Uncertain or excluded": 0
},
"redemption_values": {
  "SmartBuy travel": 1.0,
  "Airmiles": 1.0,
  "Products and vouchers": 0.5,
  "Cashback": 0.3
},
"smartbuy_accelerated_points_cap": 10000,
"smartbuy_booking_points_limit_ratio": 0.7
```

- [ ] **Step 4: Run model tests and correct fixture reconciliation if needed**

Run the focused command from Step 2. Expected: all four tests PASS. If the expected annual value differs, the test must use the sum of positive included amounts; do not change production logic to match an incorrect arithmetic fixture.

- [ ] **Step 5: Commit the model slice**

```bash
git add 'HDFC Diners Black Metal Statements/dashboard_model.py' 'HDFC Diners Black Metal Statements/tests/test_dashboard_model.py' 'HDFC Diners Black Metal Statements/benefits_config.json'
git commit -m "feat: add HDFC dashboard progress model"
```

---

### Task 2: Reward Projection and Reconciliation Engine

**Files:**
- Modify: `HDFC Diners Black Metal Statements/dashboard_model.py`
- Modify: `HDFC Diners Black Metal Statements/tests/test_dashboard_model.py`
- Create: `HDFC Diners Black Metal Statements/dashboard_state.json`

**Interfaces:**
- Consumes: `DashboardSnapshot` and its `config` from Task 1.
- Produces: `project_spend(snapshot: DashboardSnapshot, amount: float, category: str, portal_markup_percent: float, redemption_method: str) -> Projection`
- Produces: `redemption_values(points: int, config: dict[str, Any]) -> dict[str, float]`
- Produces: immutable `Projection` with `estimated_base_points`, `estimated_bonus_points`, `estimated_total_points`, `gross_value`, `portal_cost`, `net_value`, three projected `Progress` values, and `confidence`.

- [ ] **Step 1: Add failing projection tests**

Append tests that assert:

```python
    def test_projection_rounds_each_full_150_and_subtracts_portal_markup(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = model.load_dashboard(self.make_card_dir(tmp), as_of=date(2026, 7, 10))
            projection = model.project_spend(snapshot, 30000, "SmartBuy hotel", 8.0, "SmartBuy travel")
        self.assertEqual(1000, projection.estimated_base_points)
        self.assertEqual(9000, projection.estimated_bonus_points)
        self.assertEqual(10000, projection.estimated_total_points)
        self.assertEqual(10000, projection.gross_value)
        self.assertEqual(2400, projection.portal_cost)
        self.assertEqual(7600, projection.net_value)
        self.assertEqual("Estimated", projection.confidence)

    def test_uncertain_category_projects_no_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = model.load_dashboard(self.make_card_dir(tmp), as_of=date(2026, 7, 10))
            projection = model.project_spend(snapshot, 50000, "Uncertain or excluded", 0, "Cashback")
        self.assertEqual(0, projection.estimated_total_points)
        self.assertEqual("Uncertain", projection.confidence)

    def test_missing_actual_points_is_pending(self):
        state = {"actual_posted_points": None}
        self.assertEqual("Pending", model.reconciliation_label(4250, state))

    def test_redemption_values_keep_miles_separate_from_rupee_values(self):
        values = model.redemption_values(10000, {
            "redemption_values": {"SmartBuy travel": 1, "Airmiles": 1, "Products and vouchers": 0.5, "Cashback": 0.3}
        })
        self.assertEqual(10000, values["SmartBuy travel"])
        self.assertEqual(10000, values["Airmiles"])
        self.assertEqual(5000, values["Products and vouchers"])
        self.assertEqual(3000, values["Cashback"])
```

- [ ] **Step 2: Run only the new tests and confirm missing interfaces**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest tests.test_dashboard_model.DashboardModelTests.test_projection_rounds_each_full_150_and_subtracts_portal_markup tests.test_dashboard_model.DashboardModelTests.test_uncertain_category_projects_no_points tests.test_dashboard_model.DashboardModelTests.test_missing_actual_points_is_pending -v
```

Expected: FAIL with missing `project_spend` or `Projection`.

- [ ] **Step 3: Implement projection and reconciliation**

Add this public dataclass and functions to `dashboard_model.py`:

```python
import math


@dataclass(frozen=True)
class Projection:
    amount: float
    category: str
    estimated_base_points: int
    estimated_bonus_points: int
    estimated_total_points: int
    gross_value: float
    portal_cost: float
    net_value: float
    welcome_progress: Progress
    quarterly_progress: Progress
    annual_progress: Progress
    confidence: str


def redemption_values(points: int, config: dict[str, Any]) -> dict[str, float]:
    rates = config.get("redemption_values", {})
    return {name: round(points * float(rate), 2) for name, rate in rates.items()}


def reconciliation_label(estimated_points: int, state: dict[str, Any]) -> str:
    actual = state.get("actual_posted_points")
    if actual is None:
        return "Pending"
    difference = int(actual) - int(estimated_points)
    return "Matched" if difference == 0 else f"Review difference: {difference:+d} points"


def project_spend(snapshot: DashboardSnapshot, amount: float, category: str, portal_markup_percent: float, redemption_method: str) -> Projection:
    amount = max(0.0, float(amount))
    multiplier = float(snapshot.config.get("projection_categories", {}).get(category, 0))
    points_per_150 = float(snapshot.config.get("reward_model", {}).get("base_points_per_150", 5))
    base_points = math.floor(amount / 150) * points_per_150 if multiplier > 0 else 0
    total_points = int(base_points * multiplier)
    bonus_points = max(0, total_points - int(base_points))
    if category.startswith("SmartBuy"):
        cap = int(snapshot.config.get("smartbuy_accelerated_points_cap", 10000))
        bonus_points = min(bonus_points, cap)
        total_points = int(base_points) + bonus_points
    values = redemption_values(total_points, snapshot.config)
    gross_value = values.get(redemption_method, 0.0)
    portal_cost = round(amount * max(0.0, float(portal_markup_percent)) / 100.0, 2)
    confidence = "Uncertain" if multiplier == 0 else "Estimated"
    projected_eligible_amount = 0 if multiplier == 0 else amount
    return Projection(
        amount=amount,
        category=category,
        estimated_base_points=int(base_points),
        estimated_bonus_points=bonus_points,
        estimated_total_points=total_points,
        gross_value=gross_value,
        portal_cost=portal_cost,
        net_value=round(gross_value - portal_cost, 2),
        welcome_progress=build_progress(snapshot.welcome_progress.current + projected_eligible_amount, snapshot.welcome_progress.target),
        quarterly_progress=build_progress(snapshot.quarterly_progress.current + projected_eligible_amount, snapshot.quarterly_progress.target),
        annual_progress=build_progress(snapshot.annual_progress.current + projected_eligible_amount, snapshot.annual_progress.target),
        confidence=confidence,
    )
```

Create `dashboard_state.json`:

```json
{
  "actual_posted_points": null,
  "memberships": {
    "Club Marriott": "evidence needed",
    "Amazon Prime": "evidence needed",
    "Swiggy One": "evidence needed"
  }
}
```

- [ ] **Step 4: Run the complete model test file**

Expected: all Task 1 and Task 2 tests PASS. Confirm no `streamlit` import exists in `dashboard_model.py` with:

```bash
rg -n '^import streamlit|^from streamlit' dashboard_model.py
```

Expected: no output and exit code 1.

- [ ] **Step 5: Commit the projection slice**

```bash
git add 'HDFC Diners Black Metal Statements/dashboard_model.py' 'HDFC Diners Black Metal Statements/tests/test_dashboard_model.py' 'HDFC Diners Black Metal Statements/dashboard_state.json'
git commit -m "feat: add HDFC reward projection engine"
```

---

### Task 3: Streamlit Dashboard UI

**Files:**
- Create: `HDFC Diners Black Metal Statements/dashboard.py`
- Create: `HDFC Diners Black Metal Statements/tests/test_dashboard_app.py`
- Create: `HDFC Diners Black Metal Statements/requirements-dashboard.txt`

**Interfaces:**
- Consumes: `load_dashboard`, `project_spend`, `redemption_values`, and `reconciliation_label` from Tasks 1 and 2.
- Produces: a Streamlit app whose visible section headings are `Welcome benefit`, `Quarterly milestone`, `Annual fee waiver`, `Spend shifter`, `Reward value`, `Reward reconciliation`, and `Transactions`.

- [ ] **Step 1: Add Streamlit dependency and failing AppTest**

Create `requirements-dashboard.txt`:

```text
streamlit>=1.36,<2
```

Create `tests/test_dashboard_app.py`:

```python
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class DashboardAppTests(unittest.TestCase):
    def test_dashboard_renders_progress_and_projection_sections(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "dashboard.py"))
        app.run(timeout=15)
        self.assertFalse(app.exception)
        page = " ".join(item.value for item in [*app.title, *app.header, *app.subheader, *app.markdown])
        for text in ["Welcome benefit", "Quarterly milestone", "Annual fee waiver", "Spend shifter", "Reward value", "Transactions"]:
            self.assertIn(text, page)
        self.assertEqual(3, len(app.progress))

    def test_spend_shifter_updates_projection_without_writing_tracker_files(self):
        app_path = Path(__file__).resolve().parents[1] / "dashboard.py"
        alerts_path = app_path.parent / "gmail_alerts.json"
        before = alerts_path.read_bytes()
        app = AppTest.from_file(str(app_path)).run(timeout=15)
        app.slider[0].set_value(30000).run(timeout=15)
        self.assertEqual(before, alerts_path.read_bytes())
        self.assertTrue(any("Projection" in item.value for item in app.markdown))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Install dependency and confirm the app test fails because the app is absent**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pip install -r requirements-dashboard.txt
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest discover -s tests -p 'test_dashboard_app.py' -v
```

Expected: dependency installation succeeds; test FAILS because `dashboard.py` does not exist.

- [ ] **Step 3: Implement the quiet, dense Streamlit UI**

Create `dashboard.py` with this structure and labels:

```python
from datetime import date
from pathlib import Path

import streamlit as st

from dashboard_model import load_dashboard, project_spend, reconciliation_label, redemption_values


CARD_DIR = Path(__file__).resolve().parent
st.set_page_config(page_title="DCB Metal Tracker", page_icon="💳", layout="wide")
st.title("HDFC Diners Black Metal")
st.caption("Card ending 2360 · Local read-only dashboard")

try:
    snapshot = load_dashboard(CARD_DIR, as_of=date.today())
except ValueError as exc:
    st.error(str(exc))
    st.stop()

if snapshot.trust.ok:
    st.success(f"Verified tracker · synced {snapshot.synced_at} · latest transaction {snapshot.latest_alert_date}")
else:
    st.error("Stale or unreconciled tracker. Projections are visible for inspection, but trusted recommendations are disabled.")
    for failure in snapshot.trust.failures:
        st.caption(f"• {failure}")


def progress_block(title: str, progress, detail: str) -> None:
    st.subheader(title)
    st.progress(progress.ratio, text=f"₹{progress.current:,.0f} of ₹{progress.target:,.0f}")
    st.caption(f"₹{progress.remaining:,.0f} remaining · {detail}")


welcome_col, quarter_col, annual_col = st.columns(3)
with welcome_col:
    deadline = snapshot.welcome_deadline.isoformat() if snapshot.welcome_deadline else "deadline evidence needed"
    progress_block("Welcome benefit", snapshot.welcome_progress, deadline)
with quarter_col:
    progress_block("Quarterly milestone", snapshot.quarterly_progress, f"{snapshot.quarter_start} to {snapshot.quarter_end} · +{snapshot.quarterly_bonus_points:,} RP")
with annual_col:
    progress_block("Annual fee waiver", snapshot.annual_progress, "₹10,000 + taxes at risk until target is met")

st.markdown("#### Membership claims")
membership_cols = st.columns(3)
for column, name in zip(membership_cols, snapshot.config.get("welcome_memberships", [])):
    with column:
        status = snapshot.dashboard_state.get("memberships", {}).get(name, "evidence needed")
        st.metric(name, status.title())

st.header("Spend shifter")
amount = st.slider("Additional planned spend", 0, 500000, 0, 5000)
category = st.selectbox("Spend category", list(snapshot.config.get("projection_categories", {})))
markup = st.slider("Portal markup or processing fee (%)", 0.0, 20.0, 0.0, 0.5)
method = st.selectbox("Intended redemption", list(snapshot.config.get("redemption_values", {})))
projection = project_spend(snapshot, amount, category, markup, method)
st.markdown(f"**Projection · {projection.confidence}:** {projection.estimated_total_points:,} RP · gross ₹{projection.gross_value:,.0f} · portal cost ₹{projection.portal_cost:,.0f} · net ₹{projection.net_value:,.0f}")
if not snapshot.trust.recommendations_enabled:
    st.warning("Recommendation disabled until tracker freshness and reconciliation pass.")

projected_cols = st.columns(3)
for column, title, progress in zip(projected_cols, ["Welcome after spend", "Quarter after spend", "Waiver after spend"], [projection.welcome_progress, projection.quarterly_progress, projection.annual_progress]):
    column.metric(title, f"{progress.ratio:.0%}", f"₹{progress.remaining:,.0f} remaining")

st.header("Reward value")
point_balance = st.number_input("Point balance", min_value=0, value=projection.estimated_total_points, step=100)
values = redemption_values(point_balance, snapshot.config)
value_cols = st.columns(len(values))
for column, (name, value) in zip(value_cols, values.items()):
    suffix = " miles-equivalent" if name == "Airmiles" else ""
    column.metric(name, f"{value:,.0f}{suffix}" if suffix else f"₹{value:,.0f}")
st.caption("SmartBuy flight/hotel points can cover up to 70% of a booking. Values are redemption estimates, not guaranteed cash value.")

st.header("Reward reconciliation")
estimated = sum(int(float(item.get("amount", 0)) // 150 * 5) for item in snapshot.included_transactions)
actual = snapshot.dashboard_state.get("actual_posted_points")
st.metric("Estimated base points", f"{estimated:,}")
st.metric("Actual posted points", "Pending" if actual is None else f"{int(actual):,}")
st.caption(reconciliation_label(estimated, snapshot.dashboard_state))

st.header("Transactions")
st.dataframe(list(snapshot.included_transactions), use_container_width=True, hide_index=True)
with st.expander(f"Exceptions ({len(snapshot.exceptions)})"):
    if snapshot.exceptions:
        st.dataframe(list(snapshot.exceptions), use_container_width=True, hide_index=True)
    else:
        st.caption("No declined, reversed, refunded, duplicate, or uncertain entries are present in the local cache.")
```

- [ ] **Step 4: Run AppTest and model regression tests**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest discover -s tests -p 'test_dashboard_*.py' -v
```

Expected: all dashboard model and app tests PASS. If the selected Streamlit version exposes widget collections differently, adjust only the test selectors while preserving visible labels and behaviors.

- [ ] **Step 5: Commit the UI slice**

```bash
git add 'HDFC Diners Black Metal Statements/dashboard.py' 'HDFC Diners Black Metal Statements/tests/test_dashboard_app.py' 'HDFC Diners Black Metal Statements/requirements-dashboard.txt'
git commit -m "feat: add HDFC Streamlit dashboard"
```

---

### Task 4: HDFC Markdown Progress Report and Launch Documentation

**Files:**
- Create: `HDFC Diners Black Metal Statements/hdfc_report.py`
- Create: `HDFC Diners Black Metal Statements/tests/test_hdfc_report.py`
- Modify: `HDFC Diners Black Metal Statements/update_report.py`
- Create: `HDFC Diners Black Metal Statements/README_dashboard.md`

**Interfaces:**
- Consumes: `load_dashboard` and existing `card_benefit_tracker.build_report`.
- Produces: `build_hdfc_report(card_dir: Path, as_of: date | None = None) -> str`
- Produces: `write_hdfc_report(card_dir: Path, as_of: date | None = None) -> Path`

- [ ] **Step 1: Add a failing Markdown shape test**

Create `tests/test_hdfc_report.py`:

```python
import tempfile
import unittest
from datetime import date
from pathlib import Path

import hdfc_report


class HdfcReportTests(unittest.TestCase):
    def test_progress_bar_is_static_and_zero_value_table_is_removed(self):
        card_dir = Path(__file__).resolve().parents[1]
        report = hdfc_report.build_hdfc_report(card_dir, as_of=date(2026, 7, 10))
        self.assertIn("Welcome benefit progress", report)
        self.assertIn("Quarterly milestone progress", report)
        self.assertIn("Annual fee-waiver progress", report)
        self.assertRegex(report, r"[█░]{20}")
        self.assertNotIn("| Eligible Reward Points Spend | INR 127,565.50 | INR 0.00 |", report)
        self.assertIn("streamlit run dashboard.py", report)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and confirm `hdfc_report` is absent**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest discover -s tests -p 'test_hdfc_report.py' -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'hdfc_report'`.

- [ ] **Step 3: Implement HDFC-specific Markdown transformation**

Create `hdfc_report.py`:

```python
from __future__ import annotations

from datetime import date
from pathlib import Path

import card_benefit_tracker as tracker
from dashboard_model import DashboardSnapshot, Progress, load_dashboard, redemption_values


def text_bar(progress: Progress, width: int = 20) -> str:
    filled = round(progress.ratio * width)
    return "█" * filled + "░" * (width - filled)


def progress_lines(label: str, progress: Progress, detail: str) -> list[str]:
    return [
        f"### {label}",
        f"`{text_bar(progress)}` {progress.ratio:.1%}",
        f"- INR {progress.current:,.2f} of INR {progress.target:,.2f}",
        f"- INR {progress.remaining:,.2f} remaining",
        f"- {detail}",
        "",
    ]


def build_hdfc_report(card_dir: Path, as_of: date | None = None) -> str:
    snapshot = load_dashboard(card_dir, as_of=as_of)
    base = tracker.build_report(card_dir, as_of=as_of)
    transaction_start = base.index("## 4. Current Cycle Transaction Table")
    source_start = base.index("## 6. Source Notes")
    before_transactions = base[:transaction_start]
    transactions = base[transaction_start:source_start]
    source_notes = base[source_start:]
    welcome_start = before_transactions.index("## 3. Welcome Benefit Tracker")
    before_welcome = before_transactions[:welcome_start]
    deadline = snapshot.welcome_deadline.isoformat() if snapshot.welcome_deadline else "Deadline evidence needed; window remains provisional."
    progress_section = ["## 3. Milestone Progress", ""]
    progress_section += progress_lines("Welcome benefit progress", snapshot.welcome_progress, deadline)
    progress_section += progress_lines("Quarterly milestone progress", snapshot.quarterly_progress, f"Calendar quarter {snapshot.quarter_start} to {snapshot.quarter_end}; unlocks {snapshot.quarterly_bonus_points:,} estimated bonus RP.")
    progress_section += progress_lines("Annual fee-waiver progress", snapshot.annual_progress, "INR 8 lakh in 12 months waives the next renewal fee.")
    points = sum(int(float(item.get("amount", 0)) // 150 * 5) for item in snapshot.included_transactions)
    values = redemption_values(points, snapshot.config)
    reward_section = [
        "## 5. Reward Value and Reconciliation",
        f"- Estimated base points: {points:,}",
        f"- SmartBuy travel value: up to INR {values.get('SmartBuy travel', 0):,.2f}",
        f"- Airmiles: up to {values.get('Airmiles', 0):,.0f} miles-equivalent",
        f"- Products/vouchers: up to INR {values.get('Products and vouchers', 0):,.2f}",
        f"- Cashback: up to INR {values.get('Cashback', 0):,.2f}",
        f"- Actual posted points: {snapshot.dashboard_state.get('actual_posted_points') or 'Pending'}",
        "",
        "Interactive projections: run `/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m streamlit run dashboard.py` from this directory.",
        "",
    ]
    transaction_only = transactions.split("## 5. Benefit Utilization and Recommendation", 1)[0]
    return before_welcome + "\n".join(progress_section) + "\n" + transaction_only + "\n".join(reward_section) + "\n" + source_notes


def write_hdfc_report(card_dir: Path, as_of: date | None = None) -> Path:
    path = card_dir / "benefit_tracker_report.md"
    path.write_text(build_hdfc_report(card_dir, as_of=as_of), encoding="utf-8")
    return path
```

Modify `update_report.py` to import `hdfc_report` and call:

```python
if __name__ == "__main__":
    path = hdfc_report.write_hdfc_report(Path(__file__).resolve().parent)
    print(path)
```

Retain the existing parent-directory `sys.path` setup so `card_benefit_tracker` remains importable.

- [ ] **Step 4: Add launch and trust documentation**

Create `README_dashboard.md` with exact commands:

```markdown
# HDFC Diners Black Metal Local Dashboard

## Install

`/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m pip install -r requirements-dashboard.txt`

## Refresh trusted data

Run the existing read-only Gmail connector workflow. The dashboard does not access Gmail itself. A failed `validation_report.json` freshness/reconciliation gate disables trusted recommendations.

## Launch

`/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501`

Open `http://127.0.0.1:8501`.

## Interpretation

Confirmed values come from validated tracker evidence. Estimated values use configured reward rules. Projection values come only from the spend shifter and are never written to transaction files. Uncertain values lack MCC, category, or posted-points evidence.
```

- [ ] **Step 5: Run report, model, and UI tests; rebuild the report**

Run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest discover -s tests -p 'test_*.py' -v
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 run_workflow.py --sync-source none
```

Expected: all tests PASS; workflow exits 0; `validation_report.json.ok` remains true; generated Markdown contains 20-character static bars and no generic zero-value reward row.

- [ ] **Step 6: Commit report and documentation**

```bash
git add 'HDFC Diners Black Metal Statements/hdfc_report.py' 'HDFC Diners Black Metal Statements/tests/test_hdfc_report.py' 'HDFC Diners Black Metal Statements/update_report.py' 'HDFC Diners Black Metal Statements/README_dashboard.md' 'HDFC Diners Black Metal Statements/benefit_tracker_report.md'
git commit -m "feat: add HDFC milestone progress report"
```

---

### Task 5: Full Verification and Browser Smoke Test

**Files:**
- Modify only if verification finds a scoped defect in Task 1-4 files.

**Interfaces:**
- Consumes the complete app and report.
- Produces verification evidence; no new product behavior.

- [ ] **Step 1: Run the complete existing and new unit suite**

From `/Users/ejazanwar/Documents/Gmail Automations` run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest test_card_benefit_workflows.py -v
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m unittest discover -s 'HDFC Diners Black Metal Statements/tests' -p 'test_*.py' -v
```

Expected: both commands exit 0 with zero failures and zero errors.

- [ ] **Step 2: Start Streamlit locally**

From the HDFC directory run:

```bash
/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3 -m streamlit run dashboard.py --server.headless true --server.address 127.0.0.1 --server.port 8501
```

Expected: output includes `Local URL: http://127.0.0.1:8501` and the process remains running for the smoke test.

- [ ] **Step 3: Perform a real browser smoke test**

Using the browser-control skill, open `http://127.0.0.1:8501` and verify:

- Exactly three initial milestone progress bars render.
- Freshness state and latest transaction date are visible.
- Welcome deadline is labelled evidence-needed if issuance date remains null.
- Moving additional spend to INR 30,000 updates projected points and all three projected milestone values.
- Selecting `Uncertain or excluded` changes the projection confidence to `Uncertain` and adds no projected milestone spend.
- Reward values show travel, miles, vouchers, and cashback separately.
- Transactions preserve merchant names and dates.
- No raw filesystem paths appear in the normal dashboard content.
- The layout remains readable at desktop and narrow viewport widths.

Expected: all checks pass with no Streamlit exception panel or browser console error affecting use.

- [ ] **Step 4: Confirm the dashboard did not mutate trusted tracker inputs**

Capture hashes before and after slider interaction:

```bash
shasum gmail_alerts.json sync_metadata.json validation_report.json statements_data.json benefits_config.json
```

Expected: hashes for the four trusted data files are unchanged. `benefits_config.json` is also unchanged during runtime; its implementation-time update was committed in Task 1.

- [ ] **Step 5: Inspect final Git scope and commit any verified corrective changes**

Run:

```bash
git status --short
git diff --check
```

Expected: no scratch files, caches, or test artifacts; no whitespace errors. Preserve unrelated pre-existing user files. If a scoped correction was required, stage only the named HDFC dashboard files and commit with `fix: correct HDFC dashboard verification issue`.
