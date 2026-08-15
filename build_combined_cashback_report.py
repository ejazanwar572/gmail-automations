#!/usr/bin/env python3
"""Build a stacked Markdown report from the three card-level cashback reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


BASE_DIR = Path("/Users/ejazanwar/Documents/Gmail Automations")
OUTPUT_PATH = BASE_DIR / "combined_cashback_report.md"


@dataclass(frozen=True)
class CardReport:
    label: str
    badge: str
    path: Path

    @property
    def display_name(self) -> str:
        return f"{self.badge} {self.label}"


CARD_REPORTS = (
    CardReport("SBI Cashback", "🟦", BASE_DIR / "SBI Cashback Statements" / "cashback_cap_report.md"),
    CardReport("Airtel Axis", "🟥", BASE_DIR / "Airtel Axis Statements" / "cashback_cap_report.md"),
    CardReport("Flipkart Axis", "🟨", BASE_DIR / "Flipkart Axis Statements" / "cashback_cap_report.md"),
)


def read_report(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def extract_line(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.replace(prefix, "").strip().strip("*").strip()
    return ""


def extract_executive_summary(text: str) -> str:
    marker = "## 1. Executive Summary"
    start = text.find(marker)
    if start == -1:
        return ""
    next_section = text.find("\n## 2.", start + len(marker))
    section = text[start : next_section if next_section != -1 else len(text)].strip()
    return section.replace(marker, "#### Executive Summary")


def normalize_full_report_heading(card: CardReport, text: str) -> str:
    if not text.startswith("# "):
        return text
    first_newline = text.find("\n")
    return f"### {card.display_name} Full Report{text[first_newline:]}"


def build_report() -> str:
    loaded = [(card, read_report(card.path)) for card in CARD_REPORTS]
    lines = [
        "# Combined Cashback Tracker",
        "",
        "**Account Holder:** Md Ejaz Anwar  ",
        f"**Report Generation Date:** {datetime.now().strftime('%B %-d, %Y')}  ",
        "**Cards Tracked:** 🟦 SBI Cashback, 🟥 Airtel Axis, 🟨 Flipkart Axis",
        "",
        "---",
        "",
        "## 1. Combined Executive Dashboard",
        "| Card | Current Window | Source Report |",
        "| :--- | :--- | :--- |",
    ]

    for card, text in loaded:
        window = extract_line(text, "**Current Statement Period (Ongoing):**")
        if not window:
            window = extract_line(text, "**Current Axis Statement Quarter:**")
        relative_path = card.path.relative_to(BASE_DIR).as_posix().replace(" ", "%20")
        lines.append(f"| {card.display_name} | {window} | [{card.path.parent.name}/cashback_cap_report.md]({relative_path}) |")

    lines.extend(["", "---", "", "## 2. Executive Summaries"])
    for card, text in loaded:
        lines.extend(["", f"### {card.display_name}", "", extract_executive_summary(text)])

    lines.extend(["", "---", "", "## 3. Full Stacked Reports"])
    for index, (card, text) in enumerate(loaded, start=1):
        lines.extend(["", f"### {index}. {card.display_name}", "", normalize_full_report_heading(card, text)])

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    OUTPUT_PATH.write_text(build_report(), encoding="utf-8")
    print(f"Combined report updated successfully: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
