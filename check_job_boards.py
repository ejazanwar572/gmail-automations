import urllib.request
import urllib.parse
import re
import json
import os
import html
import sys
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import socket
socket.setdefaulttimeout(15)

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')

# Paths
base_dir = "/Users/ejazanwar/Documents/Gmail Automations"
if not os.path.exists(base_dir):
    base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, "job_boards.json")
db_path = os.path.join(base_dir, "scraped_jobs.json")

# Ensure scratch dir exists
os.makedirs(base_dir, exist_ok=True)

# Load target URLs
with open(config_path, 'r', encoding='utf-8') as f:
    target_urls = json.load(f)

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

target_locations = ["india", "bangalore", "bengaluru", "gurgaon", "gurugram", "hyderabad", "noida", "pune", "mumbai", "chennai", "delhi", "ncr", "remote", "anywhere"]

def clean_html(raw_html):
    if not raw_html:
        return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return html.unescape(cleantext).strip()

def add_query_param(url, param_name, param_value):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query[param_name] = [str(param_value)]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

# Load existing scraped jobs
existing_jobs = {}
if os.path.exists(db_path):
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            jobs_list = json.load(f)
            existing_jobs = {str(j['id']): j for j in jobs_list}
    except Exception as e:
        print(f"Warning: could not load existing jobs: {e}", file=sys.stderr)

new_jobs = []
updated_jobs_list = list(existing_jobs.values())

def fetch_html(url, timeout=15):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None

# ==================== GREENHOUSE BOARD SCRAPER ====================
def scrape_greenhouse_board(url):
    all_posts = []
    page = 1
    total_pages = 1
    
    while page <= total_pages:
        page_url = add_query_param(url, 'page', page)
        print(f"Scraping Greenhouse page: {page_url}", file=sys.stderr)
        html_content = fetch_html(page_url)
        if not html_content:
            break
            
        match = re.search(r'window\.__remixContext\s*=\s*(\{.*?\});\s*</script>', html_content)
        if not match:
            print(f"Could not find window.__remixContext on page {page}", file=sys.stderr)
            break
            
        try:
            context_data = json.loads(match.group(1))
            loader_data = context_data.get('state', {}).get('loaderData', {})
            job_posts_block = None
            for key, val in loader_data.items():
                if isinstance(val, dict) and 'jobPosts' in val:
                    job_posts_block = val['jobPosts']
                    break
            
            if not job_posts_block:
                print(f"Job posts data structure not found on Greenhouse page {page}", file=sys.stderr)
                break
                
            posts = job_posts_block.get('data', [])
            all_posts.extend(posts)
            
            total_pages = job_posts_block.get('total_pages', 1)
            page += 1
        except Exception as e:
            print(f"Error parsing Greenhouse page {page}: {e}", file=sys.stderr)
            break
            
    return all_posts

def scrape_greenhouse_job_details(job_url):
    html_content = fetch_html(job_url)
    if not html_content:
        return None
        
    match = re.search(r'window\.__remixContext\s*=\s*(\{.*?\});\s*</script>', html_content)
    if not match:
        return None
        
    try:
        job_context = json.loads(match.group(1))
        loader_data = job_context.get('state', {}).get('loaderData', {})
        job_detail = None
        for key, val in loader_data.items():
            if isinstance(val, dict) and 'jobPost' in val:
                job_detail = val['jobPost']
                break
                
        if not job_detail:
            return None
            
        content_html = job_detail.get('content', '')
        intro_html = job_detail.get('introduction', '')
        conclusion_html = job_detail.get('conclusion', '')
        
        full_html = f"{intro_html}\n{content_html}\n{conclusion_html}"
        plain_text = clean_html(full_html)
        return full_html, plain_text
    except Exception as e:
        # Fallback to direct parsing if context parsing fails
        desc_match = re.search(r'<div class="job__description[^>]*>(.*?)</div>\s*<div class="job-alert', html_content, re.DOTALL)
        if desc_match:
            desc_html = desc_match.group(1)
            return desc_html, clean_html(desc_html)
        return None

