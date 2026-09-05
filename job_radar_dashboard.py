import os
import re
import json
import time
import subprocess
from datetime import datetime, timezone
import urllib.parse
import urllib.request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─── Page Configuration ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Radar & Intelligence Hub",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom Dark Aesthetic Theme ───────────────────────────────────────────
st.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
.stApp {
    background-color: #0b0f19 !important;
    color: #f1f5f9 !important;
}
html, body, [class*="css"], .stMarkdown, p, div, label, span, h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif !important;
}
[data-testid="stToolbar"], [data-testid="stDecoration"], #stDecoration { display: none !important; }
header[data-testid="stHeader"] {
    height: 0 !important;
    min-height: 0 !important;
    background-color: #0b0f19 !important;
    overflow: hidden !important;
}
[data-testid="stAppViewBlockContainer"] {
    padding-top: 24px !important;
    padding-bottom: 40px !important;
}
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #0b0f19; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #3b82f6; }

/* Metric Card */
.metric-box {
    background: linear-gradient(145deg, #131b2e 0%, #0f172a 100%);
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 16px 20px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    margin-bottom: 12px;
}
.metric-label {
    font-size: 0.85rem;
    font-weight: 500;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
}
.metric-value {
    font-size: 1.85rem;
    font-weight: 700;
    color: #f8fafc;
    line-height: 1.2;
}
.metric-sub {
    font-size: 0.80rem;
    color: #38bdf8;
    margin-top: 4px;
}

/* Job Match Card */
.job-card {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 8px;
    transition: transform 0.15s ease, border-color 0.15s ease;
}
.job-card:hover {
    border-color: #3b82f6;
    transform: translateY(-2px);
}
.badge-score-high {
    background-color: #064e3b;
    color: #34d399;
    border: 1px solid #059669;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.85rem;
    display: inline-block;
}
.badge-score-mid {
    background-color: #0c4a6e;
    color: #38bdf8;
    border: 1px solid #0284c7;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.85rem;
    display: inline-block;
}
.badge-score-good {
    background-color: #451a03;
    color: #fbbf24;
    border: 1px solid #d97706;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.85rem;
    display: inline-block;
}
.tag-chip {
    display: inline-block;
    background-color: #064e3b22;
    color: #34d399;
    font-size: 0.78rem;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 9999px;
    margin-right: 6px;
    margin-bottom: 6px;
    border: 1px solid #05966944;
}
.tag-gap {
    display: inline-block;
    background-color: #7f1d1d22;
    color: #fca5a5;
    font-size: 0.78rem;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 9999px;
    margin-right: 6px;
    margin-bottom: 6px;
    border: 1px solid #b91c1c44;
}
.apply-btn {
    display: inline-block;
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    color: #ffffff !important;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 8px 16px;
    border-radius: 8px;
    text-decoration: none;
    transition: background 0.15s ease;
}
.apply-btn:hover {
    background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
}
.status-badge-applied {
    display: inline-block;
    background-color: #0284c7;
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 6px;
    margin-left: 8px;
}
.status-badge-saved {
    display: inline-block;
    background-color: #eab308;
    color: #0f172a;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 6px;
    margin-left: 8px;
}
.highlight-term {
    background-color: #854d0e;
    color: #fef08a;
    padding: 2px 5px;
    border-radius: 4px;
    font-weight: 600;
}
</style>
""")

# ─── Path Constants ─────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOARDS_FILE = os.path.join(BASE_DIR, "job_boards.json")
JOBS_FILE = os.path.join(BASE_DIR, "scraped_jobs.json")
REPORT_FILE = os.path.join(BASE_DIR, "job_matches_report.md")
TRACKER_FILE = os.path.join(BASE_DIR, "job_applications.json")

# ─── Application Status Tracking Helpers ─────────────────────────────────────
def load_application_tracker():
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_application_tracker(data):
    try:
        with open(TRACKER_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Failed to save application status: {e}")

# ─── Data Extraction & Helpers ──────────────────────────────────────────────
COMPANY_KEYWORDS = [
    ('amazon', 'Amazon'), ('walmart', 'Walmart'), ('meesho', 'Meesho'), ('postman', 'Postman'),
    ('uber', 'Uber'), ('tide', 'Tide'), ('gartner', 'Gartner'), ('adobe', 'Adobe'),
    ('salesforce', 'Salesforce'), ('nutanix', 'Nutanix'), ('ebay', 'eBay'), ('pepsico', 'PepsiCo'),
    ('spglobal', 'S&P Global'), ('s&p', 'S&P Global'), ('stripe', 'Stripe'), ('groww', 'Groww'),
    ('razorpay', 'Razorpay'), ('arcesium', 'Arcesium'), ('visa', 'Visa'), ('expedia', 'Expedia'),
    ('microsoft', 'Microsoft'), ('media.net', 'Media.net'), ('inmobi', 'InMobi'), ('swiggy', 'Swiggy'),
    ('zomato', 'Zomato'), ('flipkart', 'Flipkart'), ('target', 'Target'), ('atlassian', 'Atlassian'),
    ('apple', 'Apple'), ('google', 'Google'), ('meta', 'Meta'), ('coinbase', 'Coinbase'),
    ('datadog', 'Datadog'), ('figma', 'Figma'), ('robinhood', 'Robinhood'), ('servicenow', 'ServiceNow'),
    ('twilio', 'Twilio'), ('reddit', 'Reddit'), ('brex', 'Brex'), ('freshworks', 'Freshworks'),
    ('phonepe', 'PhonePe'), ('cred', 'CRED'), ('paypal', 'PayPal'), ('grab', 'Grab'),
    ('intuit', 'Intuit'), ('canva', 'Canva'), ('goto', 'GoTo'), ('rubrik', 'Rubrik')
]

def identify_firm(url):
    u = (url or "").lower()
    for key, name in COMPANY_KEYWORDS:
        if key in u:
            return name
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        parts = [p for p in netloc.split('.') if p not in ('www', 'jobs', 'careers', 'com', 'co', 'io', 'in', 'org', 'net', 'myworkdayjobs')]
        if parts:
            return parts[0].capitalize()
    except Exception:
        pass
    return "Career Portal"

def identify_platform(url):
    u = (url or "").lower()
    if 'greenhouse' in u: return 'Greenhouse'
    if 'myworkdayjobs' in u: return 'Workday'
    if 'smartrecruiters' in u: return 'SmartRecruiters'
    if 'lever.co' in u: return 'Lever'
    if any(k in u for k in ['gartner.com', 'careers.adobe', 'salesforce.com', 'nutanix.com', 'ebayinc.com']): return 'Phenom'
    if 'pepsicojobs' in u or 'spglobal' in u: return 'Jibe'
    if 'amazon.jobs' in u: return 'Amazon API'
    if 'careers.swiggy' in u or 'mynexthire' in u: return 'MyNextHire API'
    if 'turbohire' in u: return 'TurboHire API'
    if 'microsoft' in u: return 'Microsoft API'
    if 'uber' in u: return 'Uber API'
    if 'expediagroup' in u: return 'WordPress'
    if 'media.net' in u: return 'Media.net API'
    return 'Custom Portal'

def highlight_keywords(text):
    if not text:
        return ""
    keywords = [
        r'\b8\+?\s*years?\b', r'\b10\+?\s*years?\b', r'\b7\+?\s*years?\b', r'\b5\+?\s*years?\b',
        r'\bSQL\b', r'\bPython\b', r'\bPowerBI\b', r'\bPower\s*BI\b', r'\bTableau\b',
        r'\bA/B\s*test(?:ing)?\b', r'\bCausal(?:\s*inference)?\b', r'\bMachine\s*Learning\b',
        r'\bLLMs?\b', r'\bGenerative\s*AI\b', r'\bAnalytics\s*Lead(?:ership)?\b', r'\bBangalore\b', r'\bBengaluru\b'
    ]
    highlighted = text
    for kw in keywords:
        highlighted = re.sub(kw, lambda m: f'<span class="highlight-term">{m.group(0)}</span>', highlighted, flags=re.IGNORECASE)
    return highlighted.replace('\n', '<br>')

@st.cache_data(ttl=60)
def load_data():
    # 1. Load Tracked Boards
    boards = []
    if os.path.exists(BOARDS_FILE):
        try:
            with open(BOARDS_FILE, 'r', encoding='utf-8') as f:
                boards = json.load(f)
        except Exception:
            boards = []

    # 2. Load Scraped Jobs Database
    jobs = []
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
        except Exception:
            jobs = []

    # 3. Load Matches Report & Scan History
    scan_runs = []
    high_matches = []
    if os.path.exists(REPORT_FILE):
        try:
            with open(REPORT_FILE, 'r', encoding='utf-8') as f:
                report_content = f.read()

            # Parse Scan Runs
            run_blocks = re.split(r'## 📅 Scan Run: ', report_content)
            for block in run_blocks[1:]:
                lines = block.strip().split('\n')
                date_str = lines[0].strip()
                new_jobs_match = re.search(r'\*\*Total New Jobs Scraped\*\*:\s*(\d+)', block)
                high_match_count = re.search(r'\*\*High-Match Roles[^:]*\*\*:\s*(\d+)', block)
                
                scan_runs.append({
                    'timestamp_str': date_str,
                    'new_jobs': int(new_jobs_match.group(1)) if new_jobs_match else 0,
                    'high_matches': int(high_match_count.group(1)) if high_match_count else 0
                })

            # Parse Evaluated High-Match Table Rows
            row_pattern = r'\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*\*\*([0-9]+)/100\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|'
            rows = re.findall(row_pattern, report_content)
            for r in rows:
                high_matches.append({
                    'title': r[0].strip(),
                    'url': r[1].strip(),
                    'company': r[2].strip(),
                    'location': r[3].strip(),
                    'score': int(r[4].strip()),
                    'key_matches': [m.strip(' •\r') for m in r[5].replace('<br>', '\n').split('\n') if m.strip()],
                    'gaps': [g.strip(' •\r') for g in r[6].replace('<br>', '\n').split('\n') if g.strip() and g.strip().lower() != 'none']
                })
        except Exception as e:
            st.error(f"Error parsing job matches report: {e}")

    # Build Boards DataFrame
    board_counts = {}
    for j in jobs:
        sb = j.get('source_board', '')
        board_counts[sb] = board_counts.get(sb, 0) + 1

    board_records = []
    for b in boards:
        firm = identify_firm(b)
        platform = identify_platform(b)
        count = board_counts.get(b, 0)
        firm_matches = len([m for m in high_matches if m['company'].lower() == firm.lower()])
        status = "🟢 Active" if count > 0 else "⚪ Scheduled"
        board_records.append({
            'Firm': firm,
            'Platform': platform,
            'Listings': count,
            'Matches': firm_matches,
            'Status': status,
            'URL': b
        })

    df_boards = pd.DataFrame(board_records)
    if not df_boards.empty:
        df_boards = df_boards.sort_values(by=['Listings', 'Firm'], ascending=[False, True])

    df_runs = pd.DataFrame(scan_runs)
    return boards, jobs, high_matches, df_boards, df_runs

boards, jobs, high_matches, df_boards, df_runs = load_data()
app_tracker = load_application_tracker()

# ─── Top Header & Pulse Metrics ────────────────────────────────────────────
st.markdown("## 🎯 Corporate Job Radar & Intelligence Hub")
st.markdown("Real-time monitoring of corporate career portals, crawl freshness, and AI match opportunities.")

# Compute Freshness
latest_scan_str = "Never"
hours_ago_str = "Awaiting first run"
if not df_runs.empty and 'timestamp_str' in df_runs.columns:
    latest_scan_str = df_runs.iloc[0]['timestamp_str']
    try:
        last_dt = datetime.strptime(latest_scan_str, "%Y-%m-%d %H:%M:%S")
        diff_hours = (datetime.now() - last_dt).total_seconds() / 3600
        if diff_hours < 1:
            hours_ago_str = f"{int(diff_hours * 60)} mins ago"
        elif diff_hours < 24:
            hours_ago_str = f"{diff_hours:.1f} hrs ago"
        else:
            hours_ago_str = f"{int(diff_hours / 24)} days ago"
    except Exception:
        hours_ago_str = latest_scan_str

# Count applied and saved
applied_count = sum(1 for v in app_tracker.values() if v.get('status') == 'Applied')
saved_count = sum(1 for v in app_tracker.values() if v.get('status') == 'Saved')

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Firms on Radar</div>
        <div class="metric-value">{df_boards['Firm'].nunique() if not df_boards.empty else 0}</div>
        <div class="metric-sub">Across {len(boards)} career portals</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Tracked Listings</div>
        <div class="metric-value">{len(jobs):,}</div>
        <div class="metric-sub">Indexed in local database</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">High-Match Roles</div>
        <div class="metric-value">{len(high_matches)}</div>
        <div class="metric-sub">Evaluated score &ge; 70%</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Applied / Saved</div>
        <div class="metric-value">{applied_count} <span style="font-size:1.1rem; color:#94a3b8;">/ {saved_count}</span></div>
        <div class="metric-sub">In application tracker</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Scraper Freshness</div>
        <div class="metric-value">{hours_ago_str}</div>
        <div class="metric-sub">{latest_scan_str}</div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Scan Schedule</div>
        <div class="metric-value">Every 3h</div>
        <div class="metric-sub">GitHub Actions Runner</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ─── Tabs Navigation ────────────────────────────────────────────────────────
tab_radar, tab_matches, tab_explorer, tab_ops = st.tabs([
    "🏢 Radar & Firms Matrix",
    "🎯 High-Match Roles",
    "🔍 Full Job Explorer",
    "🛠️ Scraper Ops & Manager"
])

# ─── TAB 1: RADAR & FIRMS HEALTH MATRIX ─────────────────────────────────────
with tab_radar:
    st.subheader("Firms on Radar & Health Status")
    
    r_col1, r_col2, r_col3 = st.columns([2, 1, 1])
    with r_col1:
        search_firm = st.text_input("🔍 Search firm name...", placeholder="e.g. Target, Swiggy, Amazon, Flipkart, Stripe")
    with r_col2:
        platforms_list = ["All Platforms"] + sorted(df_boards['Platform'].unique().tolist()) if not df_boards.empty else []
        sel_platform = st.selectbox("Filter by ATS / Platform", platforms_list)
    with r_col3:
        status_list = ["All Statuses", "🟢 Active", "⚪ Scheduled"]
        sel_status = st.selectbox("Filter by Status", status_list)

    filtered_df = df_boards.copy()
    if search_firm:
        filtered_df = filtered_df[filtered_df['Firm'].str.contains(search_firm, case=False, na=False)]
    if sel_platform != "All Platforms":
        filtered_df = filtered_df[filtered_df['Platform'] == sel_platform]
    if sel_status != "All Statuses":
        filtered_df = filtered_df[filtered_df['Status'] == sel_status]

    c_left, c_right = st.columns([3, 2])
    with c_left:
        st.dataframe(
            filtered_df[['Firm', 'Platform', 'Listings', 'Matches', 'Status', 'URL']],
            use_container_width=True,
            height=480,
            column_config={
                "URL": st.column_config.LinkColumn("Career Board URL", display_text="Open Portal ↗"),
                "Listings": st.column_config.NumberColumn("Tracked Listings", format="%d"),
                "Matches": st.column_config.NumberColumn("Matches (≥70%)", format="%d")
            }
        )

    with c_right:
        if not df_boards.empty:
            platform_counts = df_boards.groupby('Platform').size().reset_index(name='Count')
            fig_plat = px.pie(
                platform_counts,
                names='Platform',
                values='Count',
                title="Tracked Boards by ATS Platform",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            fig_plat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#cbd5e1",
                legend=dict(orientation="h", yanchor="bottom", y=-0.3),
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig_plat, use_container_width=True)

# ─── TAB 2: HIGH-MATCH OPPORTUNITY PIPELINE ─────────────────────────────────
with tab_matches:
    st.subheader("Curated High-Match Pipeline (Score ≥ 70%)")
    
    m_col1, m_col2, m_col3, m_col4 = st.columns([1.2, 1.2, 1.2, 1.2])
    with m_col1:
        min_score = st.slider("Minimum Match Score", min_value=70, max_value=100, value=75, step=5)
    with m_col2:
        all_companies = ["All Companies"] + sorted(list(set(m['company'] for m in high_matches)))
        sel_comp = st.selectbox("Company", all_companies)
    with m_col3:
        status_filter = st.selectbox("Application Status", ["All Roles", "Active Pipeline", "Applied", "Saved", "Hidden"])
    with m_col4:
        search_kw = st.text_input("Role Keyword", placeholder="e.g. Lead, Science, Product")

    filtered_matches = []
    for m in high_matches:
        if m['score'] < min_score:
            continue
        if sel_comp != "All Companies" and m['company'].lower() != sel_comp.lower():
            continue
        if search_kw and search_kw.lower() not in m['title'].lower():
            continue
        
        job_status = app_tracker.get(m['url'], {}).get('status', 'Unapplied')
        if status_filter == "Applied" and job_status != "Applied":
            continue
        if status_filter == "Saved" and job_status != "Saved":
            continue
        if status_filter == "Hidden" and job_status != "Hidden":
            continue
        if status_filter == "Active Pipeline" and job_status in ("Hidden", "Applied"):
            continue

        m_copy = dict(m)
        m_copy['status'] = job_status
        filtered_matches.append(m_copy)

    st.markdown(f"**Showing {len(filtered_matches)} opportunities matching your criteria:**")

    if not filtered_matches:
        st.info("No roles match the selected filter criteria. Try lowering the score threshold or adjusting status filters.")
    else:
        for idx, job in enumerate(filtered_matches[:30]):
            score = job['score']
            badge_class = "badge-score-high" if score >= 85 else ("badge-score-mid" if score >= 75 else "badge-score-good")
            
            key_tags_html = "".join([f'<span class="tag-chip">✓ {t}</span>' for t in job.get('key_matches', [])])
            gap_tags_html = "".join([f'<span class="tag-gap">⚠ {g}</span>' for g in job.get('gaps', [])])
            if not gap_tags_html:
                gap_tags_html = '<span class="tag-chip" style="color: #4ade80;">✓ No major gaps identified</span>'

            curr_status = job.get('status', 'Unapplied')
            status_indicator = ""
            if curr_status == 'Applied':
                status_indicator = '<span class="status-badge-applied">✓ APPLIED</span>'
            elif curr_status == 'Saved':
                status_indicator = '<span class="status-badge-saved">★ SAVED</span>'

            st.markdown(f"""
            <div class="job-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <h4 style="margin: 0; font-size: 1.15rem; color: #f8fafc;">
                            {job['title']} {status_indicator}
                        </h4>
                        <div style="margin-top: 4px; color: #94a3b8; font-size: 0.9rem;">
                            🏢 <strong style="color: #e2e8f0;">{job['company']}</strong> &nbsp;|&nbsp; 📍 {job['location']}
                        </div>
                    </div>
                    <div>
                        <span class="{badge_class}">{score}/100 Match</span>
                    </div>
                </div>
                <div style="margin-top: 8px;">
                    <div style="font-size: 0.78rem; font-weight: 600; color: #64748b; margin-bottom: 4px;">KEY REQUIREMENTS & ALIGNMENTS</div>
                    <div>{key_tags_html}</div>
                </div>
                <div style="margin-top: 6px;">
                    <div style="font-size: 0.78rem; font-weight: 600; color: #64748b; margin-bottom: 4px;">GAPS / CONSIDERATIONS</div>
                    <div>{gap_tags_html}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Action bar: Apply link + Status Select
            act_col1, act_col2 = st.columns([2, 1])
            with act_col1:
                st.markdown(f'<a href="{job["url"]}" target="_blank" class="apply-btn">Apply on {job["company"]} ↗</a>', unsafe_allow_html=True)
            with act_col2:
                status_options = ["Unapplied", "Applied", "Saved", "Hidden"]
                curr_idx = status_options.index(curr_status) if curr_status in status_options else 0
                new_status = st.selectbox(
                    "Track Status",
                    status_options,
                    index=curr_idx,
                    key=f"status_sel_{idx}_{hash(job['url'])}",
                    label_visibility="collapsed"
                )
                if new_status != curr_status:
                    app_tracker[job['url']] = {
                        'title': job['title'],
                        'company': job['company'],
                        'status': new_status,
                        'updated_at': datetime.now().isoformat()
                    }
                    save_application_tracker(app_tracker)
                    st.rerun()

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        if len(filtered_matches) > 30:
            st.caption(f"Displaying top 30 of {len(filtered_matches)} matching roles. Use filters to narrow down.")

# ─── TAB 3: FULL JOB EXPLORER ───────────────────────────────────────────────
with tab_explorer:
    st.subheader("Database Job Explorer & Deep JD Inspector")
    st.caption("Search across all 4,511+ raw scraped job postings across every tracked company with automatic skill & experience highlighting.")

    e_col1, e_col2, e_col3, e_col4 = st.columns([2, 1.2, 1.2, 1])
    with e_col1:
        query = st.text_input("Search Title or Description Keywords", placeholder="e.g. PySpark, A/B testing, Causal, Machine Learning")
    with e_col2:
        exp_firm = st.selectbox("Firm Filter", ["All Firms"] + sorted(df_boards['Firm'].unique().tolist()) if not df_boards.empty else ["All Firms"])
    with e_col3:
        exp_level = st.selectbox("Seniority / Experience", ["All Levels", "8+ Years / Lead / Staff", "5+ Years / Senior", "Management / Director"])
    with e_col4:
        exp_limit = st.selectbox("Results Limit", [20, 50, 100], index=0)

    filtered_jobs = []
    q_lower = query.lower().strip() if query else ""
    
    for j in jobs:
        firm_name = identify_firm(j.get('source_board', ''))
        if exp_firm != "All Firms" and firm_name.lower() != exp_firm.lower():
            continue
            
        title_text = j.get('title', '').lower()
        desc_text = j.get('description_text', '').lower()
        loc_text = j.get('location', '').lower()
        full_content = f"{title_text} {desc_text}"

        if exp_level == "8+ Years / Lead / Staff":
            if not any(k in full_content for k in ['8+ year', '8 years', '10+ year', '10 years', 'lead', 'staff', 'principal', 'head of', 'director']):
                continue
        elif exp_level == "5+ Years / Senior":
            if not any(k in full_content for k in ['5+ year', '5 years', '6+ year', '7+ year', 'senior', 'sr.']):
                continue
        elif exp_level == "Management / Director":
            if not any(k in full_content for k in ['manager', 'director', 'head of', 'vp', 'lead']):
                continue

        if q_lower:
            if q_lower not in title_text and q_lower not in desc_text and q_lower not in loc_text:
                continue
                
        filtered_jobs.append(j)

    st.markdown(f"**Found {len(filtered_jobs):,} matching listings:**")

    for i, j in enumerate(filtered_jobs[:exp_limit]):
        firm_name = identify_firm(j.get('source_board', ''))
        with st.expander(f"**{j.get('title', 'Unknown Title')}** — {firm_name} ({j.get('location', 'India')})"):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"📍 **Location**: {j.get('location', 'India')}")
                st.markdown(f"🌐 **Source Board**: `{j.get('source_board', '')}`")
            with c2:
                st.markdown(f"[Apply Directly ↗]({j.get('url')})")
            
            st.divider()
            desc = j.get('description_text') or j.get('description_html') or "No description preview available."
            st.markdown("#### Job Description (Key Keywords Highlighted)")
            highlighted_desc = highlight_keywords(desc[:3500] + ("..." if len(desc) > 3500 else ""))
            st.markdown(f"""
            <div style="background-color: #0f172a; padding: 16px; border-radius: 8px; border: 1px solid #1e293b; max-height: 400px; overflow-y: auto; font-size: 0.9rem; line-height: 1.6;">
                {highlighted_desc}
            </div>
            """, unsafe_allow_html=True)

