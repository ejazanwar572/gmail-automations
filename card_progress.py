"""Plain-Markdown progress rendering shared by individual card reports."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date, datetime


EVIDENCE_STATES = {"verified", "provisional", "stale", "pending"}


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


def render_progress_bar(current, target, *, width: int = 20) -> str:
    if target is None or float(target) <= 0 or width <= 0:
        return "`Progress unavailable`"
    ratio = min(1.0, max(0.0, float(current or 0) / float(target)))
    filled = int(ratio * width + 0.5)
    return f"`{'█' * filled}{'░' * (width - filled)} {ratio * 100:.1f}%`"


def render_milestone(
    *,
    current,
    target,
    format_value: Callable,
    evidence_state: str = "verified",
    period: str | None = None,
    deadline=None,
    as_of=None,
    supporting_lines: Iterable[str] = (),
) -> str:
    if evidence_state not in EVIDENCE_STATES:
        raise ValueError(f"Unsupported evidence state: {evidence_state}")

    lines = [render_progress_bar(current, target)]
    if period:
        lines.extend(["", f"- Period: {period}"])
    if as_of is not None:
        milestone_met = target is not None and float(target) > 0 and float(current or 0) >= float(target)
        lines.extend(["", f"- {render_days_left(deadline=deadline, as_of=as_of, milestone_met=milestone_met)}"])
    if target is None or float(target) <= 0:
        lines.extend(["", "- Progress: Pending", "- Remaining: Pending", "- Status: Pending"])
    else:
        current_value = max(0.0, float(current or 0))
        target_value = float(target)
        remaining = max(0.0, target_value - current_value)
        exceeded = max(0.0, current_value - target_value)
        lines.extend([
            "",
            f"- Progress: {format_value(current_value)} of {format_value(target_value)}",
            f"- Remaining: {format_value(remaining)}",
        ])
        if exceeded:
            lines.append(f"- Exceeded by: {format_value(exceeded)}")
        lines.append(f"- Status: {'Met' if current_value >= target_value else 'In progress'}")
    if evidence_state != "verified":
        lines.append(f"- Evidence: {evidence_state.title()}")
    lines.extend(f"- {line}" for line in supporting_lines)
    return "\n".join(lines)
