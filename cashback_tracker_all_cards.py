#!/usr/bin/env python3
"""Friendly entrypoint for running all cashback card tracker workflows."""

from __future__ import annotations

from combined_cashback_workflow import (
    BASE_DIR,
    PYTHON_BIN,
    CARDS,
    CardWorkflow,
    StepResult,
    WorkflowResult,
    compile_aggregate,
    compile_benefit_report,
    compile_stacked_report,
    fingerprint,
    main,
    merge_gmail_step_logs,
    report_paths,
    run_local_api_sync,
    run_script,
    run_verifier,
    run_workflow,
    snapshot_reports,
    update_card_reports,
    validate_cards,
)


if __name__ == "__main__":
    raise SystemExit(main())
