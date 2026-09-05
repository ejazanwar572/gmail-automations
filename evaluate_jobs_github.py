import subprocess
import sys
import json
import os
import time
from datetime import datetime

RESUME = """
# Ejaz Anwar
Email: anwar.ejaz181@gmail.com | Phone: +91 9024293714 | LinkedIn | Notice Period: 1 Month

## Professional Summary
Lead AI Analyst with 8+ years of experience in product analytics, designing A/B tests, causal inference, and translating product data into roadmap and growth decisions across Impact Analytics, PayPal, OLX Autos, and Uber. Strong in SQL, Python, experiment design, funnel analysis, LLM workflows, and data storytelling.

## Target Roles
- Lead AI Analyst
- Analytics Lead
- Senior Product Analyst
- Principal Analyst
- Analytics Manager

## Work Experience
### Lead AI Analyst - Impact Analytics (Bangalore | 04/26 - Present)
- Built functional AI and data prototypes using Python, Pandas, Streamlit/Jupyter, and automated workflows to convert analytical diagnoses into repeatable internal tooling.
- Diagnosed business metric variance using SQL, cohort analysis, A/B testing, and mix-vs-rate decomposition, translating findings into explainable LLM/agent-enabled workflows.

### Senior Product Analyst - PayPal (Bangalore | 04/23 - 03/26)
- Designed and analyzed 12+ A/B experiments for PayPal Shopping surfaces, influencing roadmap decisions across checkout, offers, and user engagement initiatives.
- Applied statistical analysis, predictive modelling, and causal inference to evaluate PayPal Shopping opportunities, helping Product teams prioritize roadmap bets and measure user and business impact.
- Mentored 4 analysts on SQL, Python best practices, and experimental design to improve analytical quality and experimentation rigor.

### Product Analyst - OLX Autos (Gurgaon | 07/22 - 03/23)
- Reduced Zero Result Pages (ZRP) by 15% through data-driven A/B testing and user behavior analytics, improving search engagement.
- Led analytics for the car comparison feature launch, driving a 10% increase in lead generation and supporting product growth initiatives.

### Business Analyst - Uber (Hyderabad | 08/21 - 07/22)
- Automated 35+ recurring BAU reports using Python, improving reporting reliability and saving 250+ analyst hours annually.
- Built a dynamic U4B dashboard using Power BI and Google Sheets, automating daily data refreshes and improving reporting access for business stakeholders.

### Analyst - Aditya Birla Group (Bangalore | 07/18 - 07/21)
- Analyzed yield, process efficiency, and inventory data for production and operations teams, identifying operational bottlenecks and recommending cost-saving improvements across plant workflows.

## Education
- BITS Pilani (2014 - 2018): B.Tech - Chemical Engineering

## Skills
- **Analytics:** SQL, Python, PySpark, A/B Testing, Experiment Design, Funnel Analysis, Statistical Analysis, Predictive Modelling, Causal Inference, ETL, Causal Methods.
- **Tools & Platforms:** Tableau, Power BI, Looker, BigQuery, Databricks, Airflow, Streamlit, Gradio, Jupyter, Google Analytics, Adobe Analytics, CleverTap, JIRA, Git.
- **Product & Business:** Product Metrics, User Behavior Analytics, LLM/Agent Workflows, RAG Concepts, Forecasting, Cross-functional Collaboration, Stakeholder Management, Data Storytelling.

## Certifications
- Google Data Analytics Certificate - Coursera
"""

