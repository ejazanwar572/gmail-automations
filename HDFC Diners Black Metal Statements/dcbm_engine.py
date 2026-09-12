"""Core calculation and auto-tracking engine for HDFC Diners Club Black Metal (DCBM).

Provides pure, testable calculations for:
- Automatic SmartBuy detection & reward points computation
- Dual-cycle tracking (official calendar month vs statement billing cycle)
- Daily and monthly cap enforcement
- Milestone progress (Welcome, Quarterly bonus, Annual fee waiver)
- Redemption valuation & spend simulation
- One-click Gmail synchronization
"""

from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple


CARD_DIR = Path(__file__).resolve().parent
BASE_POINTS_PER_150 = 5  # Standard 3.33% reward rate (5 RP per Rs. 150)
MONTHLY_ACCELERATED_CAP = 10000
DAILY_ACCELERATED_CAP = 2500

# Regular expressions for auto-classifying merchants
SMARTBUY_FLIGHT_PATTERN = re.compile(
    r"(?:via\s+smartbu|via\s+smart|smartbuy).*?(?:flight|emt|easemytrip|yatra|goibibo|cleartrip)|(?:emt|yatra|goibibo|cleartrip).*?(?:flight).*?(?:via\s+smartbu|via\s+smart|smartbuy)",
    re.IGNORECASE,
)
SMARTBUY_HOTEL_PATTERN = re.compile(
    r"(?:via\s+smartbu|via\s+smart|smartbuy).*?(?:hotel|stay|lodging)|(?:hotel).*?(?:via\s+smartbu|via\s+smart|smartbuy)",
    re.IGNORECASE,
)
SMARTBUY_VOUCHER_PATTERN = re.compile(
    r"gyftr|instant\s+voucher|smartbuy\s+voucher",
    re.IGNORECASE,
)
LOUNGE_PATTERN = re.compile(r"lounge", re.IGNORECASE)
JEWELLERY_PATTERN = re.compile(r"diamond|jewel|titan|tanishq|malabar|kalyan", re.IGNORECASE)


@dataclass
class TransactionCategory:
    name: str
    icon: str
    is_smartbuy: bool
    accelerated_multiplier: int
    total_multiplier: int
    description: str


CATEGORIES = {
    "smartbuy_flight": TransactionCategory(
        name="SmartBuy Flights",
        icon="✈️",
        is_smartbuy=True,
        accelerated_multiplier=4,
        total_multiplier=5,
        description="5X Total Points (1X Base + 4X Accelerated)",
    ),
    "smartbuy_hotel": TransactionCategory(
        name="SmartBuy Hotels",
        icon="🏨",
        is_smartbuy=True,
        accelerated_multiplier=9,
        total_multiplier=10,
        description="10X Total Points (1X Base + 9X Accelerated)",
    ),
    "smartbuy_voucher": TransactionCategory(
        name="SmartBuy Instant Vouchers",
        icon="🎟️",
        is_smartbuy=True,
        accelerated_multiplier=4,
        total_multiplier=5,
        description="Up to 5X Total Points via Gyftr",
    ),
    "jewellery": TransactionCategory(
        name="Jewellery",
        icon="💎",
        is_smartbuy=False,
        accelerated_multiplier=0,
        total_multiplier=1,
        description="Standard Base Points (5 RP per Rs. 150)",
    ),
    "lounge": TransactionCategory(
        name="Airport Lounge",
        icon="🛋️",
        is_smartbuy=False,
        accelerated_multiplier=0,
        total_multiplier=1,
        description="Complimentary Access Verification Charge",
    ),
    "general": TransactionCategory(
        name="General Retail",
        icon="🛍️",
        is_smartbuy=False,
        accelerated_multiplier=0,
        total_multiplier=1,
        description="Standard Base Points (5 RP per Rs. 150)",
    ),
}


