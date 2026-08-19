#!/usr/bin/env python3
"""
Amazon India Automated Price Tracker
------------------------------------
Tracks prices, deal badges, coupons, bank offers, and stock status for Amazon India products.
Stores price history in SQLite and generates categorized summary reports.
"""

import os
import re
import sys
import ssl
import json
import time
import html
import random
import sqlite3
import argparse
import urllib.request
import urllib.error
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'amazon_products.json')
DB_FILE = os.path.join(BASE_DIR, 'amazon_prices.db')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
REPORT_FILE = os.path.join(REPORTS_DIR, 'amazon_price_report.md')

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
]

# SSL Context to ensure compatibility across macOS Python installs
SSL_CONTEXT = ssl._create_unverified_context()

def get_db_connection(db_path=DB_FILE):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            asin TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT,
            baseline_price REAL,
            target_price REAL,
            active INTEGER DEFAULT 1,
            last_checked TEXT,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asin TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            price REAL,
            mrp REAL,
            discount_pct REAL,
            coupon TEXT,
            in_stock INTEGER DEFAULT 1,
            deal_badge TEXT,
            bank_offers TEXT,
            raw_price_str TEXT,
            FOREIGN KEY (asin) REFERENCES products(asin)
        )
    """)
    # Schema migrations for existing databases
    cursor.execute("PRAGMA table_info(price_history)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    for col_name, col_type in [("discount_pct", "REAL"), ("coupon", "TEXT"), ("bank_offers", "TEXT")]:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE price_history ADD COLUMN {col_name} {col_type}")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_asin_time ON price_history(asin, timestamp)")
    conn.commit()


def sync_products_from_config(conn, config_path=CONFIG_FILE):
    if not os.path.exists(config_path):
        return []
    with open(config_path, 'r', encoding='utf-8') as f:
        products = json.load(f)

    now_str = datetime.now().isoformat()
    cursor = conn.cursor()
    for p in products:
        cursor.execute("""
            INSERT INTO products (asin, title, category, baseline_price, target_price, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asin) DO UPDATE SET
                title = excluded.title,
                category = excluded.category,
                baseline_price = excluded.baseline_price,
                target_price = excluded.target_price,
                active = excluded.active
        """, (
            p['asin'],
            p.get('title', 'Unknown Product'),
            p.get('category', 'General'),
            float(p.get('baseline_price') or 0.0),
            float(p.get('target_price') or 0.0),
            1 if p.get('active', True) else 0,
            now_str
        ))
    conn.commit()
    return products

def parse_price_str(price_str):
    if not price_str:
        return None
    cleaned = re.sub(r'[^0-9.]', '', price_str)
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None

def extract_product_details_from_html(html_text):
    """
    Extracts all pricing, discounts, deal badges, coupons, bank offers, and stock status.
    """
    price = None
    mrp = None
    raw_price_str = None
    deal_badge = None
    coupon = None
    discount_pct = None
    bank_offers = []
    in_stock = True
    title = None

    # 1. Product Title
    title_match = re.search(r'<span[^>]*id=["\']productTitle["\'][^>]*>(.*?)</span>', html_text, re.DOTALL | re.IGNORECASE)
    if title_match:
        title = html.unescape(title_match.group(1)).strip()

    # 2. Deal Badges (e.g. "Limited time deal", "Deal of the Day", "Great Indian Festival Deal")
    deal_match = re.search(r'\b(Limited time deal|Deal of the Day|Great Indian Festival Deal|Lightning Deal)\b', html_text, re.IGNORECASE)
    if deal_match:
        deal_badge = deal_match.group(1).title()

    # 3. Savings / Discount Percentage from badge
    savings_match = re.search(r'class=["\'][^"\']*savingsPercentage[^"\']*["\'][^>]*>([^<]+)</span>', html_text, re.IGNORECASE)
    if savings_match:
        savings_text = re.sub(r'[^0-9]', '', savings_match.group(1))
        if savings_text:
            discount_pct = float(savings_text)

    # 4. Coupons & Checkbox Vouchers
    coupon_match = re.search(r'(?:Save|Apply)\s+(?:extra\s+)?(₹\d+|\d+%\s*off|\d+%)\s*(?:with\s+coupon|coupon)', html_text, re.IGNORECASE)
    if coupon_match:
        coupon = coupon_match.group(0).strip()

    # 5. Bank / Card Offers
    bank_matches = re.findall(r'(?:Upto|Up to|Flat|Get)\s+₹?\d+[\d,]*\s+(?:Instant\s+Discount|Cashback|discount)[^<\n.]{5,80}', html_text, re.IGNORECASE)
    if bank_matches:
        # Keep unique first 2 offers
        cleaned_offers = []
        for b in bank_matches:
            b_clean = re.sub(r'\s+', ' ', b).strip()
            if b_clean not in cleaned_offers:
                cleaned_offers.append(b_clean)
        bank_offers = cleaned_offers[:2]

    # 6. Availability / Stock
    avail_match = re.search(r'<div[^>]*id=["\']availability["\'][^>]*>(.*?)</div>', html_text, re.DOTALL | re.IGNORECASE)
    if avail_match:
        avail_text = re.sub(r'<[^>]+>', '', avail_match.group(1)).strip().lower()
        if 'currently unavailable' in avail_text or 'out of stock' in avail_text:
            in_stock = False

    # 7. Selling Price patterns (ordered by reliability)
    patterns = [
        r'class=["\'][^"\']*apexPriceToPay[^"\']*["\'][^>]*>.*?<span[^>]*class=["\']a-offscreen["\'][^>]*>([^<]+)</span>',
        r'id=["\']corePriceDisplay_desktop_feature_div["\'][^>]*>.*?<span[^>]*class=["\']a-offscreen["\'][^>]*>([^<]+)</span>',
        r'id=["\']corePrice_desktop["\'][^>]*>.*?<span[^>]*class=["\']a-offscreen["\'][^>]*>([^<]+)</span>',
        r'id=["\']priceblock_dealprice["\'][^>]*>([^<]+)</span>',
        r'id=["\']priceblock_ourprice["\'][^>]*>([^<]+)</span>',
        r'id=["\']priceblock_saleprice["\'][^>]*>([^<]+)</span>',
        r'<span[^>]*class=["\'][^"\']*a-price[^"\']*["\'][^>]*>.*?<span[^>]*class=["\']a-offscreen["\'][^>]*>([^<]+)</span>',
        r'["\']priceAmount["\']\s*:\s*([0-9]+(?:\.[0-9]+)?)'
    ]

    for pat in patterns:
        m = re.search(pat, html_text, re.DOTALL | re.IGNORECASE)
        if m:
            candidate_str = m.group(1).strip()
            parsed = parse_price_str(candidate_str)
            if parsed:
                price = parsed
                raw_price_str = candidate_str
                break

    # 8. MRP extraction
    mrp_match = re.search(r'class=["\'][^"\']*a-text-price[^"\']*["\'][^>]*>.*?<span[^>]*class=["\']a-offscreen["\'][^>]*>([^<]+)</span>', html_text, re.DOTALL | re.IGNORECASE)
    if mrp_match:
        mrp = parse_price_str(mrp_match.group(1))

    # Calculate discount % from MRP if missing
    if discount_pct is None and mrp and price and mrp > price:
        discount_pct = round(((mrp - price) / mrp) * 100, 1)

    return {
        'title': title,
        'price': price,
        'mrp': mrp,
        'discount_pct': discount_pct,
        'raw_price_str': raw_price_str,
        'deal_badge': deal_badge,
        'coupon': coupon,
        'bank_offers': ' | '.join(bank_offers) if bank_offers else None,
        'in_stock': in_stock
    }

def fetch_product_page(asin, retries=2, backoff=2.0):
    url = f'https://www.amazon.in/dp/{asin}'
    ua = random.choice(USER_AGENTS)
    headers = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'identity',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }

    req = urllib.request.Request(url, headers=headers)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=12, context=SSL_CONTEXT) as resp:
                if resp.status == 200:
                    html_bytes = resp.read()
                    try:
                        return html_bytes.decode('utf-8', errors='replace')
                    except Exception:
                        return html_bytes.decode('latin-1', errors='replace')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            elif e.code in (429, 503):
                time.sleep(backoff * (attempt + 1))
            else:
                time.sleep(1.0)
        except Exception:
            time.sleep(backoff)

    return None

def check_single_product(asin, conn=None, dry_run=False):
    html_content = fetch_product_page(asin)
    if not html_content:
        return {'asin': asin, 'success': False, 'error': 'Failed to fetch page'}

    details = extract_product_details_from_html(html_content)
    now_str = datetime.now().isoformat()
    details['asin'] = asin
    details['timestamp'] = now_str
    details['success'] = details['price'] is not None

    if conn and details['success'] and not dry_run:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO price_history (asin, timestamp, price, mrp, discount_pct, coupon, in_stock, deal_badge, bank_offers, raw_price_str)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            asin,
            now_str,
            details['price'],
            details['mrp'],
            details['discount_pct'],
            details['coupon'],
            1 if details['in_stock'] else 0,
            details['deal_badge'],
            details['bank_offers'],
            details['raw_price_str']
        ))
        cursor.execute("UPDATE products SET last_checked = ? WHERE asin = ?", (now_str, asin))
        conn.commit()

    return details

def get_product_price_summary(conn, asin):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE asin = ?", (asin,))
    prod = cursor.fetchone()
    if not prod:
        return None

    cursor.execute("""
        SELECT * FROM price_history
        WHERE asin = ?
        ORDER BY timestamp DESC LIMIT 2
    """, (asin,))
    recent = cursor.fetchall()

    latest_price = recent[0]['price'] if len(recent) > 0 else None
    prev_price = recent[1]['price'] if len(recent) > 1 else None

    cursor.execute("SELECT MIN(price) as min_price FROM price_history WHERE asin = ? AND price > 0", (asin,))
    row_min = cursor.fetchone()
    min_price = row_min['min_price'] if row_min else None

    baseline = prod['baseline_price']
    target = prod['target_price']

    drop_from_baseline = None
    drop_pct_baseline = None
    if latest_price and baseline and baseline > 0:
        drop_from_baseline = round(baseline - latest_price, 2)
        drop_pct_baseline = round(((baseline - latest_price) / baseline) * 100, 1)

    drop_from_prev = None
    if latest_price and prev_price:
        drop_from_prev = round(prev_price - latest_price, 2)

    is_all_time_low = (latest_price is not None and min_price is not None and latest_price <= min_price)
    hit_target = (latest_price is not None and target is not None and latest_price <= target)

    # Consolidated Deal / Offer Info
    deal_info = []
    if len(recent) > 0:
        if recent[0]['deal_badge']:
            deal_info.append(f"🏷️ {recent[0]['deal_badge']}")
        if recent[0]['discount_pct'] and recent[0]['discount_pct'] > 0:
            deal_info.append(f"💥 {recent[0]['discount_pct']}% off MRP")
        if recent[0]['coupon']:
            deal_info.append(f"🎟️ {recent[0]['coupon']}")
        if recent[0]['bank_offers']:
            deal_info.append(f"💳 {recent[0]['bank_offers']}")

    return {
        'asin': asin,
        'title': prod['title'],
        'category': prod['category'],
        'baseline_price': baseline,
        'target_price': target,
        'latest_price': latest_price,
        'mrp': recent[0]['mrp'] if len(recent) > 0 else None,
        'prev_price': prev_price,
        'min_price': min_price,
        'drop_from_baseline': drop_from_baseline,
        'drop_pct_baseline': drop_pct_baseline,
        'drop_from_prev': drop_from_prev,
        'is_all_time_low': is_all_time_low,
        'hit_target': hit_target,
        'deal_badge': recent[0]['deal_badge'] if len(recent) > 0 else None,
        'coupon': recent[0]['coupon'] if len(recent) > 0 else None,
        'discount_pct': recent[0]['discount_pct'] if len(recent) > 0 else None,
        'deal_summary': ' • '.join(deal_info) if deal_info else 'Standard Price',
        'in_stock': bool(recent[0]['in_stock']) if len(recent) > 0 else True,
        'last_checked': prod['last_checked']
    }

def generate_markdown_report(conn, output_path=REPORT_FILE):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cursor = conn.cursor()
    cursor.execute("SELECT asin FROM products WHERE active = 1 ORDER BY category, title")
    rows = cursor.fetchall()

    summaries = []
    for r in rows:
        s = get_product_price_summary(conn, r['asin'])
        if s:
            summaries.append(s)

    now_display = datetime.now().strftime('%d %b %Y, %I:%M %p')

    by_category = {}
    price_drops = []
    target_hits = []

    for s in summaries:
        cat = s['category'] or 'General'
        by_category.setdefault(cat, []).append(s)
        if s.get('drop_from_baseline') and s['drop_from_baseline'] > 0:
            price_drops.append(s)
        if s.get('hit_target'):
            target_hits.append(s)

    lines = []
    lines.append(f"# 🛒 Amazon India Price & Deal Tracker Report\n")
    lines.append(f"**Generated**: {now_display} | **Tracked Products**: {len(summaries)}\n")

    if target_hits:
        lines.append("## 🎯 Target Price Hits (Buy Now Recommendations)\n")
        lines.append("| Product | Current Price | Target Price | Baseline | Offers / Deals | Link |")
        lines.append("|---|---|---|---|---|---|")
        for s in target_hits:
            cur_p = f"₹{s['latest_price']:,.2f}" if s['latest_price'] else "N/A"
            lines.append(f"| **{s['title']}** | {cur_p} | ₹{s['target_price']:,.2f} | ₹{s['baseline_price']:,.2f} | {s['deal_summary']} | [View](https://www.amazon.in/dp/{s['asin']}) |")
        lines.append("\n")

    if price_drops:
        lines.append("## 🔥 Active Price Drops\n")
        lines.append("| Product | Current Price | Baseline | Savings | Drop % | Offers / Deals |")
        lines.append("|---|---|---|---|---|---|")
        for s in price_drops:
            lines.append(f"| {s['title']} | **₹{s['latest_price']:,.2f}** | ₹{s['baseline_price']:,.2f} | -₹{s['drop_from_baseline']:,.2f} | **{s['drop_pct_baseline']}% OFF** | {s['deal_summary']} |")
        lines.append("\n")

    lines.append("## 📋 All Tracked Products & Offers\n")
    for cat, items in by_category.items():
        lines.append(f"### {cat}\n")
        lines.append("| Product | Current Price | Baseline | Target | Active Deals & Offers | Status | Link |")
        lines.append("|---|---|---|---|---|---|---|")
        for s in items:
            cur_price_str = f"₹{s['latest_price']:,.2f}" if s['latest_price'] else "*Unchecked*"
            status = "🟢 In Stock" if s['in_stock'] else "🔴 Out of Stock"
            if s.get('is_all_time_low') and s['latest_price']:
                status += " 🌟 Low"
            lines.append(f"| {s['title']} | **{cur_price_str}** | ₹{s['baseline_price']:,.2f} | ₹{s['target_price']:,.2f} | {s['deal_summary']} | {status} | [Amazon](https://www.amazon.in/dp/{s['asin']}) |")
        lines.append("\n")

    content = "\n".join(lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return output_path

def run_price_check(conn, delay_sec=1.5, dry_run=False):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE active = 1 ORDER BY category, title")
    products = cursor.fetchall()

    print(f"Starting price check for {len(products)} products...")
    print("=" * 85)

    success_count = 0
    drop_count = 0

    for idx, p in enumerate(products, 1):
        asin = p['asin']
        title = p['title']
        baseline = p['baseline_price']

        print(f"[{idx}/{len(products)}] Checking {asin}: {title[:35]}...", end=' ', flush=True)
        res = check_single_product(asin, conn=conn, dry_run=dry_run)

        if res.get('success'):
            success_count += 1
            cur_price = res['price']
            diff = baseline - cur_price
            diff_str = f"(Baseline: ₹{baseline:.2f})"
            if diff > 0:
                drop_count += 1
                diff_str = f"🔥 SAVING ₹{diff:.2f} ({round((diff/baseline)*100, 1)}% drop!)"
            elif diff < 0:
                diff_str = f"📈 +₹{abs(diff):.2f}"

            offer_tags = []
            if res.get('deal_badge'):
                offer_tags.append(f"🏷️ {res['deal_badge']}")
            if res.get('discount_pct'):
                offer_tags.append(f"{res['discount_pct']}% OFF MRP")
            if res.get('coupon'):
                offer_tags.append(f"🎟️ {res['coupon']}")

            tag_str = f" [{' • '.join(offer_tags)}]" if offer_tags else ""
            print(f"-> ₹{cur_price:.2f} {diff_str}{tag_str}")
        else:
            print(f"-> [Baseline: ₹{baseline:.2f}]")

        if idx < len(products):
            time.sleep(delay_sec + random.uniform(0.2, 0.8))

    print("=" * 85)
    print(f"Price check finished: {success_count}/{len(products)} live prices retrieved. {drop_count} price drops detected.")

    report_path = generate_markdown_report(conn)
    print(f"Markdown Report generated at: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Amazon India Price & Deal Tracker")
    parser.add_argument("--check", action="store_true", help="Run live price & deal check on all active products")
    parser.add_argument("--asin", type=str, help="Check single product by ASIN")
    parser.add_argument("--report", action="store_true", help="Generate markdown report without scraping")
    parser.add_argument("--list", action="store_true", help="List all tracked products")
    parser.add_argument("--dry-run", action="store_true", help="Do not write price updates to DB")

    args = parser.parse_args()

    conn = get_db_connection()
    sync_products_from_config(conn)

    if args.list:
        cursor = conn.cursor()
        cursor.execute("SELECT asin, category, title, baseline_price, target_price FROM products WHERE active = 1 ORDER BY category")
        rows = cursor.fetchall()
        print(f"\n{len(rows)} Tracked Products:")
        print("-" * 90)
        for r in rows:
            print(f"{r['asin']} | [{r['category']}] {r['title'][:40]:<40} | Base: ₹{r['baseline_price']:<7.2f} | Target: ₹{r['target_price']:<7.2f}")
        print("-" * 90)

    elif args.asin:
        print(f"Checking single ASIN: {args.asin}...")
        res = check_single_product(args.asin, conn=conn, dry_run=args.dry_run)
        print(json.dumps(res, indent=2, ensure_ascii=False))

    elif args.report:
        report_path = generate_markdown_report(conn)
        print(f"Markdown Report generated at: {report_path}")

    elif args.check:
        run_price_check(conn, dry_run=args.dry_run)

    else:
        parser.print_help()

if __name__ == '__main__':
    main()
