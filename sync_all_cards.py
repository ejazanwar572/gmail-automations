#!/usr/bin/env python3
"""
Automated Card Sync Runner for HSBC Live+ and HDFC Diners Black Metal.
Intended to run periodically via macOS launchd and managed by MacTask Hub.
"""
from __future__ import annotations

import datetime
from pathlib import Path
import subprocess
import sys


PROJECT_DIR = Path(__file__).resolve().parent
HSBC_DIR = PROJECT_DIR / "HSBC Live Plus Statements"
HDFC_DIR = PROJECT_DIR / "HDFC Diners Black Metal Statements"
LOG_FILE = PROJECT_DIR / "sync_daemon.log"


def log(msg: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def run_card_workflow(card_name: str, card_dir: Path) -> bool:
    workflow_script = card_dir / "run_workflow.py"
    if not workflow_script.exists():
        log(f"⚠️ {card_name}: workflow script not found at {workflow_script}")
        return False
    try:
        proc = subprocess.run(
            [sys.executable, str(workflow_script)],
            cwd=str(card_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            log(f"✅ {card_name}: workflow completed successfully.")
            return True
        else:
            log(f"❌ {card_name}: workflow failed (code {proc.returncode}):\n{proc.stderr.strip() or proc.stdout.strip()}")
            return False
    except Exception as exc:
        log(f"❌ {card_name}: error during workflow run: {exc}")
        return False


def remove_stale_index_lock():
    lock_file = PROJECT_DIR / ".git" / "index.lock"
    if lock_file.exists():
        try:
            res = subprocess.run(["lsof", str(lock_file)], capture_output=True, text=True)
            if not res.stdout.strip():
                lock_file.unlink(missing_ok=True)
                log("ℹ️ Cleaned up orphaned .git/index.lock")
        except Exception:
            pass


def push_changes_if_any() -> bool:
    try:
        remove_stale_index_lock()
        status_proc = subprocess.run(
            ["git", "status", "--porcelain", "HSBC Live Plus Statements", "HDFC Diners Black Metal Statements"],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=15,
        )
        changed_files = [line.strip() for line in status_proc.stdout.splitlines() if line.strip()]
        if not changed_files:
            log("ℹ️ No new alert data or report changes to commit.")
            return True

        log(f"📦 Detected {len(changed_files)} changed files. Committing and pushing to origin...")
        subprocess.run(
            ["git", "add", "HSBC Live Plus Statements", "HDFC Diners Black Metal Statements"],
            cwd=str(PROJECT_DIR),
            check=True,
            timeout=15,
        )
        commit_msg = f"chore(auto-sync): update credit card alert ledgers and reports [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}]"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(PROJECT_DIR),
            check=True,
            timeout=15,
        )
        subprocess.run(
            ["git", "pull", "--rebase", "origin", "main"],
            cwd=str(PROJECT_DIR),
            check=True,
            timeout=30,
        )
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=str(PROJECT_DIR),
            check=True,
            timeout=30,
        )
        subprocess.run(
            ["git", "push", "origin", "main:feature/hsbc-live-plus"],
            cwd=str(PROJECT_DIR),
            check=True,
            timeout=30,
        )
        log("🚀 Successfully synced and pushed latest alert records to GitHub.")
        return True
    except Exception as exc:
        log(f"⚠️ Git push failed or skipped: {exc}")
        return False


def main():
    log("=" * 60)
    log("Starting Credit Card Alert Sync Cycle...")
    hsbc_ok = run_card_workflow("HSBC Live+", HSBC_DIR)
    hdfc_ok = run_card_workflow("HDFC Diners Black Metal", HDFC_DIR)
    if hsbc_ok or hdfc_ok:
        push_changes_if_any()
    log("Sync cycle completed.")
    log("=" * 60)


if __name__ == "__main__":
    main()