def classify_merchant(merchant: str, message_id: str = "", custom_classifications: Optional[Dict[str, Any]] = None) -> TransactionCategory:
    """Classify a merchant using configured overrides or pattern detection."""
    if custom_classifications and message_id:
        custom = custom_classifications.get(message_id)
        if custom and isinstance(custom, dict):
            mult = custom.get("accelerated_multiplier", 0)
            if mult == 4:
                return CATEGORIES["smartbuy_flight"]
            elif mult == 9:
                return CATEGORIES["smartbuy_hotel"]
            elif mult > 0:
                return TransactionCategory(
                    name=custom.get("classification", "Custom SmartBuy"),
                    icon="⭐",
                    is_smartbuy=True,
                    accelerated_multiplier=mult,
                    total_multiplier=mult + 1,
                    description=f"{mult+1}X Points",
                )

    m = merchant.strip()
    if SMARTBUY_FLIGHT_PATTERN.search(m) or "EMT FLIGHT" in m.upper() or "YATRA FLIGHT" in m.upper() or "GOIBIBO FLIGHT" in m.upper():
        return CATEGORIES["smartbuy_flight"]
    if SMARTBUY_HOTEL_PATTERN.search(m):
        return CATEGORIES["smartbuy_hotel"]
    if SMARTBUY_VOUCHER_PATTERN.search(m):
        return CATEGORIES["smartbuy_voucher"]
    if LOUNGE_PATTERN.search(m):
        return CATEGORIES["lounge"]
    if JEWELLERY_PATTERN.search(m):
        return CATEGORIES["jewellery"]

    return CATEGORIES["general"]


def calculate_points_for_amount(amount: float, category: TransactionCategory) -> Tuple[int, int, int]:
    """Calculate (blocks, base_points, raw_accelerated_points)."""
    blocks = math.floor(max(0.0, amount) / 150.0)
    base_points = blocks * BASE_POINTS_PER_150
    raw_accelerated = base_points * category.accelerated_multiplier
    return blocks, base_points, raw_accelerated