# ==================== PHENOM PEOPLE (GARTNER / ADOBE / EBAY / SALESFORCE / NUTANIX) ====================
def scrape_phenom_board(url):
    all_parsed_jobs = []
    parsed_url = urlparse(url)
    
    first_page_content = fetch_html(url)
    if not first_page_content:
        return []
        
    is_json_layout = "phApp.ddo" in first_page_content or "eagerLoadRefineSearch" in first_page_content
    
    if is_json_layout:
        params = parse_qs(parsed_url.query)
        from_val = int(params.get('from', [0])[0])
        
        while True:
            page_url = add_query_param(url, 'from', from_val)
            print(f"Scraping Phenom JSON board page starting from {from_val}: {page_url}", file=sys.stderr)
            html_content = fetch_html(page_url) if from_val > 0 else first_page_content
            if not html_content:
                break
                
            match = re.search(r'phApp\.ddo\s*=\s*(\{.*?\});', html_content)
            if not match:
                match = re.search(r'"eagerLoadRefineSearch"\s*:\s*(\{.*?\})\s*,\s*"data"', html_content)
                
            data_json = {}
            if match:
                try:
                    data_str = match.group(1).strip().rstrip(';')
                    data_json = json.loads(data_str)
                except Exception as e:
                    print(f"Error parsing JSON on from={from_val}: {e}", file=sys.stderr)
                    raw_jobs_match = re.search(r'"jobs"\s*:\s*(\[.*?\])\s*,\s*"totalHits"', html_content)
                    if raw_jobs_match:
                        try:
                            data_json = {"jobs": json.loads(raw_jobs_match.group(1))}
                        except Exception:
                            pass
            else:
                raw_jobs_match = re.search(r'"jobs"\s*:\s*(\[.*?\])\s*,\s*"totalHits"', html_content)
                if raw_jobs_match:
                    try:
                        data_json = {"jobs": json.loads(raw_jobs_match.group(1))}
                    except Exception:
                        pass
            
            page_jobs_data = []
            if 'jobs' in data_json:
                page_jobs_data = data_json['jobs']
            elif 'eagerLoadRefineSearch' in data_json:
                page_jobs_data = data_json['eagerLoadRefineSearch'].get('data', {}).get('jobs', [])
            elif 'data' in data_json and 'jobs' in data_json['data']:
                page_jobs_data = data_json['data']['jobs']
                
            if not page_jobs_data:
                break
                
            page_jobs = []
            for job in page_jobs_data:
                job_id = job.get('jobId')
                title = job.get('title')
                location = job.get('location')
                if not job_id or not title:
                    continue
                title_slug = slugify(title)
                
                # Format URL based on company domain
                if "adobe" in parsed_url.netloc:
                    job_url = f"https://{parsed_url.netloc}/us/en/job/{job_id}/{title_slug}"
                elif "ebay" in parsed_url.netloc:
                    job_url = f"https://jobs.ebayinc.com/us/en/job/{job_id}/{title_slug}"
                else:
                    job_url = f"https://{parsed_url.netloc}/jobs/job/{job_id}/{title_slug}"
                
                page_jobs.append({
                    'id': str(job_id),
                    'title': title,
                    'url': job_url,
                    'location': location or "N/A"
                })
                
            if not page_jobs:
                break
                
            new_on_page = [j for j in page_jobs if j['url'] not in [aj['url'] for aj in all_parsed_jobs]]
            if not new_on_page:
                break
                
            all_parsed_jobs.extend(page_jobs)
            from_val += len(page_jobs_data)
            
    else:
        page_num = 1
        while True:
            page_url = add_query_param(url, 'page', page_num)
            print(f"Scraping Phenom HTML board page {page_num}: {page_url}", file=sys.stderr)
            html_content = fetch_html(page_url) if page_num > 1 else first_page_content
            if not html_content:
                break
                
            job_blocks = re.findall(r'<div class="card card-job js-job".*?</div>\s*</div>', html_content, re.DOTALL)
            if not job_blocks:
                job_blocks = re.findall(r'<div class="card card-job js-job".*?<ul class="job-meta">.*?</ul>', html_content, re.DOTALL)
                
            if not job_blocks:
                break
                
            page_jobs = []
            for block in job_blocks:
                link_match = re.search(r'href="(/jobs/job/[^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
                loc_match = re.search(r'<ul class="job-meta">\s*<li>\s*(.*?)\s*</li>\s*</ul>', block, re.DOTALL)
                
                if link_match:
                    url_path = link_match.group(1).strip()
                    title = html.unescape(link_match.group(2).strip())
                    title = re.sub(r'<.*?>', '', title)
                    
                    location = "India"
                    if loc_match:
                        location = html.unescape(loc_match.group(1).strip())
                        location = re.sub(r'\s+', ' ', location)
                        
                    page_jobs.append({
                        'id': url_path.split('/')[-2],
                        'title': title,
                        'url': f"https://{parsed_url.netloc}{url_path}",
                        'location': location
                    })
            
            if not page_jobs:
                break
                
            new_on_page = [j for j in page_jobs if j['url'] not in [aj['url'] for aj in all_parsed_jobs]]
            if not new_on_page:
                break
                
            all_parsed_jobs.extend(page_jobs)
            page_num += 1
            
    return all_parsed_jobs

def scrape_phenom_job_details(job_url):
    html_content = fetch_html(job_url)
    if not html_content:
        return None
        
    blocks = re.findall(r'<script\s+[^>]*type=["\']application/ld\+json["\']\s*[^>]*>(.*?)</script>', html_content, re.DOTALL | re.IGNORECASE)
    for block in blocks:
        try:
            data = json.loads(block.strip())
            if isinstance(data, dict):
                if data.get('@type') == 'JobPosting' or 'description' in data:
                    desc_html = data.get('description')
                    if desc_html:
                        return desc_html, clean_html(desc_html)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and ('description' in item or item.get('@type') == 'JobPosting'):
                        desc_html = item.get('description')
                        if desc_html:
                            return desc_html, clean_html(desc_html)
        except Exception:
            continue
            
    detail_match = re.search(r'phApp\.ddo\s*=\s*(\{.*?\});', html_content)
    if detail_match:
        try:
            detail_json = json.loads(detail_match.group(1).strip().rstrip(';'))
            job_data = detail_json['jobDetail']['data']['job']
            desc_html = job_data.get('description', '')
            if desc_html:
                return desc_html, clean_html(desc_html)
        except Exception:
            pass
            
    desc_match = re.search(r'"description"\s*:\s*"(.*?)"\s*,\s*"', html_content, re.DOTALL)
    if desc_match:
        try:
            desc_val = json.loads(f'"{desc_match.group(1)}"')
            return desc_val, clean_html(desc_val)
        except Exception:
            return desc_match.group(1), clean_html(desc_match.group(1))
            
    return None

# ==================== JIBE SCRAPER (PEPSICO / S&P GLOBAL) ====================
def scrape_jibe_board(url):
    all_parsed_jobs = []
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    api_base = f"https://{parsed_url.netloc}/api/jobs"
    
    page = 1
    while True:
        query_dict = {k: v[0] for k, v in params.items()}
        query_dict['page'] = str(page)
        api_url = f"{api_base}?{urlencode(query_dict)}"
        
        print(f"Scraping Jibe board page {page}: {api_url}", file=sys.stderr)
        req = urllib.request.Request(api_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching Jibe page {page}: {e}", file=sys.stderr)
            break
            
        jobs_list = data.get("jobs", [])
        if not jobs_list:
            break
            
        page_jobs = []
        for job_wrapper in jobs_list:
            job = job_wrapper.get("data", {})
            job_id = str(job.get("slug") or job.get("req_id") or job_wrapper.get("id"))
            title = job.get("title")
            if not job_id or not title:
                continue
                
            if job_id in existing_jobs:
                continue
                
            location = job.get("full_location") or job.get("short_location") or job.get("location_name") or "India"
            job_url = job.get("apply_url") or f"https://{parsed_url.netloc}/jobs/{job_id}"
            
            desc_html = job.get("description", "")
            desc_text = clean_html(desc_html)
            
            page_jobs.append({
                'id': job_id,
                'title': title,
                'location': location,
                'url': job_url,
                'description_html': desc_html,
                'description_text': desc_text,
                'source_board': url
            })
            
        all_parsed_jobs.extend(page_jobs)
        if len(jobs_list) < 10:
            break
        page += 1
        
    return all_parsed_jobs

# ==================== SMARTRECRUITERS (VISA) ====================
def scrape_smartrecruiters_board(url):
    all_parsed_jobs = []
    parsed_url = urlparse(url)
    path_parts = [p for p in parsed_url.path.split('/') if p]
    company = path_parts[-2] if len(path_parts) >= 2 else "visa"
    
    limit = 100
    offset = 0
    while True:
        api_url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings?limit={limit}&offset={offset}"
        print(f"Scraping SmartRecruiters page offset {offset}: {api_url}", file=sys.stderr)
        req = urllib.request.Request(api_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching SmartRecruiters offset {offset}: {e}", file=sys.stderr)
            break
            
        postings = data.get("content", [])
        if not postings:
            break
            
        page_jobs = []
        consecutive_existing = 0
        stop_pagination = False
        for post in postings:
            job_id = str(post.get("id"))
            title = post.get("name")
            if not job_id or not title:
                continue
                
            if job_id in existing_jobs:
                consecutive_existing += 1
                if consecutive_existing >= 3:
                    print(f"Found {consecutive_existing} consecutive existing SmartRecruiters jobs. Stopping pagination.", file=sys.stderr)
                    stop_pagination = True
                    break
                continue
            else:
                consecutive_existing = 0
                
            loc_obj = post.get("location", {})
            location = f"{loc_obj.get('city', '')}, {loc_obj.get('country', '')}".strip(', ') or "India"
            
            # Pre-filter location before fetching details to minimize HTTP calls
            if location and not any(loc in location.lower() for loc in target_locations):
                continue
                
            job_url = f"https://careers.smartrecruiters.com/{company}/{job_id}"
            
            # Fetch details
            details_url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings/{job_id}"
            try:
                det_req = urllib.request.Request(details_url, headers=headers)
                with urllib.request.urlopen(det_req, timeout=15) as det_res:
                    details = json.loads(det_res.read().decode('utf-8'))
                    
                sections = details.get("jobAd", {}).get("sections", {})
                full_html = ""
                for sec_name, sec_val in sections.items():
                    title_sec = sec_val.get("title", "")
                    text_sec = sec_val.get("text", "")
                    full_html += f"<h3>{title_sec}</h3>\n{text_sec}\n"
                    
                desc_text = clean_html(full_html)
                page_jobs.append({
                    'id': job_id,
                    'title': title,
                    'location': location,
                    'url': job_url,
                    'description_html': full_html,
                    'description_text': desc_text,
                    'source_board': url
                })
            except Exception as e:
                print(f"Error fetching SmartRecruiters job {job_id} details: {e}", file=sys.stderr)
                
        all_parsed_jobs.extend(page_jobs)
        if stop_pagination:
            break
        if len(postings) < limit:
            break
        offset += limit
        
    return all_parsed_jobs

def scrape_workday_board(url):
    all_parsed_jobs = []
    parsed_url = urlparse(url)
    base_api_path = parsed_url.path
    if base_api_path.endswith("/jobs"):
        base_api_path = base_api_path[:-5]
    
    limit = 20
    offset = 0
    workday_headers = headers.copy()
    workday_headers['Content-Type'] = 'application/json'
    
    while True:
        payload = {"searchText": "India", "limit": limit, "offset": offset, "appliedFacets": {}}
        print(f"Scraping Workday page offset {offset}: {url}", file=sys.stderr)
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=workday_headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching Workday page offset {offset}: {e}", file=sys.stderr)
            break
            
        postings = data.get("jobPostings", [])
        if not postings:
            break
            
        page_jobs = []
        consecutive_existing = 0
        stop_pagination = False
        for post in postings:
            ext_path = post.get("externalPath")
            title = post.get("title")
            if not ext_path or not title:
                continue
                
            job_id = ext_path.split('_')[-1]
            
            if job_id in existing_jobs:
                consecutive_existing += 1
                if consecutive_existing >= 3:
                    print(f"Found {consecutive_existing} consecutive existing Workday jobs. Stopping pagination.", file=sys.stderr)
                    stop_pagination = True
                    break
                continue
            else:
                consecutive_existing = 0
                
            location = post.get("locationsText") or "India"
            
            # Pre-filter location before fetching details to minimize HTTP calls
            if location and not any(loc in location.lower() for loc in target_locations):
                continue
                
            job_url = f"https://{parsed_url.netloc}{base_api_path.replace('/wday/cxs', '')}{ext_path}"
            
            # Fetch details
            details_url = f"https://{parsed_url.netloc}{base_api_path}{ext_path}"
            try:
                det_req = urllib.request.Request(details_url, headers=headers)
                with urllib.request.urlopen(det_req, timeout=15) as det_res:
                    details = json.loads(det_res.read().decode('utf-8'))
                    
                job_info = details.get("jobPostingInfo", {})
                desc_html = job_info.get("jobDescription", "")
                desc_text = clean_html(desc_html)
                
                page_jobs.append({
                    'id': job_id,
                    'title': title,
                    'location': location,
                    'url': job_url,
                    'description_html': desc_html,
                    'description_text': desc_text,
                    'source_board': url
                })
            except Exception as e:
                print(f"Error fetching Workday job details from {details_url}: {e}", file=sys.stderr)
                
        all_parsed_jobs.extend(page_jobs)
        if stop_pagination:
            break
        if len(postings) < limit:
            break
        offset += limit
        
    return all_parsed_jobs

# ==================== WORDPRESS (EXPEDIA) ====================
def scrape_expedia_wordpress_board(url):
    all_parsed_jobs = []
    parsed_url = urlparse(url)
    
    page = 1
    while True:
        page_url = f"https://careers.expediagroup.com/jobs/page/{page}/"
        print(f"Scraping Expedia page {page}: {page_url}", file=sys.stderr)
        req = urllib.request.Request(page_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                html_content = res.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            print(f"Error fetching Expedia page {page}: {e}", file=sys.stderr)
            break
        except Exception as e:
            print(f"Error fetching Expedia page {page}: {e}", file=sys.stderr)
            break
            
        job_links = set(re.findall(r'href="([^"]*/job/[^"/]+/[^"/]+/[^"/]+/?)"', html_content))
        if not job_links:
            break
            
        page_jobs = []
        consecutive_existing = 0
        stop_pagination = False
        for link in job_links:
            absolute_link = link if link.startswith("http") else f"https://{parsed_url.netloc}{link}"
            
            path_parts = [p for p in urlparse(absolute_link).path.split('/') if p]
            if len(path_parts) >= 4:
                title_slug = path_parts[1]
                location_slug = path_parts[2]
                job_id = path_parts[3]
                
                title = title_slug.replace('-', ' ').title()
                location = location_slug.replace('-', ' ').title()
                
                if job_id in existing_jobs:
                    consecutive_existing += 1
                    if consecutive_existing >= 3:
                        print(f"Found {consecutive_existing} consecutive existing Expedia jobs. Stopping pagination.", file=sys.stderr)
                        stop_pagination = True
                        break
                    continue
                else:
                    consecutive_existing = 0
                    
                # Pre-filter location before fetching details to minimize HTTP calls
                if location and not any(loc in location.lower() for loc in target_locations):
                    continue
                    
                try:
                    det_req = urllib.request.Request(absolute_link, headers=headers)
                    with urllib.request.urlopen(det_req, timeout=15) as det_res:
                        det_html = det_res.read().decode('utf-8')
                        
                    desc_match = re.search(r'<div class="Desc__copy text-body">(.*?)</div>', det_html, re.DOTALL)
                    if desc_match:
                        desc_html = desc_match.group(1)
                        desc_text = clean_html(desc_html)
                    else:
                        desc_html = ""
                        desc_text = clean_html(det_html)
                        
                    page_jobs.append({
                        'id': job_id,
                        'title': title,
                        'location': location,
                        'url': absolute_link,
                        'description_html': desc_html,
                        'description_text': desc_text,
                        'source_board': url
                    })
                except Exception as e:
                    print(f"Error fetching Expedia job details from {absolute_link}: {e}", file=sys.stderr)
                    
        all_parsed_jobs.extend(page_jobs)
        if stop_pagination:
            break
        if page >= 5:
            break
        page += 1
        
    return all_parsed_jobs

# ==================== EIGHTFOLD / PCSX (MICROSOFT) ====================
def scrape_microsoft_board(url):
    all_parsed_jobs = []
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    query_str = params.get('query', ['Analyst'])[0]
    
    start = 0
    while True:
        api_url = f"https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query={urllib.parse.quote(query_str)}&start={start}"
        print(f"Scraping Microsoft offset {start}: {api_url}", file=sys.stderr)
        req = urllib.request.Request(api_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching Microsoft page offset {start}: {e}", file=sys.stderr)
            break
            
        positions = data.get("data", {}).get("positions", [])
        if not positions:
            break
            
        page_jobs = []
        consecutive_existing = 0
        stop_pagination = False
        for pos in positions:
            job_id = str(pos.get("id"))
            title = pos.get("name")
            if not job_id or not title:
                continue
                
            if job_id in existing_jobs:
                consecutive_existing += 1
                if consecutive_existing >= 3:
                    print(f"Found {consecutive_existing} consecutive existing Microsoft jobs. Stopping pagination.", file=sys.stderr)
                    stop_pagination = True
                    break
                continue
            else:
                consecutive_existing = 0
                
            loc_list = pos.get("standardizedLocations") or pos.get("locations") or ["India"]
            location = ", ".join(loc_list)
            
            # Pre-filter location before fetching details to minimize HTTP calls
            if location and not any(loc in location.lower() for loc in target_locations):
                continue
                
            job_url = f"https://apply.careers.microsoft.com/careers/job/{job_id}"
            
            try:
                det_req = urllib.request.Request(job_url, headers=headers)
                with urllib.request.urlopen(det_req, timeout=15) as det_res:
                    det_html = det_res.read().decode('utf-8')
                    
                desc_html = ""
                blocks = re.findall(r'<script\s+[^>]*type=["\']application/ld\+json["\']\s*[^>]*>(.*?)</script>', det_html, re.DOTALL | re.IGNORECASE)
                for block in blocks:
                    try:
                        ld_data = json.loads(block.strip())
                        if isinstance(ld_data, dict) and (ld_data.get('@type') == 'JobPosting' or 'description' in ld_data):
                            desc_html = ld_data.get('description', '')
                            break
                    except Exception:
                        continue
                        
                if not desc_html:
                    desc_match = re.search(r'"description"\s*:\s*"(.*?)"\s*,\s*"', det_html, re.DOTALL)
                    if desc_match:
                        try:
                            desc_html = json.loads(f'"{desc_match.group(1)}"')
                        except Exception:
                            desc_html = desc_match.group(1)
                            
                desc_text = clean_html(desc_html) if desc_html else clean_html(det_html)
                
                page_jobs.append({
                    'id': job_id,
                    'title': title,
                    'location': location,
                    'url': job_url,
                    'description_html': desc_html or det_html,
                    'description_text': desc_text,
                    'source_board': url
                })
            except Exception as e:
                print(f"Error fetching Microsoft job {job_id} details: {e}", file=sys.stderr)
                
        all_parsed_jobs.extend(page_jobs)
        if stop_pagination:
            break
        if len(positions) < 10:
            break
        start += 10
        
    return all_parsed_jobs

# ==================== CUSTOM (MEDIA.NET) ====================
def scrape_medianet_board(url):
    all_parsed_jobs = []
    depts = ["business-operations", "product-marketing", "marketing", "business-development", "data-science-analytics"]
    
    for d in depts:
        dept_url = f"https://careers.media.net/{d}/"
        print(f"Scraping Media.net department page: {dept_url}", file=sys.stderr)
        req = urllib.request.Request(dept_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                html_content = res.read().decode('utf-8')
        except Exception as e:
            print(f"Error fetching Media.net department {d}: {e}", file=sys.stderr)
            continue
            
        pattern = rf'href="(https://careers\.media\.net/{d}/[^"/]+/?)"'
        matches = set(re.findall(pattern, html_content))
        
        for m in matches:
            parts = [p for p in urlparse(m).path.split('/') if p]
            if len(parts) >= 2:
                job_id = parts[1]
                title = job_id.replace('-', ' ').title()
                
                if job_id in existing_jobs:
                    continue
                    
                try:
                    det_req = urllib.request.Request(m, headers=headers)
                    with urllib.request.urlopen(det_req, timeout=15) as det_res:
                        det_html = det_res.read().decode('utf-8')
                        
                    body_text = re.sub(r"<script[^>]*>.*?</script>", "", det_html, flags=re.DOTALL)
                    body_text = re.sub(r"<style[^>]*>.*?</style>", "", body_text, flags=re.DOTALL)
                    
                    desc_text = clean_html(body_text)
                    all_parsed_jobs.append({
                        'id': job_id,
                        'title': title,
                        'location': "India (Mumbai/Bangalore)",
                        'url': m,
                        'description_html': det_html,
                        'description_text': desc_text,
                        'source_board': url
                    })
                except Exception as e:
                    print(f"Error fetching Media.net job details from {m}: {e}", file=sys.stderr)
                    
    return all_parsed_jobs

# ==================== UBER (ORACLE RECRUITING / HAPPY DANCE) ====================
def scrape_uber_board(url):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from bs4 import BeautifulSoup
    import time
    
    all_parsed_jobs = []
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    print(f"Starting Selenium Chrome Driver for Uber search: {url}", file=sys.stderr)
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(5)
        html_content = driver.page_source
    except Exception as e:
        print(f"Error starting Selenium Chrome Driver or loading Uber page: {e}", file=sys.stderr)
        if driver:
            try:
                driver.quit()
            except:
                pass
        return []
        
    try:
        driver.quit()
    except:
        pass
        
    soup = BeautifulSoup(html_content, 'html.parser')
    cards = soup.find_all('div', {'data-slot': 'card'})
    print(f"Scraped {len(cards)} job cards from Uber board", file=sys.stderr)
    
    for card in cards:
        title_el = card.find('div', {'data-slot': 'card-title'})
        a_tag = title_el.find('a') if title_el else None
        if not a_tag:
            continue
            
        title = a_tag.get_text().strip()
        href = a_tag['href']
        job_id = card.get('data-id') or href.strip('/').split('/')[-1]
        
        # Determine exact location
        desc_el = card.find('div', {'data-slot': 'card-description'})
        location = "Bengaluru, India" # default fallback
        if desc_el:
            badges = desc_el.find_all('div')
            badge_texts = [b.get_text().strip() for b in badges if b.get_text().strip()]
            if badge_texts:
                loc_txt = badge_texts[0]
                for dept_suffix in ["Engineer", "Sales", "Operations", "Product", "Design", "Marketing", "Customer Support"]:
                    if loc_txt.endswith(dept_suffix) and len(loc_txt) > len(dept_suffix):
                        loc_txt = loc_txt[:-len(dept_suffix)].strip()
                location = loc_txt
                
        # Resolve absolute job detail page URL
        job_url = href
        if not job_url.startswith('http'):
            job_url = f"https://jobs.uber.com{href}"
            
        # Check if job is already in existing_jobs database to avoid fetching details (speeds up runs!)
        if job_id in existing_jobs:
            all_parsed_jobs.append({
                'id': job_id,
                'title': title,
                'location': location,
                'url': job_url,
                'source_board': url
            })
            continue
            
        # Fetch job description over standard, fast HTTP request
        print(f"Fetching Uber job details for {title} ({job_id}) from {job_url}...", file=sys.stderr)
        try:
            req = urllib.request.Request(job_url, headers={'User-Agent': headers['User-Agent']})
            with urllib.request.urlopen(req, timeout=15) as res:
                det_html = res.read().decode('utf-8')
                
            det_soup = BeautifulSoup(det_html, 'html.parser')
            desc_div = det_soup.find('div', class_='wysiwyg')
            if desc_div:
                desc_html = str(desc_div)
                desc_text = desc_div.get_text().strip()
            else:
                body_text = re.sub(r"<script[^>]*>.*?</script>", "", det_html, flags=re.DOTALL)
                body_text = re.sub(r"<style[^>]*>.*?</style>", "", body_text, flags=re.DOTALL)
                desc_html = det_html
                desc_text = clean_html(body_text)
                
            all_parsed_jobs.append({
                'id': job_id,
                'title': title,
                'location': location,
                'url': job_url,
                'description_html': desc_html,
                'description_text': desc_text,
                'source_board': url
            })
        except Exception as e:
            print(f"Error fetching Uber job details from {job_url}: {e}", file=sys.stderr)
            
    return all_parsed_jobs

# ==================== LEVER (CRED) ====================
def scrape_lever_board(url):
    all_parsed_jobs = []
    parsed_url = urlparse(url)
    path_parts = [p for p in parsed_url.path.split('/') if p]
    company = path_parts[-1] if path_parts else "cred"
    
    api_url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    print(f"Scraping Lever board: {api_url}", file=sys.stderr)
    req = urllib.request.Request(api_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            postings = json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching Lever board {company}: {e}", file=sys.stderr)
        return []
        
    for post in postings:
        job_id = str(post.get("id"))
        title = post.get("text")
        if not job_id or not title:
            continue
            
        location = post.get("categories", {}).get("location") or "India"
        job_url = post.get("hostedUrl") or f"https://jobs.lever.co/{company}/{job_id}"
        
        desc_html_parts = []
        desc_text_parts = []
        
        intro_html = post.get("description") or post.get("descriptionBody") or ""
        if intro_html:
            desc_html_parts.append(intro_html)
            desc_text_parts.append(clean_html(intro_html))
            
        lists = post.get("lists") or []
        for lst in lists:
            header = lst.get("text") or ""
            content = lst.get("content") or ""
            if header:
                desc_html_parts.append(f"<h3>{header}</h3>")
                desc_text_parts.append(header)
            if content:
                desc_html_parts.append(content)
                desc_text_parts.append(clean_html(content))
                
        additional = post.get("additional") or post.get("additionalPlain") or ""
        if additional:
            desc_html_parts.append(additional)
            desc_text_parts.append(clean_html(additional))
            
        desc_html = "\n".join(desc_html_parts)
        desc_text = "\n".join(desc_text_parts)
        
        all_parsed_jobs.append({
            'id': job_id,
            'title': title,
            'location': location,
            'url': job_url,
            'description_html': desc_html,
            'description_text': desc_text,
            'source_board': url
        })
        
    return all_parsed_jobs

# ==================== AMAZON ====================
def scrape_amazon_board(url):
    all_parsed_jobs = []
    limit = 10
    offset = 0
    
    # We will query Amazon.jobs JSON search API
    api_url = "https://www.amazon.jobs/en/search.json?loc_query=India&country=IND"
    
    while True:
        page_url = f"{api_url}&offset={offset}"
        print(f"Scraping Amazon.jobs page offset {offset}: {page_url}", file=sys.stderr)
        
        req = urllib.request.Request(page_url, headers={'User-Agent': headers['User-Agent']})
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching Amazon page offset {offset}: {e}", file=sys.stderr)
            break
            
        postings = data.get("jobs", [])
        if not postings:
            break
            
        consecutive_existing = 0
        stop_pagination = False
        page_jobs = []
        
        for post in postings:
            job_id = str(post.get("id_icims"))
            title = post.get("title")
            if not job_id or not title:
                continue
                
            if job_id in existing_jobs:
                consecutive_existing += 1
                if consecutive_existing >= 3:
                    print(f"Found {consecutive_existing} consecutive existing Amazon jobs. Stopping pagination.", file=sys.stderr)
                    stop_pagination = True
                    break
                continue
            else:
                consecutive_existing = 0
                
            location = post.get("city", "")
            if post.get("state"):
                location += f", {post.get('state')}"
            location += f", {post.get('country_code', 'IND')}"
            
            job_path = post.get("job_path", "")
            job_url = f"https://www.amazon.jobs{job_path}" if job_path else f"https://www.amazon.jobs/en/jobs/{job_id}"
            
            desc_html_parts = []
            desc_text_parts = []
            
            desc = post.get("description") or ""
            basic = post.get("basic_qualifications") or ""
            preferred = post.get("preferred_qualifications") or ""
            
            if desc:
                desc_html_parts.append(desc)
                desc_text_parts.append(clean_html(desc))
            if basic:
                desc_html_parts.append(f"<h3>Basic Qualifications</h3>\n{basic}")
                desc_text_parts.append(f"Basic Qualifications:\n{clean_html(basic)}")
            if preferred:
                desc_html_parts.append(f"<h3>Preferred Qualifications</h3>\n{preferred}")
                desc_text_parts.append(f"Preferred Qualifications:\n{clean_html(preferred)}")
                
            desc_html = "\n\n".join(desc_html_parts)
            desc_text = "\n\n".join(desc_text_parts)
            
            page_jobs.append({
                'id': job_id,
                'title': title,
                'location': location,
                'url': job_url,
                'description_html': desc_html,
                'description_text': desc_text,
                'source_board': url
            })
            
        all_parsed_jobs.extend(page_jobs)
        if stop_pagination:
            break
            
        offset += len(postings)
        # Avoid going infinite if the api stops paginating but returns results
        if len(postings) < 10 or offset >= 100:
            break
            
    return all_parsed_jobs

# ==================== MAIN LOOP ====================
target_locations = ["india", "bangalore", "bengaluru", "gurgaon", "gurugram", "hyderabad", "noida", "pune", "mumbai", "chennai", "delhi", "ncr", "remote", "anywhere"]

for board_url in target_urls:
    print(f"Processing board: {board_url}", file=sys.stderr)
    scraped_posts = []
    
    if "greenhouse.io" in board_url or "boards.greenhouse.io" in board_url:
        posts = scrape_greenhouse_board(board_url)
        has_india_jobs = any(
            post.get('location') and any(loc in str(post.get('location')).lower() for loc in target_locations)
            for post in posts
        )
        for post in posts:
            job_id = str(post.get('id'))
            if not job_id or job_id in existing_jobs:
                continue
                
            title = post.get('title')
            location = post.get('location')
            absolute_url = post.get('absolute_url')
            if not absolute_url:
                continue
                
            if has_india_jobs and location:
                if not any(loc in str(location).lower() for loc in target_locations):
                    continue
                    
            print(f"New Greenhouse job: {title} - {location}", file=sys.stderr)
            details = scrape_greenhouse_job_details(absolute_url)
            if details:
                full_html, plain_text = details
                scraped_posts.append({
                    'id': job_id,
                    'title': title,
                    'location': location,
                    'url': absolute_url,
                    'description_html': full_html,
                    'description_text': plain_text,
                    'source_board': board_url
                })
                
    elif "gartner.com" in board_url or "careers.adobe.com" in board_url or "salesforce.com" in board_url or "nutanix.com" in board_url or "jobs.ebayinc.com" in board_url or "phenompeople" in board_url:
        posts = scrape_phenom_board(board_url)
        has_india_jobs = any(
            post.get('location') and any(loc in str(post.get('location')).lower() for loc in target_locations)
            for post in posts
        )
        for post in posts:
            job_id = str(post['id'])
            if job_id in existing_jobs:
                continue
                
            location = post.get('location')
            if has_india_jobs and location:
                if not any(loc in str(location).lower() for loc in target_locations):
                    continue
                    
            print(f"New Phenom job: {post['title']} - {location}", file=sys.stderr)
            details = scrape_phenom_job_details(post['url'])
            if details:
                full_html, plain_text = details
                scraped_posts.append({
                    'id': job_id,
                    'title': post['title'],
                    'location': location,
                    'url': post['url'],
                    'description_html': full_html,
                    'description_text': plain_text,
                    'source_board': board_url
                })
                
    elif "pepsicojobs.com" in board_url or "careers.spglobal.com" in board_url:
        scraped_posts = scrape_jibe_board(board_url)
        
    elif "api.smartrecruiters.com" in board_url:
        scraped_posts = scrape_smartrecruiters_board(board_url)
        
    elif "myworkdayjobs.com" in board_url:
        scraped_posts = scrape_workday_board(board_url)
        
    elif "amazon.jobs" in board_url:
        scraped_posts = scrape_amazon_board(board_url)
        
    elif "careers.expediagroup.com" in board_url:
        scraped_posts = scrape_expedia_wordpress_board(board_url)
        
    elif "apply.careers.microsoft.com" in board_url or "careers.microsoft.com" in board_url:
        scraped_posts = scrape_microsoft_board(board_url)
        
    elif "careers.media.net" in board_url:
        scraped_posts = scrape_medianet_board(board_url)
        
    elif "jobs.uber.com" in board_url:
        scraped_posts = scrape_uber_board(board_url)
        
    elif "lever.co" in board_url or "jobs.lever.co" in board_url:
        scraped_posts = scrape_lever_board(board_url)
        
    # Apply global location filter and deduplication to updates
    board_new_count = 0
    for post in scraped_posts:
        jid = str(post['id'])
        if jid in existing_jobs:
            continue
            
        location = post.get('location')
        if location and not any(loc in str(location).lower() for loc in target_locations):
            continue
            
        new_jobs.append(post)
        updated_jobs_list.append(post)
        existing_jobs[jid] = post
        board_new_count += 1

    # Incremental write to prevent losing progress if subsequent scrapers hang/crash
    if board_new_count > 0:
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(updated_jobs_list, f, indent=4, ensure_ascii=False)

# Print results to stdout
print(json.dumps({"new_jobs": new_jobs}, indent=4))
