# Gmail Automations & Job Matcher Suite

A comprehensive personal utility suite that automates finance tracking (credit card statement validations, cashbacks, and expenses) and runs a scheduled career portal scraper that evaluates job listings against your target resume using the Gemini API.

---

## Repository Overview

This repository contains several automated pipelines organized into modular scripts:

### 1. 💼 Job Matcher & Scraper
* **Scraper (`check_job_boards.py`)**: Crawls 17 different career portals across Greenhouse, Phenom, Jibe, Workday, SmartRecruiters, WordPress, and custom HTML platforms. It utilizes location pre-filtering (prioritizing Bangalore first, then India/Remote) to minimize network requests.
* **AI Matcher (`evaluate_jobs_github.py`)**: Executes the scraper, reads new listings, scores them (0-100) against your resume, logs run history to `job_matches_report.md`, and sends a premium HTML email brief for high-matching roles (&ge; 70%).
* **Automation (`.github/workflows/job_matcher.yml`)**: GitHub Actions workflow that executes the pipeline automatically every 2 hours and commits database changes back to the repository.

### 2. 💳 Credit Card Bill & Cashback Trackers
* **Axis Airtel & Flipkart CC (`Airtel Axis Statements/` & `Flipkart Axis Statements/`)**: Syncs transaction alerts from Gmail, downloads billing statements, validates transactions against PDF line-items, and generates cashback cap progress reports.
* **SBI Cashback CC (`SBI Cashback Statements/`)**: Automatically validates and maps cashback alerts against downloaded statement PDFs to track spend caps.
* **Cashback Workflow (`combined_cashback_workflow.py`)**: Unifies the execution of multiple cashback validations.

### 3. 📊 Expense Tracker & Dashboard
* **Expense Ledger (`ai_expense_tracker.py` & `local_expense_tracker.py`)**: Programmatically parses UPI debit and payment emails to maintain a local SQLite expense database.
* **Visual Dashboard (`dashboard.py`)**: Web-based analytical dashboard displaying card spends, categories, remaining cap limits, and matching job listings.

---

## Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ejazanwar572/gmail-automations.git
   cd gmail-automations
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your actual values:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   * `SBI_CASHBACK_PASSWORD` / `AIRTEL_AXIS_PASSWORD`: Passwords to decrypt statement PDFs.
   * `GEMINI_API_KEY`: Your Google Gemini API Key.
   * `SENDER_EMAIL` / `SENDER_PASSWORD`: Your Gmail email and its 16-character App Password.

3. **Install Dependencies**:
   ```bash
   pip install google-generativeai
   ```

4. **Run Job Matcher Locally**:
   ```bash
   python evaluate_jobs_github.py
   ```

---

## GitHub Actions Scheduling Setup

To automate the Job Matcher run every 2 hours:

1. **Repository Settings**:
   Go to your GitHub repository on the web: **Settings** &rarr; **Secrets and variables** &rarr; **Actions**.
2. **Add Secrets**:
   Click **New repository secret** and configure:
   * `GEMINI_API_KEY`: Your Google Gemini API key.
   * `SENDER_EMAIL`: The Gmail address used to send briefs (e.g. `anwar.ejaz181@gmail.com`).
   * `SENDER_PASSWORD`: The 16-character Gmail App Password (no spaces).
   * `RECEIVER_EMAIL` (Optional): The recipient email (defaults to `anwar.ejaz181@gmail.com`).
3. **Configure Permissions**:
   Go to **Settings** &rarr; **Actions** &rarr; **General** &rarr; **Workflow permissions**, select **"Read and write permissions"**, and click **Save**. This allows the Actions runner to commit database updates back to `scraped_jobs.json`.