def load_json_file(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_billing_cycle(as_of: date, cycle_end_day: int = 13) -> Tuple[date, date]:
    """Compute the active statement billing cycle for a given date.
    
    If end_day is 13, a statement closes on the 13th of each month.
    Cycle runs from (previous month's 14th) to (current month's 13th).
    """
    if as_of.day > cycle_end_day:
        # We are past this month's statement date; cycle runs from 14th of this month to 13th of next month
        start_year, start_month = as_of.year, as_of.month
        if start_month == 12:
            end_year, end_month = start_year + 1, 1
        else:
            end_year, end_month = start_year, start_month + 1
        start_date = date(start_year, start_month, cycle_end_day + 1)
        end_date = date(end_year, end_month, cycle_end_day)
    else:
        # We are on or before statement date; cycle started on 14th of previous month and ends on 13th of this month
        if as_of.month == 1:
            start_year, start_month = as_of.year - 1, 12
        else:
            start_year, start_month = as_of.year, as_of.month - 1
        start_date = date(start_year, start_month, cycle_end_day + 1)
        end_date = date(as_of.year, as_of.month, cycle_end_day)
    return start_date, end_date


def get_calendar_quarter(as_of: date) -> Tuple[int, str, date, date]:
    """Return (quarter_number, label, start_date, end_date) for a date."""
    q = (as_of.month - 1) // 3 + 1
    start_month = (q - 1) * 3 + 1
    end_month = start_month + 2
    start_date = date(as_of.year, start_month, 1)
    end_day = calendar.monthrange(as_of.year, end_month)[1]
    end_date = date(as_of.year, end_month, end_day)
    label = f"Q{q} {as_of.year}"
    return q, label, start_date, end_date


def process_transactions(
    alerts: List[Dict[str, Any]],
    custom_classifications: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Enrich raw transaction alerts with categorization and point calculations."""
    processed = []
    # Deduplicate by message_id
    seen_ids = set()
    for alert in sorted(alerts, key=lambda a: (a.get("date", ""), a.get("message_id", "")), reverse=True):
        mid = alert.get("message_id", "")
        if mid and mid in seen_ids:
            continue
        if mid:
            seen_ids.add(mid)

        amt = float(alert.get("amount", 0.0))
        merchant = alert.get("merchant", "Unknown Merchant")
        date_str = alert.get("date", "")
        try:
            tx_date = date.fromisoformat(date_str)
        except Exception:
            tx_date = None

        cat = classify_merchant(merchant, message_id=mid, custom_classifications=custom_classifications)
        blocks, base_rp, raw_acc_rp = calculate_points_for_amount(amt, cat)

        processed.append({
            "message_id": mid,
            "date": date_str,
            "tx_date": tx_date,
            "merchant": merchant,
            "amount": amt,
            "category": cat.name,
            "icon": cat.icon,
            "is_smartbuy": cat.is_smartbuy,
            "accelerated_multiplier": cat.accelerated_multiplier,
            "total_multiplier": cat.total_multiplier,
            "description": cat.description,
            "blocks": blocks,
            "base_points": base_rp,
            "raw_accelerated_points": raw_acc_rp,
        })
    return processed


def compute_cap_headroom(
    transactions: List[Dict[str, Any]],
    start_date: date,
    end_date: date,
    as_of: date,
    monthly_cap: int = MONTHLY_ACCELERATED_CAP,
    daily_cap: int = DAILY_ACCELERATED_CAP,
) -> Dict[str, Any]:
    """Calculate accelerated reward point earnings and headroom within a specified date window."""
    window_txs = [
        t for t in transactions
        if t["tx_date"] and start_date <= t["tx_date"] <= end_date and t["is_smartbuy"]
    ]

    # Daily aggregation for daily cap enforcement
    daily_raw: Dict[date, int] = {}
    for t in window_txs:
        d = t["tx_date"]
        daily_raw[d] = daily_raw.get(d, 0) + t["raw_accelerated_points"]

    daily_capped: Dict[date, int] = {
        d: min(daily_cap, pts) for d, pts in daily_raw.items()
    }

    total_accelerated_earned = min(monthly_cap, sum(daily_capped.values()))
    remaining_cap = max(0, monthly_cap - total_accelerated_earned)
    percent_used = round((total_accelerated_earned / monthly_cap) * 100, 1) if monthly_cap > 0 else 0.0
    percent_remaining = round((remaining_cap / monthly_cap) * 100, 1) if monthly_cap > 0 else 0.0

    # Calculate remaining spend headroom before hitting cap
    # For SmartBuy flights (4X multiplier = 20 RP per Rs. 150 spend)
    remaining_flight_spend_capacity = math.floor(remaining_cap / 20) * 150 if remaining_cap > 0 else 0
    # For SmartBuy hotels (9X multiplier = 45 RP per Rs. 150 spend)
    remaining_hotel_spend_capacity = math.floor(remaining_cap / 45) * 150 if remaining_cap > 0 else 0

    days_remaining = max(0, (end_date - as_of).days)
    reset_date = end_date + timedelta(days=1)

    # Today's accelerated points
    today_earned = daily_capped.get(as_of, 0)
    today_remaining = max(0, daily_cap - today_earned)

    # Status classification
    if percent_used >= 100.0:
        status_label = "CAP EXHAUSTED"
        status_color = "red"
    elif percent_used >= 80.0:
        status_label = "APPROACHING CAP"
        status_color = "orange"
    elif percent_used > 0.0:
        status_label = "ACTIVE HEADROOM"
        status_color = "green"
    else:
        status_label = "FULL HEADROOM (100% UNUSED)"
        status_color = "green"

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "reset_date": reset_date.isoformat(),
        "days_remaining": days_remaining,
        "monthly_cap": monthly_cap,
        "daily_cap": daily_cap,
        "earned": total_accelerated_earned,
        "remaining": remaining_cap,
        "percent_used": percent_used,
        "percent_remaining": percent_remaining,
        "today_earned": today_earned,
        "today_remaining": today_remaining,
        "status_label": status_label,
        "status_color": status_color,
        "flight_spend_capacity": remaining_flight_spend_capacity,
        "hotel_spend_capacity": remaining_hotel_spend_capacity,
        "smartbuy_transaction_count": len(window_txs),
    }


def compute_monthly_history(
    transactions: List[Dict[str, Any]],
    as_of: date,
) -> List[Dict[str, Any]]:
    """Compute monthly breakdown of spend, normal/base points, and accelerated points vs 10,000 cap."""
    months_map: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for t in transactions:
        if t.get("tx_date"):
            k = (t["tx_date"].year, t["tx_date"].month)
            months_map.setdefault(k, []).append(t)

    history = []
    # Sort months descending (newest first)
    for (y, m) in sorted(months_map.keys(), reverse=True):
        m_txs = months_map[(y, m)]
        m_start = date(y, m, 1)
        m_end = date(y, m, calendar.monthrange(y, m)[1])
        cap_info = compute_cap_headroom(transactions, m_start, m_end, as_of)
        base_pts = sum(t["base_points"] for t in m_txs)
        total_spend = sum(t["amount"] for t in m_txs)
        acc_pts = cap_info["earned"]
        total_pts = base_pts + acc_pts
        is_current = (y == as_of.year and m == as_of.month)

        history.append({
            "year": y,
            "month": m,
            "label": f"{calendar.month_name[m]} {y}" + (" (Ongoing)" if is_current else ""),
            "month_name": calendar.month_name[m],
            "is_current": is_current,
            "total_spend": round(total_spend, 2),
            "base_points": base_pts,
            "accelerated_points": acc_pts,
            "accelerated_cap": cap_info["monthly_cap"],
            "accelerated_remaining": cap_info["remaining"],
            "accelerated_percent_used": cap_info["percent_used"],
            "accelerated_percent_remaining": cap_info["percent_remaining"],
            "status_label": cap_info["status_label"],
            "total_points": total_pts,
            "smartbuy_tx_count": cap_info["smartbuy_transaction_count"],
            "total_tx_count": len(m_txs),
            "effective_reward_rate": round((total_pts * 1.0 / total_spend) * 100, 2) if total_spend > 0 else 0.0,
            "realized_value_inr": round(total_pts * 1.0, 2),
            "transactions": m_txs,
        })
    return history


def compute_all_dashboard_data(
    card_dir: Path = CARD_DIR,
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    """Produce the complete consolidated dataset for the dashboard UI."""
    as_of = as_of or date.today()

    config = load_json_file(card_dir / "benefits_config.json") or {}
    raw_alerts = load_json_file(card_dir / "gmail_alerts.json") or []
    sync_meta = load_json_file(card_dir / "sync_metadata.json") or {}
    stmt_rewards = load_json_file(card_dir / "statement_rewards.json") or {}
    cycle_ev = load_json_file(card_dir / "cycle_evidence.json") or {}
    redemptions = load_json_file(card_dir / "redemptions_cache.json") or []

    custom_classifications = config.get("reward_model", {}).get("smartbuy_classifications", {})
    transactions = process_transactions(raw_alerts, custom_classifications)

    # Cycle dates
    cycle_end_day = cycle_ev.get("cycle", {}).get("end_day", 13)
    billing_start, billing_end = get_billing_cycle(as_of, cycle_end_day)

    # Calendar month dates
    cal_month_start = date(as_of.year, as_of.month, 1)
    cal_month_end = date(as_of.year, as_of.month, calendar.monthrange(as_of.year, as_of.month)[1])

    # Cap Headrooms
    calendar_month_cap = compute_cap_headroom(transactions, cal_month_start, cal_month_end, as_of)
    billing_cycle_cap = compute_cap_headroom(transactions, billing_start, billing_end, as_of)

    # Previous Month Cap (August if in September)
    if as_of.month == 1:
        prev_year, prev_month = as_of.year - 1, 12
    else:
        prev_year, prev_month = as_of.year, as_of.month - 1
    prev_month_start = date(prev_year, prev_month, 1)
    prev_month_end = date(prev_year, prev_month, calendar.monthrange(prev_year, prev_month)[1])
    prev_month_cap = compute_cap_headroom(transactions, prev_month_start, prev_month_end, as_of)

    # Current billing cycle spend & points
    cycle_txs = [t for t in transactions if t["tx_date"] and billing_start <= t["tx_date"] <= billing_end]
    cycle_spend = sum(t["amount"] for t in cycle_txs)
    cycle_base_points = sum(t["base_points"] for t in cycle_txs)
    cycle_accelerated_points = billing_cycle_cap["earned"]

    # Lifetime spend & points calculation
    total_tracked_spend = sum(t["amount"] for t in transactions)
    unbilled_base_points = sum(t["base_points"] for t in transactions)
    # Statement points baseline if available
    confirmed_total_points = stmt_rewards.get("total_points", 0)
    confirmed_base = stmt_rewards.get("base_points", 0)
    confirmed_acc = stmt_rewards.get("accelerated_points", 0)
    stmt_end_str = stmt_rewards.get("statement_end")
    stmt_end = date.fromisoformat(stmt_end_str) if stmt_end_str else None

    # Post-statement points (transactions strictly after confirmed statement)
    if stmt_end:
        post_stmt_txs = [t for t in transactions if t["tx_date"] and t["tx_date"] > stmt_end]
        post_stmt_spend = sum(t["amount"] for t in post_stmt_txs)
        post_stmt_base = sum(t["base_points"] for t in post_stmt_txs)
        # Accelerated points post-statement grouped by month
        months_post: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        for t in post_stmt_txs:
            k = (t["tx_date"].year, t["tx_date"].month)
            months_post.setdefault(k, []).append(t)
        post_stmt_acc = 0
        for (y, m), m_txs in months_post.items():
            d_start = date(y, m, 1)
            d_end = date(y, m, calendar.monthrange(y, m)[1])
            m_cap = compute_cap_headroom(transactions, d_start, d_end, as_of)
            post_stmt_acc += m_cap["earned"]
        total_estimated_points = confirmed_total_points + post_stmt_base + post_stmt_acc
        points_evidence_mode = "Confirmed Statement Baseline + Live Gmail Tracking"
    else:
        post_stmt_spend = total_tracked_spend
        post_stmt_base = unbilled_base_points
        post_stmt_acc = calendar_month_cap["earned"]
        total_estimated_points = unbilled_base_points + calendar_month_cap["earned"]
        points_evidence_mode = "Live Gmail Alert Tracking"

    # Milestones
    # 1. Welcome Benefit (INR 1.5L in 90 days)
    welcome_cfg = config.get("welcome", {})
    welcome_target = float(welcome_cfg.get("spend_target", 150000.0))
    welcome_start_str = welcome_cfg.get("activation_proxy_date", "2026-06-30")
    welcome_start = date.fromisoformat(welcome_start_str) if welcome_start_str else date(2026, 6, 30)
    welcome_deadline = welcome_start + timedelta(days=welcome_cfg.get("window_days", 90))
    welcome_txs = [t for t in transactions if t["tx_date"] and welcome_start <= t["tx_date"] <= welcome_deadline]
    welcome_spend = sum(t["amount"] for t in welcome_txs)
    welcome_met = welcome_spend >= welcome_target
    welcome_progress = min(100.0, round((welcome_spend / welcome_target) * 100, 1)) if welcome_target > 0 else 100.0
    welcome_days_left = max(0, (welcome_deadline - as_of).days)

    # 2. Quarterly Bonus (INR 4L in calendar quarter -> 10,000 bonus RP)
    q_num, q_label, q_start, q_end = get_calendar_quarter(as_of)
    q_target = float(config.get("quarterly_bonus", {}).get("spend_target", 400000.0))
    q_bonus_pts = int(config.get("quarterly_bonus", {}).get("bonus_points", 10000))
    q_txs = [t for t in transactions if t["tx_date"] and q_start <= t["tx_date"] <= q_end]
    q_spend = sum(t["amount"] for t in q_txs)
    q_remaining = max(0.0, q_target - q_spend)
    q_progress = min(100.0, round((q_spend / q_target) * 100, 1)) if q_target > 0 else 100.0
    q_days_left = max(0, (q_end - as_of).days)
    q_required_daily_runrate = round(q_remaining / q_days_left, 2) if q_days_left > 0 else 0.0
    q_met = q_spend >= q_target

    # 3. Annual Fee Waiver (INR 8L in 12 months -> waive Rs. 10,000 fee)
    annual_cfg = config.get("annual_fee", {})
    annual_target = float(annual_cfg.get("waiver_spend", 800000.0))
    annual_fee_amt = float(annual_cfg.get("amount", 10000.0))
    annual_start_str = annual_cfg.get("period_start", "2026-06-25")
    annual_end_str = annual_cfg.get("period_end", "2027-06-24")
    annual_start = date.fromisoformat(annual_start_str) if annual_start_str else date(2026, 6, 25)
    annual_end = date.fromisoformat(annual_end_str) if annual_end_str else date(2027, 6, 24)
    annual_txs = [t for t in transactions if t["tx_date"] and annual_start <= t["tx_date"] <= annual_end]
    annual_spend = sum(t["amount"] for t in annual_txs)
    annual_remaining = max(0.0, annual_target - annual_spend)
    annual_progress = min(100.0, round((annual_spend / annual_target) * 100, 1)) if annual_target > 0 else 100.0
    annual_days_left = max(0, (annual_end - as_of).days)
    annual_met = annual_spend >= annual_target

    # Redemptions tracking
    total_points_redeemed = sum(r.get("points_redeemed", 0) for r in redemptions)
    total_value_saved_inr = sum(r.get("value_saved_inr", 0.0) for r in redemptions)
    total_fare_inr = sum(r.get("total_fare", 0.0) for r in redemptions)
    total_cash_paid = sum(r.get("cash_paid", 0.0) for r in redemptions)

    # Net available points = Gross estimated earned - Points redeemed
    net_available_points = max(0, total_estimated_points - total_points_redeemed)

    # Valuation breakdown
    # If quarterly milestone is met, include the 10,000 bonus points
    projected_points_with_bonus = net_available_points + (q_bonus_pts if q_met else 0)
    redemption_values = {
        "smartbuy_travel": {
            "name": "SmartBuy Flights & Hotels",
            "rate_inr": 1.00,
            "total_value_inr": round(projected_points_with_bonus * 1.00, 2),
            "tag": "Maximum Value (Recommended)",
            "icon": "✈️",
        },
        "airmiles": {
            "name": "1:1 Air Miles Transfer",
            "rate_inr": 1.00,
            "total_value_inr": round(projected_points_with_bonus * 1.00, 2),
            "tag": "KrisFlyer, Flying Blue, Club Vistara",
            "icon": "🌐",
        },
        "vouchers": {
            "name": "Instant Gift Vouchers",
            "rate_inr": 0.50,
            "total_value_inr": round(projected_points_with_bonus * 0.50, 2),
            "tag": "Amazon / Brand Vouchers (50p/pt)",
            "icon": "🎁",
        },
        "cashback": {
            "name": "Statement Credit (Cashback)",
            "rate_inr": 0.30,
            "total_value_inr": round(projected_points_with_bonus * 0.30, 2),
            "tag": "Avoid liquidation at only 30p/pt",
            "icon": "💵",
        },
    }

    return {
        "as_of": as_of.isoformat(),
        "card_name": config.get("card_name", "HDFC Diners Black Metal Credit Card"),
        "card_ending": config.get("card_ending", "2360"),
        "sync_metadata": {
            "last_synced": sync_meta.get("synced_at"),
            "alert_count": sync_meta.get("alert_count", len(raw_alerts)),
            "cached_total": sync_meta.get("cached_total", total_tracked_spend),
            "source": sync_meta.get("source", "gmail-api"),
        },
        "caps": {
            "calendar_month": calendar_month_cap,
            "billing_cycle": billing_cycle_cap,
            "previous_month": prev_month_cap,
        },
        "billing_cycle": {
            "start": billing_start.isoformat(),
            "end": billing_end.isoformat(),
            "spend": cycle_spend,
            "transaction_count": len(cycle_txs),
            "base_points": cycle_base_points,
            "accelerated_points": cycle_accelerated_points,
            "total_cycle_points": cycle_base_points + cycle_accelerated_points,
        },
        "points_summary": {
            "total_estimated": total_estimated_points,
            "total_redeemed": total_points_redeemed,
            "net_available": net_available_points,
            "confirmed_statement": confirmed_total_points,
            "post_statement_base": post_stmt_base,
            "post_statement_accelerated": post_stmt_acc,
            "mode": points_evidence_mode,
        },
        "redemptions": redemptions,
        "redemptions_summary": {
            "total_count": len(redemptions),
            "total_points_redeemed": total_points_redeemed,
            "total_value_saved_inr": total_value_saved_inr,
            "total_fare_inr": total_fare_inr,
            "total_cash_paid": total_cash_paid,
        },
        "milestones": {
            "welcome": {
                "target": welcome_target,
                "spend": welcome_spend,
                "progress": welcome_progress,
                "met": welcome_met,
                "remaining": max(0.0, welcome_target - welcome_spend),
                "deadline": welcome_deadline.isoformat(),
                "days_left": welcome_days_left,
                "memberships": welcome_cfg.get("memberships", ["Club Marriott", "Amazon Prime", "Swiggy One"]),
            },
            "quarterly": {
                "label": q_label,
                "target": q_target,
                "spend": q_spend,
                "progress": q_progress,
                "met": q_met,
                "remaining": q_remaining,
                "days_left": q_days_left,
                "bonus_points": q_bonus_pts,
                "daily_runrate_needed": q_required_daily_runrate,
            },
            "annual_waiver": {
                "target": annual_target,
                "fee_amount": annual_fee_amt,
                "spend": annual_spend,
                "progress": annual_progress,
                "met": annual_met,
                "remaining": annual_remaining,
                "days_left": annual_days_left,
                "period_end": annual_end.isoformat(),
            },
        },
        "redemption_values": redemption_values,
        "transactions": transactions,
        "monthly_history": compute_monthly_history(transactions, as_of),
    }


def simulate_spend(
    data: Dict[str, Any],
    spend_amount: float,
    category_key: str,
) -> Dict[str, Any]:
    """Simulate a prospective spend and return point & milestone impact."""
    cat = CATEGORIES.get(category_key, CATEGORIES["general"])
    blocks, base_rp, raw_acc = calculate_points_for_amount(spend_amount, cat)

    # Check against current month cap
    month_cap = data["caps"]["calendar_month"]
    avail_monthly = month_cap["remaining"]
    avail_daily = month_cap["daily_cap"]

    effective_acc = min(raw_acc, avail_daily, avail_monthly)
    capped_reason = []
    if raw_acc > avail_daily:
        capped_reason.append(f"Capped by Daily Limit (max {avail_daily:,} RP/day)")
    if raw_acc > avail_monthly:
        capped_reason.append(f"Capped by Monthly Limit (only {avail_monthly:,} RP headroom left)")

    total_rp = base_rp + effective_acc
    smartbuy_value = round(total_rp * 1.0, 2)
    cash_value = round(total_rp * 0.3, 2)

    # Milestone contributions
    q_spend_now = data["milestones"]["quarterly"]["spend"]
    q_target = data["milestones"]["quarterly"]["target"]
    q_spend_after = q_spend_now + spend_amount
    q_progress_after = min(100.0, round((q_spend_after / q_target) * 100, 1))

    annual_spend_now = data["milestones"]["annual_waiver"]["spend"]
    annual_target = data["milestones"]["annual_waiver"]["target"]
    annual_spend_after = annual_spend_now + spend_amount
    annual_progress_after = min(100.0, round((annual_spend_after / annual_target) * 100, 1))

    return {
        "spend_amount": spend_amount,
        "category_name": cat.name,
        "category_icon": cat.icon,
        "base_points": base_rp,
        "accelerated_points": effective_acc,
        "raw_accelerated_points": raw_acc,
        "total_points": total_rp,
        "is_capped": len(capped_reason) > 0,
        "capped_reasons": capped_reason,
        "effective_reward_rate": round((smartbuy_value / spend_amount) * 100, 2) if spend_amount > 0 else 0.0,
        "value_smartbuy": smartbuy_value,
        "value_cashback": cash_value,
        "quarterly_progress_before": data["milestones"]["quarterly"]["progress"],
        "quarterly_progress_after": q_progress_after,
        "annual_progress_before": data["milestones"]["annual_waiver"]["progress"],
        "annual_progress_after": annual_progress_after,
    }


def trigger_live_sync(card_dir: Path = CARD_DIR) -> Dict[str, Any]:
    """Execute live Gmail synchronization via sync_alerts."""
    import sys
    sys.path.insert(0, str(card_dir))
    import sync_alerts
    return sync_alerts.run(card_dir)