# ─── TAB 4: SCRAPER OPERATIONS & BOARD MANAGER ──────────────────────────────
with tab_ops:
    st.subheader("Scraper Operations & History")
    
    # Historical Scrape Chart
    if not df_runs.empty:
        st.markdown("#### 📈 Discovery Velocity per Scan Run")
        df_plot = df_runs.copy().iloc[:40]
        fig_runs = go.Figure()
        fig_runs.add_trace(go.Bar(
            x=df_plot['timestamp_str'],
            y=df_plot['new_jobs'],
            name="New Jobs Scraped",
            marker_color="#3b82f6"
        ))
        fig_runs.add_trace(go.Scatter(
            x=df_plot['timestamp_str'],
            y=df_plot['high_matches'],
            name="High Matches (≥70%)",
            mode="lines+markers",
            marker=dict(color="#10b981", size=7),
            line=dict(color="#10b981", width=2)
        ))
        fig_runs.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#cbd5e1",
            xaxis=dict(showgrid=False, title="Scan Run Timestamp", autorange="reversed"),
            yaxis=dict(gridcolor="#1e293b", title="Count"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(l=10, r=10, t=30, b=30)
        )
        st.plotly_chart(fig_runs, use_container_width=True)

    st.divider()
    
    op_col1, op_col2 = st.columns(2)
    
    with op_col1:
        st.markdown("#### ⚡ Live Board Extraction Test")
        st.caption("Select any tracked board or paste a custom URL to test live extraction and inspect parsed jobs.")
        
        test_url = st.selectbox("Select Tracked Board to Test", boards if boards else ["None"])
        if st.button("🚀 Run Live Test Scrape"):
            with st.spinner(f"Scraping {test_url}..."):
                from check_job_boards import (
                    scrape_greenhouse_board, scrape_workday_board, scrape_smartrecruiters_board,
                    scrape_lever_board, scrape_swiggy_board, scrape_flipkart_board
                )
                t_start = time.time()
                posts = []
                try:
                    if "greenhouse.io" in test_url:
                        posts = scrape_greenhouse_board(test_url)
                    elif "myworkdayjobs.com" in test_url:
                        posts = scrape_workday_board(test_url)
                    elif "smartrecruiters.com" in test_url:
                        posts = scrape_smartrecruiters_board(test_url)
                    elif "lever.co" in test_url:
                        posts = scrape_lever_board(test_url)
                    elif "swiggy" in test_url:
                        posts = scrape_swiggy_board(test_url)
                    elif "flipkart" in test_url or "turbohire" in test_url:
                        posts = scrape_flipkart_board(test_url)
                    else:
                        st.warning("Board uses a custom parser.")
                        
                    duration = time.time() - t_start
                    st.success(f"Successfully scraped in {duration:.2f}s! Returned {len(posts)} total listings.")
                    if posts:
                        sample_preview = pd.DataFrame([
                            {'Title': p.get('title'), 'Location': p.get('location'), 'URL': p.get('url')}
                            for p in posts[:10]
                        ])
                        st.dataframe(sample_preview, use_container_width=True)
                except Exception as e:
                    st.error(f"Scraper error: {e}")

    with op_col2:
        st.markdown("#### ➕ Add New Career Board to Radar")
        st.caption("Add a new Greenhouse, Workday, Lever, or SmartRecruiters board to automated crawling.")
        
        new_board_url = st.text_input("New Board URL", placeholder="https://job-boards.greenhouse.io/company")
        if st.button("Add Board to Radar"):
            new_url_clean = new_board_url.strip()
            if not new_url_clean:
                st.warning("Please enter a valid URL.")
            elif new_url_clean in boards:
                st.info("This board is already tracked in job_boards.json.")
            else:
                detected_platform = identify_platform(new_url_clean)
                detected_firm = identify_firm(new_url_clean)
                boards.append(new_url_clean)
                try:
                    with open(BOARDS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(boards, f, indent=4)
                    st.success(f"Added {detected_firm} ({detected_platform}) to job_boards.json!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update job_boards.json: {e}")

    st.divider()
    st.markdown("#### 🔄 Trigger Full Radar Scan")
    st.caption("Manually trigger a full crawling scan across all 44 job boards via check_job_boards.py in the background.")
    if st.button("▶ Start Full Scan Now"):
        with st.spinner("Initiating full crawler job in background..."):
            try:
                proc = subprocess.Popen(
                    ["python3", "check_job_boards.py"],
                    cwd=BASE_DIR,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                st.success(f"Full scraper initiated in background (PID: {proc.pid})! New roles will populate upon completion.")
            except Exception as e:
                st.error(f"Failed to launch scraper: {e}")
