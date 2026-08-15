#!/usr/bin/env python3
"""Combined runner for all cashback tracker workflows."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from verify_cashback_reports import CARD_REPORTS, verify_reports


BASE_DIR = Path("/Users/ejazanwar/Documents/Gmail Automations")
PYTHON_BIN = Path("/Users/ejazanwar/.pyenv/versions/3.12.2/bin/python3")


@dataclass(frozen=True)
class CardWorkflow:
    name: str
    folder: str

    @property
    def directory_name(self) -> str:
        return self.folder


CARDS = (
    CardWorkflow("Airtel Axis", "Airtel Axis Statements"),
    CardWorkflow("Flipkart Axis", "Flipkart Axis Statements"),
    CardWorkflow("SBI Cashback", "SBI Cashback Statements"),
)


@dataclass
class StepResult:
    name: str
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def output(self) -> str:
        return "\n".join(part for part in (self.stdout, self.stderr) if part).strip()


@dataclass
class WorkflowResult:
    mode: str
    steps: list[StepResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 1 if self.failures else 0

    def add_step(self, step: StepResult) -> None:
        self.steps.append(step)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def summary(self) -> str:
        lines = [f"Combined cashback workflow mode: {self.mode}"]
        if self.steps:
            lines.append("Steps:")
            for step in self.steps:
                status = "OK" if step.ok else f"FAILED ({step.returncode})"
                lines.append(f"- {status}: {step.name}")
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in self.warnings)
        if self.failures:
            lines.append("Failures:")
            lines.extend(f"- {failure}" for failure in self.failures)
        return "\n".join(lines)


def run_script(name: str, script: Path, cwd: Path, python_bin: Path) -> StepResult:
    if not script.exists():
        return StepResult(name=name, returncode=127, stderr=f"Missing script: {script}")
    completed = subprocess.run(
        [str(python_bin), str(script)],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    return StepResult(
        name=name,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def report_paths(base_dir: Path) -> list[Path]:
    return [base_dir / card.folder / card.filename for card in CARD_REPORTS]


def fingerprint(path: Path) -> str:
    if not path.exists():
        return "missing"
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def snapshot_reports(paths: list[Path]) -> dict[Path, str]:
    return {path: fingerprint(path) for path in paths}


def merge_gmail_step_logs(base_dir: Path, python_bin: Path, result: WorkflowResult) -> None:
    for card in CARDS:
        card_dir = base_dir / card.folder
        step = run_script(
            f"Merge cached Gmail/MCP step logs for {card.name}",
            card_dir / "sync_gmail_mcp.py",
            card_dir,
            python_bin,
        )
        result.add_step(step)
        if not step.ok:
            result.warn(f"{card.name}: Gmail/MCP step-log merge unavailable; continuing with existing alert cache")


def run_local_api_sync(base_dir: Path, python_bin: Path, result: WorkflowResult) -> None:
    for card in CARDS:
        card_dir = base_dir / card.folder
        step = run_script(f"Local Gmail API sync for {card.name}", card_dir / "sync_alerts.py", card_dir, python_bin)
        result.add_step(step)
        if not step.ok:
            output = step.output()
            if any(token in output.lower() for token in ("invalid_grant", "captcha", "otp", "manual")):
                result.fail(f"{card.name}: Gmail authentication/manual approval is required; stop and refresh auth")
            else:
                result.fail(f"{card.name}: local Gmail API sync failed")
            return


def validate_cards(base_dir: Path, python_bin: Path, result: WorkflowResult) -> None:
    for card in CARDS:
        card_dir = base_dir / card.folder
        step = run_script(f"Validate statements for {card.name}", card_dir / "validate_statements.py", card_dir, python_bin)
        result.add_step(step)
        if not step.ok:
            output = step.output()
            if card.name == "Airtel Axis" and "944" in output:
                result.warn("Airtel Axis: known January 2026 944.0 alert/PDF mismatch remains in validation output")
            else:
                result.warn(f"{card.name}: validation returned exit code {step.returncode}; review validation output")


def update_card_reports(base_dir: Path, python_bin: Path, result: WorkflowResult) -> None:
    for card in CARDS:
        card_dir = base_dir / card.folder
        step = run_script(f"Regenerate card report for {card.name}", card_dir / "update_report.py", card_dir, python_bin)
        if not step.ok and card.name == "SBI Cashback" and "No module named 'pypdf'" in step.output():
            result.warn("SBI Cashback: pypdf import failed once; retrying update_report.py")
            result.add_step(step)
            step = run_script(f"Regenerate card report for {card.name} (retry)", card_dir / "update_report.py", card_dir, python_bin)
        result.add_step(step)
        if not step.ok:
            result.fail(f"{card.name}: update_report.py failed with exit code {step.returncode}")
            return


def compile_aggregate(base_dir: Path, python_bin: Path, result: WorkflowResult) -> None:
    step = run_script("Compile aggregate cashback report", base_dir / "aggregate_report.py", base_dir, python_bin)
    result.add_step(step)
    if not step.ok:
        result.fail(f"Aggregate compiler failed with exit code {step.returncode}")


def compile_stacked_report(base_dir: Path, python_bin: Path, result: WorkflowResult) -> None:
    script = base_dir / "build_combined_cashback_report.py"
    if not script.exists():
        result.warn("Combined stacked report builder not found; skipped combined_cashback_report.md")
        return
    step = run_script("Compile stacked combined cashback report", script, base_dir, python_bin)
    result.add_step(step)
    if not step.ok:
        result.fail(f"Stacked combined report compiler failed with exit code {step.returncode}")


def compile_benefit_report(base_dir: Path, python_bin: Path, result: WorkflowResult) -> None:
    script = base_dir / "build_combined_card_benefits_report.py"
    if not script.exists():
        result.warn("Combined card benefits report builder not found; skipped combined_card_benefits_report.md")
        return
    step = run_script("Compile combined card benefits report", script, base_dir, python_bin)
    result.add_step(step)
    if not step.ok:
        result.fail(f"Combined card benefits report compiler failed with exit code {step.returncode}")


def run_verifier(base_dir: Path, scope: str, result: WorkflowResult) -> None:
    verification = verify_reports(base_dir=base_dir, scope=scope)
    if verification.warnings:
        result.warnings.extend(verification.warnings)
    if verification.failures:
        result.fail(f"Format verification failed for scope {scope}:\n{verification.summary()}")


def run_workflow(
    mode: str = "aggregate-safe",
    base_dir: str | Path = BASE_DIR,
    python_bin: str | Path = PYTHON_BIN,
    sync_source: str = "mcp-step-logs",
) -> WorkflowResult:
    base = Path(base_dir)
    py = Path(python_bin)
    result = WorkflowResult(mode=mode)

    if mode not in {"aggregate-safe", "full-refresh"}:
        result.fail(f"Unsupported mode: {mode}")
        return result
    if sync_source not in {"mcp-step-logs", "local-api", "none"}:
        result.fail(f"Unsupported sync source: {sync_source}")
        return result

    card_reports_before = snapshot_reports(report_paths(base))

    if sync_source == "mcp-step-logs":
        merge_gmail_step_logs(base, py, result)
    elif sync_source == "local-api":
        run_local_api_sync(base, py, result)
        if result.failures:
            return result

    validate_cards(base, py, result)

    if mode == "full-refresh":
        update_card_reports(base, py, result)
        if result.failures:
            return result
        run_verifier(base, "cards", result)
        if result.failures:
            return result

    compile_aggregate(base, py, result)
    if result.failures:
        return result
    compile_stacked_report(base, py, result)
    if result.failures:
        return result
    compile_benefit_report(base, py, result)
    if result.failures:
        return result

    if mode == "aggregate-safe":
        card_reports_after = snapshot_reports(report_paths(base))
        changed = [str(path) for path, before in card_reports_before.items() if card_reports_after[path] != before]
        if changed:
            result.fail("Aggregate-safe mode changed individual card reports: " + ", ".join(changed))
            return result

    run_verifier(base, "aggregate", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the combined cashback tracker workflow.")
    parser.add_argument("--mode", choices=("aggregate-safe", "full-refresh"), default="aggregate-safe")
    parser.add_argument(
        "--sync-source",
        choices=("mcp-step-logs", "local-api", "none"),
        default="mcp-step-logs",
        help="mcp-step-logs merges cached Gmail connector output; local-api is fallback only.",
    )
    parser.add_argument("--base-dir", default=str(BASE_DIR))
    parser.add_argument("--python-bin", default=str(PYTHON_BIN))
    args = parser.parse_args()

    result = run_workflow(
        mode=args.mode,
        base_dir=Path(args.base_dir),
        python_bin=Path(args.python_bin),
        sync_source=args.sync_source,
    )
    print(result.summary())
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
