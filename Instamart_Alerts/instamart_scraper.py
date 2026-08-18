from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import sqlite3
import re
import urllib.parse
import urllib.request
import sys
import os
import json
import argparse
from datetime import datetime, timezone



# Dynamically resolve instamart_prices.db in the same directory as this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instamart_prices.db")

# Load local .env variables if present
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


# Tracked Delivery Locations (Add or remove locations here anytime in the future!)
TRACKED_LOCATIONS = [
    "HSR Layout Bangalore", 
    "Manganapallaya Bangalore",
    # "Indiranagar Bangalore",
]

# Watchlist Keywords (Add or remove keywords here anytime in the future!)
TRACKED_KEYWORDS = [
    "milk",
    "mustard oil",
    "eggs",
    "oil",
    "soap",
    "shampoo",
    "sugar",
    "coffee",
]



def generate_product_id(item_name, quantity):
    """Generates a unique, readable slug for a product based on name and weight."""
    raw = f"{item_name.lower().strip()}-{quantity.lower().strip()}"
    slug = re.sub(r'[^a-z0-9]+', '-', raw).strip('-')
    return slug

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS instamart_prices (
            product_id TEXT,
            search_query TEXT,
            location TEXT,
            item_name TEXT,
            quantity TEXT,
            price REAL,
            description TEXT,
            web_link TEXT,
            image_url TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (product_id, location, scraped_at)
        )
    """)
    conn.commit()
    return conn, cursor

def get_tracked_search_queries():
    """Queries SQLite database for all distinct search_query strings saved in historical runs."""
    if not os.path.exists(DB_PATH):
        return ["milk"]
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT search_query FROM instamart_prices WHERE search_query IS NOT NULL AND search_query != '';")
        rows = cursor.fetchall()
        conn.close()
        queries = [r[0].strip() for r in rows if r[0]]
        return queries if queries else ["milk"]
    except Exception:
        return ["milk"]

def clean_price(price_str):
    if not price_str or price_str == 'N/A':
        return None
    digits = ''.join(c for c in price_str if c.isdigit() or c == '.')
    try:
        return float(digits)
    except ValueError:
        return None

DEFAULT_RECIPIENT_EMAIL = "anwar.ejaz181@gmail.com"

def send_email_alert(rows):
    """Sends a formatted HTML email price drop alert via Gmail SMTP if SENDER_EMAIL and SENDER_PASSWORD are set."""
    if not rows:
        return

    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")
    recipient_email = os.getenv("RECIPIENT_EMAIL", DEFAULT_RECIPIENT_EMAIL)
    
    if not sender_email or not sender_password:
        return

        
    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        import smtplib

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎉 Swiggy Instamart Alert: {len(rows)} Price Drops Found!"
        msg["From"] = f"Instamart Tracker <{sender_email}>"
        msg["To"] = recipient_email

        html_cards = ""
        for r in rows:
            prod_id, loc, name, qty, old_p, new_p, diff, pct, old_t, new_t, link = r
            html_cards += f"""
            <div style="background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="font-size: 15px; font-weight: bold; color: #1a1a1a; margin-bottom: 6px; line-height: 1.3;">{name}</div>
                <div style="margin-bottom: 12px;">
                    <span style="font-size: 12px; color: #555; background: #f0f0f0; padding: 3px 8px; border-radius: 12px; font-weight: 500;">{qty}</span>
                    <span style="font-size: 12px; color: #777; margin-left: 6px;">📍 {loc}</span>
                </div>
                <div style="background: #fff5ed; border: 1px solid #ffd8be; border-radius: 6px; padding: 10px 14px; margin-bottom: 14px; display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <span style="font-size: 13px; color: #888; text-decoration: line-through;">₹{old_p:.0f}</span>
                        <span style="font-size: 20px; font-weight: 800; color: #e53935; margin-left: 8px;">₹{new_p:.0f}</span>
                    </div>
                    <div style="background-color: #2e7d32; color: #ffffff; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 20px;">
                        Save ₹{diff:.0f} ({pct}% OFF)
                    </div>
                </div>
                <a href="{link}" style="display: block; width: 100%; text-align: center; background-color: #fc8019; color: #ffffff; padding: 12px 0; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; box-sizing: border-box;" target="_blank">
                    🛒 View Item on Instamart
                </a>
            </div>
            """

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f5f7; margin: 0; padding: 12px;">
            <div style="max-width: 500px; margin: 0 auto;">
                <div style="background-color: #fc8019; color: #ffffff; padding: 18px 16px; border-radius: 8px; text-align: center; margin-bottom: 16px;">
                    <h2 style="margin: 0; font-size: 20px; font-weight: 800;">🎉 Swiggy Instamart Price Drop!</h2>
                    <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.95;">Found {len(rows)} discount(s) > 20% on your watchlist</p>
                </div>

                {html_cards}

                <div style="text-align: center; padding: 12px 0; font-size: 11px; color: #888;">
                    Automated Alert • Swiggy Instamart Price Tracker • HSR Layout Bangalore
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))


        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [recipient_email], msg.as_string())
        server.quit()
        print(f"📧 Email price drop alert sent successfully to {recipient_email}!")
    except Exception as e:
        print(f"⚠️ Failed to send Email alert: {e}")

def send_whatsapp_alert(message_text):
    """Sends a free WhatsApp alert via CallMeBot API if CALLMEBOT_PHONE and CALLMEBOT_API_KEY environment variables are set."""
    phone = os.getenv("CALLMEBOT_PHONE")
    api_key = os.getenv("CALLMEBOT_API_KEY")
    
    if not phone or not api_key:
        return
        
    try:
        encoded_text = urllib.parse.quote(message_text)
        url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_text}&apikey={api_key}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201):
                print("📱 WhatsApp price drop alert delivered successfully!")
            else:
                print(f"⚠️ WhatsApp API returned status: {resp.status}")
    except Exception as e:
        print(f"⚠️ Failed to send WhatsApp alert: {e}")


def compare_prices(target_location=None, min_scraped_at=None):
    """Calculates and displays ONLY price drops per location directly from the SQLite database."""
    if not os.path.exists(DB_PATH):
        print("No database found yet. Run a scraper command first (e.g. python3 instamart_scraper.py)!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    WITH PriceHistory AS (
        SELECT 
            product_id,
            search_query,
            location,
            item_name,
            quantity,
            price,
            web_link,
            scraped_at,
            LAG(price) OVER (PARTITION BY product_id, location ORDER BY scraped_at ASC) as previous_price,
            LAG(scraped_at) OVER (PARTITION BY product_id, location ORDER BY scraped_at ASC) as previous_time,
            ROW_NUMBER() OVER (PARTITION BY product_id, location ORDER BY scraped_at DESC) as rn
        FROM instamart_prices
    )
    SELECT 
        product_id,
        location,
        item_name,
        quantity,
        previous_price,
        price as current_price,
        (previous_price - price) as price_drop,
        ROUND(((previous_price - price) / previous_price) * 100, 2) as drop_percentage,
        previous_time,
        scraped_at as current_time,
        web_link
    FROM PriceHistory
    WHERE rn = 1 AND previous_price IS NOT NULL AND price < 0.8 * previous_price
    """
    params = []
    if target_location:
        query += " AND location LIKE ?"
        params.append(f"%{target_location}%")
    if min_scraped_at:
        query += " AND current_time >= ?"
        params.append(min_scraped_at)

    query += " ORDER BY price_drop DESC;"
    cursor.execute(query, tuple(params))


    rows = cursor.fetchall()
    
    if not rows:
        print("\n==================================================")
        print("            PRICE DROP SUMMARY                    ")
        print("==================================================")
        print("No price drops detected for your watchlist items.")
        print("==================================================\n")
        conn.close()
        return

    print("\n==================================================")
    print("            PRICE DROP SUMMARY                    ")
    print("==================================================")
    
    whatsapp_lines = ["🎉 *SWIGGY INSTAMART PRICE DROP ALERT!*"]
    for r in rows:
        prod_id, loc, name, qty, old_p, new_p, diff, pct, old_t, new_t, link = r
        print(f"🎉 PRICE DROP! [{loc}] [{qty}] {name}")
        print(f"   Old Price: ₹{old_p} ({old_t})")
        print(f"   New Price: ₹{new_p} ({new_t})")
        print(f"   SAVINGS:   ₹{diff:.2f} ({pct}% price drop!)")
        print(f"   Web Link:  {link}\n")
        
        whatsapp_lines.append(
            f"\n🛒 *{name}* ({qty})\n"
            f"   Old: ₹{old_p} ➔ New: ₹{new_p} (*Save ₹{diff:.0f} - {pct}% OFF!*)\n"
            f"   🔗 {link}"
        )
            
    print(f"Total Price Drops Found: {len(rows)}")
    print("==================================================\n")
    conn.close()

    # Send Email and WhatsApp notifications if configured
    send_email_alert(rows)
    send_whatsapp_alert("\n".join(whatsapp_lines))



