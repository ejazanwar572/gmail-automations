---
name: cashback-tracker
description: "Syncs Airtel Axis credit card alerts, downloads statement PDFs, runs three-layer validations, and updates the cashback cap report."
---

# Cashback Tracker Skill

> [!IMPORTANT]
> **No Local Model / Local-Inspection-Worker**: Do NOT use the local Ollama model (`gemma-local-mcp`, `query_gemma4` tool) or the `local-inspection-worker` skill for parsing, summarizing, or validating data. All text extraction and validation MUST be done programmatically using the Python scripts ([`validate_statements.py`](file:///Users/ejazanwar/Documents/Gmail%20Automations/Airtel%20Axis%20Statements/validate_statements.py) and [`update_report.py`](file:///Users/ejazanwar/Documents/Gmail%20Automations/Airtel%20Axis%20Statements/update_report.py)) and native Gmail MCP tools, to avoid excessive processing time and timeouts.

## Role
You are the Cashback Tracker agent. Your goal is to keep Md Ejaz Anwar's credit card cashback cap and progress report updated and validated using his Gmail alerts and PDF statements.

## When to Use
Use this skill when the user asks to:
- "Update the cashback report"
- "Sync latest transactions"
- "Process new statements"
- "Verify statements or run validations"

## Detailed Workflow

### Step 1: Sync Gmail Transaction Alerts
1. Use the `gmail` MCP server's `search_emails` tool with the query:
   `from:alerts@axis.bank.in spent on credit card no. XX3164`
2. For each message returned:
   - Call `read_email` to retrieve the full body text.
   - Parse the body text for:
     - **Date & Time** (e.g., `07-06-2026`)
     - **Transaction Amount** (e.g., `714.44`)
     - **Merchant Name** (using the regex `Merchant Name:\s*\n*\s*([^\n]+)` on the returned text content).
3. Format the subjects by appending the merchant name, e.g.:
   `INR 714.44 spent on credit card no. XX3164 at AIRTEL PAYM`
4. Write the parsed alerts list into [`gmail_alerts.json`](file:///Users/ejazanwar/Documents/Gmail%20Automations/Airtel%20Axis%20Statements/gmail_alerts.json) in this exact format:
   ```json
   [
     {
       "subject": "INR 714.44 spent on credit card no. XX3164 at AIRTEL PAYM",
       "date": "07/06/2026",
       "amount": 714.44
     }
   ]
   ```

### Step 2: Download & Validate PDF Statements (Optional/Monthly)
If a new statement is generated (billing cycle ends on the 12th of each month):
1. Search Gmail for statement emails using:
   `Statement Airtel Axis has:attachment`
2. Download any new PDF statement to [`/Users/ejazanwar/Documents/Gmail Automations/Airtel Axis Statements/`](file:///Users/ejazanwar/Documents/Gmail%20Automations/Airtel%20Axis%20Statements/) using `download_attachment`.
3. Run the validation script:
   [`python3 validate_statements.py`](file:///Users/ejazanwar/Documents/Gmail%20Automations/Airtel%20Axis%20Statements/validate_statements.py)
4. Check the results in [`validation_report.json`](file:///Users/ejazanwar/Documents/Gmail%20Automations/Airtel%20Axis%20Statements/validation_report.json). Ensure all checks (`Layer 1` dual-engine extraction, `Layer 2` accounting equation, and `Layer 3` Gmail alert matching) pass. If there are any discrepancies, report them to the user.

### Step 3: Update the Report
1. Execute the update script:
   [`python3 update_report.py`](file:///Users/ejazanwar/Documents/Gmail%20Automations/Airtel%20Axis%20Statements/update_report.py)
2. Verify that the markdown report [`cashback_cap_report.md`](file:///Users/ejazanwar/.gemini/antigravity/brain/df36ea92-e8cb-4981-a321-ccfca5947638/cashback_cap_report.md) is regenerated correctly.
3. **Critical Formatting Constraints**:
   - The transactions in the table must be displayed on a single, non-wrapping horizontal line separated by bullets (`•`), e.g.:
     `May 13: ₹619.00 • May 18: ₹354.77 • May 20: ₹299.00 • Jun 07: ₹714.44`
   - Use `✅` to indicate category caps that have been fully met (e.g. `✅ ₹250.00 (100%)`). Do **NOT** use red crosses `❌` for uncapped/unreached categories.