def send_email_brief(high_matches):
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_pwd = os.environ.get("SENDER_PASSWORD")
    receiver_email = os.environ.get("RECEIVER_EMAIL")
    if not receiver_email or not receiver_email.strip():
        receiver_email = "anwar.ejaz181@gmail.com"
    
    if not sender_email or not sender_pwd:
        print("Sender email/password secrets not set. Skipping email briefing.", file=sys.stderr)
        return
        
    subject = f"Incremental Job Match Brief - {len(high_matches)} High-Match Roles Found!"
    
    # Build HTML vertical cards of roles
    cards_html = ""
    for m in high_matches:
        matches_html = "".join([f"<li style='margin-bottom: 4px;'>{x}</li>" for x in m["key_matches"]])
        
        badge_bg = "#e6f4ea" if m["score"] >= 85 else "#e8f0fe"
        badge_color = "#137333" if m["score"] >= 85 else "#1a73e8"
        
        cards_html += f"""
        <div style="background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.03);">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="vertical-align: top;">
                        <a href="{m['url']}" style="font-size: 18px; font-weight: 700; color: #1a73e8; text-decoration: none; line-height: 1.3;">{m['title']}</a>
                    </td>
                    <td style="vertical-align: top; text-align: right; width: 85px;">
                        <span style="background-color: {badge_bg}; color: {badge_color}; padding: 6px 12px; border-radius: 16px; font-size: 14px; font-weight: 700; display: inline-block;">{m['score']}/100</span>
                    </td>
                </tr>
            </table>
            
            <div style="margin-top: 8px; font-size: 14px; color: #5f6368; font-weight: 500;">
                <span style="color: #202124; font-weight: 600;">{m['company']}</span> &nbsp;•&nbsp; 📍 {m['location']}
            </div>
            
            <hr style="border: none; border-top: 1px solid #f1f3f4; margin: 14px 0;">
            
            <div style="font-size: 14px; color: #3c4043;">
                <ul style="margin: 0; padding-left: 18px; line-height: 1.7; color: #202124;">
                    {matches_html}
                </ul>
            </div>
            
            <div style="margin-top: 16px; text-align: right;">
                <a href="{m['url']}" style="background-color: #1a73e8; color: #ffffff; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; text-decoration: none; display: inline-block;">Apply on {m['company']} &rarr;</a>
            </div>
        </div>
        """
        
    body_html = f"""
    <html>
    <body style="font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #202124; line-height: 1.5; background-color: #f4f6f9; padding: 20px; margin: 0;">
        <div style="max-width: 680px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e0e0e0;">
            <div style="background: linear-gradient(135deg, #1a73e8 0%, #1557b0 100%); padding: 24px 28px; color: #ffffff;">
                <h1 style="margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0.3px;">💼 Job Matcher Daily Brief</h1>
                <p style="margin: 6px 0 0 0; opacity: 0.95; font-size: 14px;">Found {len(high_matches)} roles matching your profile (Score &ge; 70%)</p>
            </div>
            <div style="padding: 24px;">
                <p style="font-size: 15px; color: #3c4043; margin-top: 0; margin-bottom: 20px;">Hi Ejaz, here are the top matching opportunities from your automated scan:</p>
                
                {cards_html}
                
                <p style="font-size: 13px; color: #70757a; margin-top: 24px;">All opportunities are tracked in <code>job_matches_report.md</code> in your repository.</p>
            </div>
            <div style="background-color: #f8f9fa; border-top: 1px solid #e0e0e0; padding: 14px; text-align: center; font-size: 12px; color: #5f6368;">
                Automated Job Matcher Brief • Sent via GitHub Actions
            </div>
        </div>
    </body>
    </html>
    """
    
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))
        
        print(f"Connecting to SMTP server to send brief to {receiver_email}...", file=sys.stderr)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_pwd)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!", file=sys.stderr)
    except Exception as e:
        print(f"Failed to send email via SMTP: {e}", file=sys.stderr)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scraper_path = os.path.join(script_dir, "check_job_boards.py")
    
    # 1. Run the scraper
    print("Running scraper script...", file=sys.stderr)
    result = subprocess.run(
        [sys.executable, scraper_path],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Scraper failed with exit code {result.returncode}", file=sys.stderr)
        print("Scraper Stderr:", result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
        
    try:
        data = json.loads(result.stdout)
        new_jobs = data.get("new_jobs", [])
    except Exception as e:
        print(f"Failed to parse scraper output: {e}", file=sys.stderr)
        print("Scraper stdout was:", result.stdout, file=sys.stderr)
        sys.exit(1)
        
    print(f"Scraper found {len(new_jobs)} new jobs.", file=sys.stderr)
    
    if not new_jobs and os.environ.get("SEND_TEST_EMAIL") != "true":
        print("No new jobs to process. Exiting.", file=sys.stderr)
        sys.exit(0)
        
    # 2. Configure Gemini API
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
        
    try:
        import google.generativeai as genai
    except ImportError:
        print("Installing google-generativeai package...", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai"])
        import google.generativeai as genai
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    evaluated_matches = []
    quota_exhausted = False
    api_calls_made = 0
    
    # 3. Evaluate each new job
    for idx, job in enumerate(new_jobs):
        title = job.get("title", "Unknown Title")
        url = job.get("url", "#")
        company = job.get("company", "")
        location = job.get("location", "Unknown Location")
        desc_text = job.get("description_text", "")
        
        if not company:
            sb = (job.get("source_board") or "").lower()
            url_lower = url.lower()
            combined_ref = f"{sb} {url_lower}"
            
            if "amazon" in combined_ref:
                company = "Amazon"
            elif "walmart" in combined_ref:
                company = "Walmart"
            elif "meesho" in combined_ref:
                company = "Meesho"
            elif "postman" in combined_ref:
                company = "Postman"
            elif "uber" in combined_ref:
                company = "Uber"
            elif "tide.co" in combined_ref or "tide" in combined_ref:
                company = "Tide"
            elif "gartner" in combined_ref:
                company = "Gartner"
            elif "adobe" in combined_ref:
                company = "Adobe"
            elif "salesforce" in combined_ref:
                company = "Salesforce"
            elif "nutanix" in combined_ref:
                company = "Nutanix"
            elif "ebay" in combined_ref:
                company = "eBay"
            elif "pepsico" in combined_ref:
                company = "PepsiCo"
            elif "spglobal" in combined_ref or "s&p" in combined_ref:
                company = "S&P Global"
            elif "stripe" in combined_ref:
                company = "Stripe"
            elif "groww" in combined_ref:
                company = "Groww"
            elif "razorpay" in combined_ref:
                company = "Razorpay"
            elif "arcesium" in combined_ref:
                company = "Arcesium"
            elif "visa" in combined_ref:
                company = "Visa"
            elif "expedia" in combined_ref:
                company = "Expedia"
            elif "microsoft" in combined_ref:
                company = "Microsoft"
            elif "media.net" in combined_ref or "medianet" in combined_ref:
                company = "Media.net"
            elif "inmobi" in combined_ref:
                company = "InMobi"
            elif "swiggy" in combined_ref or "mynexthire" in combined_ref:
                company = "Swiggy"
            elif "zomato" in combined_ref:
                company = "Zomato"
            elif "flipkart" in combined_ref or "turbohire" in combined_ref:
                company = "Flipkart"
            elif "target" in combined_ref:
                company = "Target"
            elif "atlassian" in combined_ref:
                company = "Atlassian"
            elif "apple" in combined_ref:
                company = "Apple"
            elif "google" in combined_ref:
                company = "Google"
            elif "meta" in combined_ref or "facebook" in combined_ref:
                company = "Meta"
            elif "coinbase" in combined_ref:
                company = "Coinbase"
            elif "datadog" in combined_ref:
                company = "Datadog"
            elif "figma" in combined_ref:
                company = "Figma"
            elif "robinhood" in combined_ref:
                company = "Robinhood"
            elif "servicenow" in combined_ref:
                company = "ServiceNow"
            elif "twilio" in combined_ref:
                company = "Twilio"
            elif "reddit" in combined_ref:
                company = "Reddit"
            elif "brex" in combined_ref:
                company = "Brex"
            else:
                # Dynamic fallback: extract primary brand name from URL domain
                import urllib.parse
                try:
                    netloc = urllib.parse.urlparse(url).netloc.lower()
                    parts = [p for p in netloc.split('.') if p not in ('www', 'jobs', 'careers', 'com', 'co', 'io', 'in', 'org', 'net', 'en', 'myworkdayjobs')]
                    company = parts[0].capitalize() if parts else "Career Portal"
                except Exception:
                    company = "Career Portal"
        desc_text = job.get("description_text", "")
        
        # Title-based relevance filter to conserve API quota and speed up runs
        title_lower = title.lower()
        keywords = ["analyst", "analytics", "data", "product", "manager", "science", "scientist", "experiment", "decision", "lead"]
        is_relevant = any(kw in title_lower for kw in keywords)
        
        if not is_relevant:
            print(f"[{idx+1}/{len(new_jobs)}] Skipping irrelevant role (title filter): {title} at {company}", file=sys.stderr)
            continue
            
        print(f"[{idx+1}/{len(new_jobs)}] Evaluating: {title} at {company} ({location})...", file=sys.stderr)
        
        # Free-tier rate limiting spacer (12 RPM -> 5s sleep)
        if api_calls_made > 0 and not quota_exhausted:
            time.sleep(5)
            
        prompt = f"""
You are an expert technical recruiter and resume matcher. Your job is to match a job description against a candidate's resume and return a structured JSON evaluation.

### Candidate Resume
{RESUME}

### Matching Parameters
- **Target Roles**: Lead AI Analyst, Analytics Lead, Senior Product Analyst, Principal Analyst, Analytics Manager.
- **High Weight Skills**: A/B testing, SQL, Python, ML (Basics), Stakeholder management, Tableau/PowerBI, Causal Methods.
- **Negative Constraints**: Exclude/penalize pre-sales/solutions engineering (e.g. AEP administration), sales ops, or marketing PM tracks requiring MBAs.
- **Location Weight**: Prioritize Bangalore, India first (Preference #1), followed by Remote (Preference #2), and other major cities in India.

### Job Description to Evaluate
- **Title**: {title}
- **Company**: {company}
- **Location**: {location}
- **URL**: {url}
- **Description**:
{desc_text}

### Instructions
Evaluate the job description against the resume and parameters.
Determine:
1. A match score from 0 to 100. Be realistic and meticulous.
   - For a perfect/excellent fit, score should be >= 85.
   - Roles that are pre-sales, sales ops, or require MBAs/marketing PM should be scored < 60.
   - Lead/Manager roles requiring 8+ years experience fit well.
2. Key Matches: 3 to 4 ultra-concise bullet points summarizing key skills & requirements EXPLICITLY requested in the Job Description.
   - CRITICAL REQUIREMENT: Every bullet point MUST accurately reflect the actual Job Description. 
   - YEARS OF EXPERIENCE RULE: State the exact experience requirement from the JD (e.g. "1+ Yrs Exp Required" if JD says 1+ years; "8+ Yrs Exp Required" ONLY if the JD explicitly asks for 8+ years). NEVER claim 8+ years if the JD asks for less.
   - Keep each bullet point extremely short (2 to 5 words max). For example:
     - "SQL, Python & PySpark"
     - "A/B Testing & Causal Inference"
     - "AI/ML & LLM Workflows"
     - "Bangalore Location Fit"
   - Do NOT write long sentences, paragraphs, or explanations. Keep them as punchy bullet tags.
3. Gaps: 1 to 2 ultra-concise bullet tags detailing any key missing requirements (2 to 5 words max).
4. Mismatch Check: If the job description body text explicitly names a different role title than the header title (e.g., header title is 'Senior Manager - Product Analytics' but body intro says 'Operational Data Scientist'), include a bullet tag in key_matches flagging this (e.g., "Note: Body specifies Data Scientist").

You MUST output your response in JSON format. Do not include markdown code block formatting. Just the raw JSON object.
Output structure:
{{
    "score": <int>,
    "key_matches": [<str>, ...],
    "gaps": [<str>, ...]
}}
"""
        success = False
        retries = 0
        backoff = 6
        res_data = {}
        
        if quota_exhausted:
            print("  -> Quota exhausted flag is set. Skipping evaluation.", file=sys.stderr)
            res_data = {
                "score": 0,
                "key_matches": ["Skipped: Gemini API quota exceeded"],
                "gaps": ["Gemini API quota exceeded in this scan window"]
            }
        else:
            while not success and retries < 5:
                try:
                    response = model.generate_content(
                        prompt,
                        generation_config={"response_mime_type": "application/json"}
                    )
                    res_data = json.loads(response.text)
                    success = True
                    api_calls_made += 1
                except Exception as e:
                    if "429" in str(e) or "Quota" in str(e) or "limit" in str(e).lower():
                        if retries >= 4:
                            print(f"  -> Rate limit (429) hit continuously. Setting quota_exhausted flag.", file=sys.stderr)
                            quota_exhausted = True
                            res_data = {
                                "score": 0,
                                "key_matches": [f"API Quota exhausted during evaluation: {e}"],
                                "gaps": []
                            }
                            break
                        print(f"  -> Rate limit (429) hit. Retrying in {backoff}s...", file=sys.stderr)
                        time.sleep(backoff)
                        retries += 1
                        backoff *= 2
                    else:
                        print(f"  -> Failed to evaluate job {title} via Gemini: {e}", file=sys.stderr)
                        res_data = {
                            "score": 0,
                            "key_matches": [f"API Error during evaluation: {e}"],
                            "gaps": []
                        }
                        break
                    
        score = int(res_data.get("score", 0))
        key_matches = res_data.get("key_matches", [])
        gaps = res_data.get("gaps", [])
        
        evaluated_matches.append({
            "title": title,
            "company": company,
            "location": location,
            "url": url,
            "score": score,
            "key_matches": key_matches,
            "gaps": gaps
        })
        print(f"  -> Match Score: {score}/100", file=sys.stderr)
            
    # 4. Generate report
    report_path = os.path.join(script_dir, "job_matches_report.md")
    high_matches = [m for m in evaluated_matches if m["score"] >= 70]
    high_matches.sort(key=lambda x: x["score"], reverse=True)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_section = f"## 📅 Scan Run: {now_str}\n"
    run_section += f"- **Total New Jobs Scraped**: {len(new_jobs)}\n"
    run_section += f"- **High-Match Roles (Score &ge; 70)**: {len(high_matches)}\n\n"
    
    if high_matches:
        run_section += "| Job Title | Company | Location | Match Score | Key Matches | Gaps |\n"
        run_section += "| :--- | :--- | :--- | :-: | :--- | :--- |\n"
        for m in high_matches:
            matches_bullets = "<br>".join([f"• {x}" for x in m["key_matches"]])
            gaps_bullets = "<br>".join([f"• {x}" for x in m["gaps"]]) if m["gaps"] else "None"
            run_section += f"| [{m['title']}]({m['url']}) | {m['company']} | {m['location']} | **{m['score']}/100** | {matches_bullets} | {gaps_bullets} |\n"
    else:
        run_section += "*No roles with score &ge; 70% found in this run.*\n"
    run_section += "\n---\n"
    
    # Prepend new run history
    header = "# Automated Job Matcher Run History\n\n"
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            existing_report = f.read()
            
        if existing_report.startswith(header):
            body = existing_report[len(header):]
            new_report = header + run_section + body
        else:
            new_report = header + run_section + existing_report
    else:
        new_report = header + run_section
        
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(new_report)
        
    print(f"Log written to {report_path}", file=sys.stderr)
    
    # 5. Send email notification if new high match roles are found
    if high_matches:
        send_email_brief(high_matches)
    elif os.environ.get("SEND_TEST_EMAIL") == "true":
        print("SEND_TEST_EMAIL is true. Sending a mock test email to verify configuration.", file=sys.stderr)
        mock_job = {
            "title": "Lead AI Analyst (TEST PIPELINE RUN)",
            "company": "GitHub Automation Tester",
            "location": "Bengaluru (Remote)",
            "url": "https://github.com/ejazanwar572/gmail-automations",
            "score": 95,
            "key_matches": [
                "This is an automated mock run to check your pipeline.",
                "Your SMTP credentials and Google Account App Password are correct.",
                "GitHub Actions environment variables are loaded and working."
            ],
            "gaps": ["No gaps - this is a test."]
        }
        send_email_brief([mock_job])
    else:
        print("No high-matching roles found. Skipping email briefing.", file=sys.stderr)

if __name__ == "__main__":
    main()
