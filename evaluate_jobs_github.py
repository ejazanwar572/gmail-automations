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
    
    # Build HTML table of roles
    rows = ""
    for m in high_matches:
        matches_html = "".join([f"<li>{x}</li>" for x in m["key_matches"]])
        gaps_html = "".join([f"<li>{x}</li>" for x in m["gaps"]]) if m["gaps"] else "<li>None</li>"
        
        rows += f"""
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 14px 10px; vertical-align: top;"><a href="{m['url']}" style="color: #1a73e8; font-weight: bold; text-decoration: none; font-size: 15px;">{m['title']}</a></td>
            <td style="padding: 14px 10px; vertical-align: top; font-weight: bold; font-size: 14px;">{m['company']}</td>
            <td style="padding: 14px 10px; vertical-align: top; font-size: 14px; color: #5f6368;">{m['location']}</td>
            <td style="padding: 14px 10px; vertical-align: top; text-align: center;"><span style="background-color: #e6f4ea; color: #137333; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 13px; display: inline-block;">{m['score']}/100</span></td>
            <td style="padding: 14px 10px; vertical-align: top; font-size: 13px;">
                <ul style="margin: 0; padding-left: 18px; color: #202124;">{matches_html}</ul>
            </td>
            <td style="padding: 14px 10px; vertical-align: top; font-size: 13px; color: #5f6368;">
                <ul style="margin: 0; padding-left: 18px; color: #5f6368;">{gaps_html}</ul>
            </td>
        </tr>
        """
        
    body_html = f"""
    <html>
    <body style="font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #202124; line-height: 1.6; background-color: #f4f6f9; padding: 20px; margin: 0;">
        <div style="max-width: 900px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.08); border: 1px solid #e0e0e0;">
            <div style="background: linear-gradient(135deg, #1a73e8 0%, #1557b0 100%); padding: 24px; color: #ffffff; text-align: center;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 600; letter-spacing: 0.5px;">Job Board Scraper Brief</h1>
                <p style="margin: 6px 0 0 0; opacity: 0.9; font-size: 14px;">Found {len(high_matches)} roles matching your profile scoring &ge; 70%</p>
            </div>
            <div style="padding: 30px;">
                <p style="font-size: 15px; color: #202124; margin-top: 0;">Hi Ejaz,</p>
                <p style="font-size: 15px; color: #202124;">Here is the list of new matching roles identified from your automated career portal scan:</p>
                
                <div style="overflow-x: auto; margin-top: 20px;">
                    <table style="border-collapse: collapse; width: 100%; min-width: 600px; border: 1px solid #e0e0e0;">
                        <thead>
                            <tr style="background-color: #f8f9fa; border-bottom: 2px solid #e0e0e0;">
                                <th style="padding: 12px 10px; text-align: left; font-weight: 600; font-size: 13px; color: #5f6368; text-transform: uppercase;">Job Title</th>
                                <th style="padding: 12px 10px; text-align: left; font-weight: 600; font-size: 13px; color: #5f6368; text-transform: uppercase;">Company</th>
                                <th style="padding: 12px 10px; text-align: left; font-weight: 600; font-size: 13px; color: #5f6368; text-transform: uppercase;">Location</th>
                                <th style="padding: 12px 10px; text-align: center; font-weight: 600; font-size: 13px; color: #5f6368; text-transform: uppercase;">Score</th>
                                <th style="padding: 12px 10px; text-align: left; font-weight: 600; font-size: 13px; color: #5f6368; text-transform: uppercase;">Key Matches</th>
                                <th style="padding: 12px 10px; text-align: left; font-weight: 600; font-size: 13px; color: #5f6368; text-transform: uppercase;">Gaps</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>
                </div>
                
                <p style="font-size: 15px; color: #202124; margin-top: 24px;">These opportunities have been logged into your repository history file <code>job_matches_report.md</code>.</p>
                <p style="font-size: 15px; color: #202124;">Best of luck with your applications!</p>
            </div>
            <div style="background-color: #f8f9fa; border-top: 1px solid #e0e0e0; padding: 16px; text-align: center; font-size: 12px; color: #5f6368;">
                This briefing was automatically generated and sent by the GitHub Actions Job Matcher workflow.
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
    
    # 3. Evaluate each new job
    for idx, job in enumerate(new_jobs):
        title = job.get("title", "Unknown Title")
        company = job.get("company", "")
        if not company and job.get("source_board"):
            sb = job.get("source_board")
            if "tide.co" in sb or "tide" in sb:
                company = "Tide"
            elif "gartner.com" in sb:
                company = "Gartner"
            elif "adobe.com" in sb:
                company = "Adobe"
            elif "salesforce.com" in sb:
                company = "Salesforce"
            elif "nutanix.com" in sb:
                company = "Nutanix"
            elif "ebayinc.com" in sb:
                company = "eBay"
            elif "pepsico" in sb:
                company = "PepsiCo"
            elif "spglobal" in sb:
                company = "S&P Global"
            elif "stripe" in sb:
                company = "Stripe"
            elif "groww" in sb:
                company = "Groww"
            elif "razorpay" in sb:
                company = "Razorpay"
            elif "arcesium" in sb:
                company = "Arcesium"
            elif "visa" in sb:
                company = "Visa"
            elif "expedia" in sb:
                company = "Expedia"
            elif "microsoft" in sb:
                company = "Microsoft"
            elif "media.net" in sb:
                company = "Media.net"
            else:
                company = "Career Portal"
                
        location = job.get("location", "Unknown Location")
        url = job.get("url", "#")
        desc_text = job.get("description_text", "")
        
        print(f"[{idx+1}/{len(new_jobs)}] Evaluating: {title} at {company} ({location})...", file=sys.stderr)
        
        # Free-tier rate limiting spacer (15 RPM -> 4s sleep)
        if idx > 0:
            time.sleep(4)
            
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
2. Key Matches (3-5 bullet points summarizing what aligns: tools, skills, experience, location).
3. Gaps (bullet points detailing requirements from the job description that the candidate lacks, e.g., java/scala, excessive years, specific industry, location mismatches).

You MUST output your response in JSON format. Do not include markdown code block formatting. Just the raw JSON object.
Output structure:
{{
    "score": <int>,
    "key_matches": [<str>, ...],
    "gaps": [<str>, ...]
}}
"""
        try:
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            res_data = json.loads(response.text)
            
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
        except Exception as e:
            print(f"  -> Failed to evaluate job {title} via Gemini: {e}", file=sys.stderr)
            evaluated_matches.append({
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "score": 0,
                "key_matches": [f"API Error during evaluation: {e}"],
                "gaps": []
            })
            
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