def set_browser_location(driver, wait, location_str):
    """Sets the active delivery location in the Swiggy Instamart browser session."""
    print(f"Setting location: '{location_str}'...")
    try:
        driver.get("https://www.swiggy.com/instamart")
        time.sleep(3)
        
        search_containers = driver.find_elements(By.CSS_SELECTOR, '[data-testid="search-location"]')
        if search_containers:
            search_containers[0].click()
            time.sleep(1)
            
            location_input = wait.until(EC.presence_of_element_located((By.CLASS_NAME, '_1wkJd')))
            driver.execute_script("arguments[0].value = '';", location_input)
            location_input.send_keys(location_str)
            
            first_suggestion = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div._2esgM')))
            first_suggestion.click()
            time.sleep(1)
            
            confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Confirm Location")]')))
            confirm_btn.click()
            time.sleep(5)
            print(f"✓ Location set to '{location_str}'")
    except Exception as loc_err:
        print(f"Location modal handled (note: {loc_err})")


def main():
    parser = argparse.ArgumentParser(description="Swiggy Instamart Live Price Scraper & Tracker")
    parser.add_argument("query", nargs="?", default=None, help="Product query to search (e.g. milk, paneer, eggs)")
    parser.add_argument("--location", "-l", default=None, help="Specific delivery location (defaults to all TRACKED_LOCATIONS)")
    parser.add_argument("--compare", "-c", action="store_true", help="Run instant database price comparison without opening browser")
    
    args = parser.parse_args()

    target_locations = [args.location] if args.location else TRACKED_LOCATIONS
    target_queries = [args.query] if args.query else TRACKED_KEYWORDS

    if args.compare:
        loc_display = args.location if args.location else "ALL TRACKED LOCATIONS"
        print(f"Running Instant Database Price Comparison (Location filter: '{loc_display}')...\n")
        compare_prices(target_location=args.location)
        return

    print(f"Tracked Locations ({len(target_locations)}): {target_locations}")
    print(f"Watchlist Keywords ({len(target_queries)}): {target_queries}\n")

    run_start_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })

        wait = WebDriverWait(driver, 10)
        conn, cursor = init_db()
        total_inserted = 0

        # Loop over each target location
        for loc_idx, current_location in enumerate(target_locations):
            print(f"\n{'='*60}")
            print(f"📍 [{loc_idx + 1}/{len(target_locations)}] Target Delivery Location: '{current_location}'")
            print(f"{'='*60}")

            set_browser_location(driver, wait, current_location)

            # Loop over all target queries for this location
            for q_idx, search_query in enumerate(target_queries):
                print(f"\n[{q_idx + 1}/{len(target_queries)}] Processing search query: '{search_query}' ({current_location})...")
                
                try:
                    # 1. Try input box typing first, fallback to direct search URL navigation if unclickable
                    search_success = False
                    try:
                        search_btns = driver.find_elements(By.XPATH, '//button[contains(., "Search for")]')
                        if search_btns:
                            driver.execute_script("arguments[0].click();", search_btns[0])
                            time.sleep(1.5)
                        
                        product_input = driver.find_element(By.CSS_SELECTOR, 'input[type="search"]')
                        driver.execute_script("arguments[0].value = '';", product_input)
                        product_input.send_keys(search_query)
                        time.sleep(1)
                        product_input.send_keys("\n")
                        search_success = True
                    except Exception:
                        pass

                    if not search_success:
                        # Fallback to direct search URL navigation
                        search_url = f"https://www.swiggy.com/instamart/search?query={urllib.parse.quote_plus(search_query)}"
                        driver.get(search_url)
                    
                    print(f"   Waiting for initial listings for '{search_query}' to render...")
                    try:
                        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div._3Rr1X, div[data-testid*="item"]')))
                    except Exception:
                        time.sleep(4)
                    
                    print(f"   Scrolling page to load full product catalog...")
                    last_card_count = 0
                    for scroll_step in range(6):
                        cards_in_dom = driver.find_elements(By.CSS_SELECTOR, 'div._3Rr1X, div[data-testid*="item"]')
                        current_count = len(cards_in_dom)
                        if current_count == 0:
                            time.sleep(3)
                            cards_in_dom = driver.find_elements(By.CSS_SELECTOR, 'div._3Rr1X, div[data-testid*="item"]')
                            current_count = len(cards_in_dom)
                        if current_count == 0 or current_count == last_card_count:
                            break
                        last_card_count = current_count
                        driver.execute_script("arguments[0].scrollIntoView(true);", cards_in_dom[-1])
                        time.sleep(2.5)

                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    cards = soup.find_all('div', class_='_3Rr1X')
                    if not cards:
                        cards = soup.select('div[data-testid*="item"]')

                    print(f"   Found {len(cards)} total product cards for '{search_query}'.")
                    
                    current_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

                    for idx, card in enumerate(cards):
                        name_el = card.find('div', class_='_1lbNR')
                        name = name_el.get_text().strip() if name_el else 'N/A'
                        
                        desc_el = card.find('div', class_='_3bM-V')
                        desc = desc_el.get_text().strip() if desc_el else 'N/A'
                        
                        weight_el = card.find('div', class_='_3wq_F')
                        weight = weight_el.get_text().strip() if weight_el else 'N/A'
                        
                        price_el = card.find('div', class_='_2jn41')
                        raw_price = price_el.get_text().strip() if price_el else 'N/A'
                        numeric_price = clean_price(raw_price)
                        
                        img_el = card.find('img')
                        image_url = img_el.get('src') if img_el and img_el.get('src') else 'N/A'
                        
                        full_item_query = f"{name} {weight}".strip()
                        encoded_name = urllib.parse.quote_plus(full_item_query)
                        web_link = f"https://www.swiggy.com/instamart/search?query={encoded_name}"
                        product_id = generate_product_id(name, weight)
                        
                        cursor.execute("""
                            INSERT OR REPLACE INTO instamart_prices 
                            (product_id, search_query, location, item_name, quantity, price, description, web_link, image_url, scraped_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (product_id, search_query, current_location, name, weight, numeric_price, desc, web_link, image_url, current_timestamp))
                        total_inserted += 1

                    conn.commit()
                    print(f"   Successfully saved {len(cards)} listings for '{search_query}' (Location: '{current_location}').")
                    time.sleep(2)

                except Exception as q_err:
                    print(f"   ⚠️ Warning: Error processing query '{search_query}': {q_err}. Continuing to next query...")

        print(f"\nAll scraping runs completed across {len(target_locations)} location(s). Total products stored/updated: {total_inserted}")
        conn.close()
        driver.quit()
        print("Browser session closed cleanly.")
        
        # Run price drop comparison ONLY for items scraped in this specific run
        if total_inserted > 0:
            target_loc_filter = args.location if args.location else None
            compare_prices(target_location=target_loc_filter, min_scraped_at=run_start_time)
        else:
            print("No new products were scraped in this run. Skipping price drop alert.")
        
    except Exception as e:
        print(f"\nScraping failed with error: {e}")



if __name__ == "__main__":
    main()
