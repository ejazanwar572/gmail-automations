# Graph Report - Gmail Automations  (2026-06-08)

## Corpus Check
- 14 files · ~9,658 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 108 nodes · 130 edges · 14 communities (11 shown, 3 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e67e7c0a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]

## God Nodes (most connected - your core abstractions)
1. `run_validation()` - 11 edges
2. `run_validation()` - 9 edges
3. `main()` - 4 edges
4. `update_report()` - 4 edges
5. `main()` - 4 edges
6. `update_report()` - 4 edges
7. `Cashback Tracker Skill` - 4 edges
8. `Detailed Workflow` - 4 edges
9. `main()` - 3 edges
10. `run_step()` - 3 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (14 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.14
Nodes (20): extract_key_fields_pdftotext(), extract_key_fields_pypdf(), extract_pdftotext(), extract_pypdf(), get_cycle_end_date(), get_env_password(), get_mapped_alerts(), get_next_month() (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.15
Nodes (18): extract_key_fields_pdftotext(), extract_key_fields_pypdf(), extract_pdftotext(), extract_pypdf(), get_env_password(), get_mapped_alerts(), grab_amounts(), Extracts key fields from vertical pdftotext layout. (+10 more)

### Community 2 - "Community 2"
Cohesion: 0.27
Nodes (10): calculate_statement_cashback(), categorize_transaction(), clean_desc(), format_bullet_points(), get_env_password(), get_statement_transactions(), load_json(), Parses transaction list from PDF statement. (+2 more)

### Community 3 - "Community 3"
Cohesion: 0.36
Nodes (7): clean_html(), get_gmail_service(), get_message_body(), main(), Authenticates and returns the Gmail service object., Recursively extracts the text body from the message payload., Strips HTML tags and normalizes whitespace.

### Community 4 - "Community 4"
Cohesion: 0.25
Nodes (7): Cashback Tracker Skill, Detailed Workflow, Role, Step 1: Sync Gmail Transaction Alerts, Step 2: Download & Validate PDF Statements (Optional/Monthly), Step 3: Update the Report, When to Use

### Community 5 - "Community 5"
Cohesion: 0.36
Nodes (7): clean_html(), get_gmail_service(), get_message_body(), main(), Strips HTML tags and normalizes whitespace., Authenticates and returns the Gmail service object., Recursively extracts the text body from the message payload.

### Community 6 - "Community 6"
Cohesion: 0.38
Nodes (6): format_bullet_points(), load_json(), Loads data from a JSON file., Formats a list of transactions into a bulleted string., Main function to process alerts and generate the report., update_report()

### Community 7 - "Community 7"
Cohesion: 0.47
Nodes (5): extract_text(), get_env_password(), main(), parse(), Loads a password from environment variable, falling back to a root-level .env fi

### Community 8 - "Community 8"
Cohesion: 0.67
Nodes (3): main(), Helper to execute a step in the workflow., run_step()

### Community 9 - "Community 9"
Cohesion: 0.67
Nodes (3): main(), Helper to execute a step in the workflow., run_step()

### Community 10 - "Community 10"
Cohesion: 0.83
Nodes (3): clean_html(), main(), parse_date_str()

## Knowledge Gaps
- **7 isolated node(s):** `Role`, `When to Use`, `Step 1: Sync Gmail Transaction Alerts`, `Step 2: Download & Validate PDF Statements (Optional/Monthly)`, `Step 3: Update the Report` (+2 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `Loads a password from environment variable, falling back to a root-level .env fi`, `Helper to execute a step in the workflow.`, `Authenticates and returns the Gmail service object.` to the rest of the system?**
  _39 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.1380952380952381 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.14619883040935672 - nodes in this community are weakly interconnected._