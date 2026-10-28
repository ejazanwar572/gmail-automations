#!/usr/bin/env python3
"""Deterministic format checks for the cashback tracker Markdown reports."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path


BASE_DIR = Path("/Users/ejazanwar/Documents/Gmail Automations")
AGGREGATE_REPORT = "aggregate_cashback_report.md"
AGGREGATE_SCRIPT = "aggregate_report.py"


@dataclass(frozen=True)
class CardReport:
    name: str
    folder: str
    filename: str
    total_cap: str


CARD_REPORTS = (
    CardReport("Airtel Axis", "Airtel Axis Statements", "cashback_cap_report.md", "\u20b91,000.00"),
    CardReport("Flipkart Axis", "Flipkart Axis Statements", "cashback_cap_report.md", "\u20b912,000.00"),
    CardReport("SBI Cashback", "SBI Cashback Statements", "cashback_cap_report.md", "\u20b94,000.00"),
)


@dataclass
class VerificationResult:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def summary(self) -> str:
        lines: list[str] = []
        if self.failures:
            lines.append("Failures:")
            lines.extend(f"- {item}" for item in self.failures)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"- {item}" for item in self.warnings)
        if not lines:
            return "All cashback report format checks passed."
        return "\n".join(lines)


def read_text(path: Path, result: VerificationResult, label: str) -> str | None:
    if not path.exists():
        result.fail(f"{label}: missing file at {path}")
        return None
    return path.read_text(encoding="utf-8")


def check_no_raw_html_or_templates(text: str, result: VerificationResult, label: str) -> None:
    raw_html_tokens = ("<br", "<span", "</span>")
    if any(token.lower() in text.lower() for token in raw_html_tokens):
        result.fail(f"{label}: raw HTML fragments found in report")
    template_tokens = ("{format_money", "{format_amount", "format_money(", "format_amount(")
    if any(token in text for token in template_tokens):
        result.fail(f"{label}: unresolved template literal found in report")


def check_aggregate(base_dir: Path, result: VerificationResult) -> None:
    report_path = base_dir / AGGREGATE_REPORT
    report = read_text(report_path, result, "Aggregate report")
    if report is None:
        return

    check_no_raw_html_or_templates(report, result, "Aggregate report")

    required_monthly_header = (
        "| Month | Airtel Axis Spend | Airtel Axis Cashback | Flipkart Axis Spend | "
        "Flipkart Axis Cashback | SBI Cashback Spend | SBI Cashback Earned | "
        "Total Spends | Total Cashback Earned | Effective Cashback Rate |"
    )
    if required_monthly_header not in report:
        result.fail("Aggregate report: monthly table must use explicit spend and cashback columns for each card")

    required_ytd_header = "| Metric | Airtel Axis | Flipkart Axis | SBI Cashback | Total |"
    if required_ytd_header not in report:
        result.fail("Aggregate report: Card-wise Contribution table must be transposed")

    for row in (
        "**Cumulative Spends**",
        "**Cumulative Cashback**",
        "**Share of Total Spends**",
        "**Share of Total Cashback**",
        "**Effective Rate**",
    ):
        if row not in report:
            result.fail(f"Aggregate report: missing transposed YTD row {row}")

    pushy_phrases = ("spend more", "must spend", "should spend more")
    lower_report = report.lower()
    for phrase in pushy_phrases:
        if phrase in lower_report:
            result.fail(f"Aggregate report: pushy recommendation phrase found: {phrase!r}")

    script = read_text(base_dir / AGGREGATE_SCRIPT, result, "Aggregate compiler")
    if script is not None:
        forbidden_output_paths = (".gemini", "antigravity", "CONVO_REPORT_PATH")
        if any(token in script for token in forbidden_output_paths):
            result.fail("Aggregate compiler: non-canonical output path reference found")


def section_between(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start == -1:
        return ""
    end = text.find(end_marker, start + len(start_marker))
    if end == -1:
        return text[start:]
    return text[start:end]


def check_card_report(base_dir: Path, card: CardReport, result: VerificationResult) -> None:
    path = base_dir / card.folder / card.filename
    report = read_text(path, result, f"{card.name} report")
    if report is None:
        return

    check_no_raw_html_or_templates(report, result, f"{card.name} report")

    summary_section = section_between(
        report,
        "## 3. June 2026 Spends & Cap Progress",
        "## 4. June 2026 Transaction Details",
    )
    if not summary_section:
        result.fail(f"{card.name} report: missing compact June cap progress section")
    else:
        if "Tracked Transactions" not in summary_section:
            result.fail(f"{card.name} report: cap progress table missing Tracked Transactions column")
        total_row = f"| **Total** | **{card.total_cap}** |"
        if total_row not in summary_section:
            result.fail(f"{card.name} report: missing Total row with expected cap {card.total_cap}")
        for line in summary_section.splitlines():
            if line.startswith("|") and "Transaction Details" in line:
                result.fail(f"{card.name} report: transaction details leaked into cap summary table")

    details_section = report.find("## 4. June 2026 Transaction Details")
    details_header = "| Date | Category | Amount | Merchant |"
    if details_section == -1 or details_header not in report[details_section:]:
        result.fail(f"{card.name} report: missing transaction details table")


def check_cards(base_dir: Path, result: VerificationResult) -> None:
    for card in CARD_REPORTS:
        check_card_report(base_dir, card, result)


def verify_reports(base_dir: str | Path = BASE_DIR, scope: str = "all") -> VerificationResult:
    base = Path(base_dir)
    result = VerificationResult()
    if scope not in {"aggregate", "cards", "all"}:
        result.fail(f"Unknown verification scope: {scope}")
        return result
    if scope in {"aggregate", "all"}:
        check_aggregate(base, result)
    if scope in {"cards", "all"}:
        check_cards(base, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify cashback report Markdown formatting.")
    parser.add_argument("--base-dir", default=str(BASE_DIR), help="Gmail Automations root directory")
    parser.add_argument("--scope", choices=("aggregate", "cards", "all"), default="all")
    args = parser.parse_args()

    result = verify_reports(base_dir=Path(args.base_dir), scope=args.scope)
    print(result.summary())
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
