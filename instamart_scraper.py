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
import argparse


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


DEFAULT_LOCATION = "HSR Layout Bangalore"

# Watchlist Keywords (Add or remove keywords here anytime in the future!)
TRACKED_KEYWORDS = [ "milk", "mustard oil","eggs", "oil", "soap","shampoo","sugar","coffee"]


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

        html_table_rows = ""
        for r in rows:
            prod_id, loc, name, qty, old_p, new_p, diff, pct, old_t, new_t, link = r
            html_table_rows += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 12px; font-weight: bold; color: #333;">{name}<br><span style="font-weight: normal; color: #666; font-size: 12px;">{qty} | {loc}</span></td>
                <td style="padding: 12px; color: #888; text-decoration: line-through;">₹{old_p:.0f}</td>
                <td style="padding: 12px; font-weight: bold; color: #e53935;">₹{new_p:.0f}</td>
                <td style="padding: 12px; font-weight: bold; color: #2e7d32;">₹{diff:.0f} ({pct}% OFF)</td>
                <td style="padding: 12px; text-align: center;"><a href="{link}" style="background-color: #fc8019; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; font-size: 13px; font-weight: bold;" target="_blank">View Item</a></td>
            </tr>
            """

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
            <div style="max-width: 650px; margin: 0 auto; background: white; border-radius: 8px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                <div style="background-color: #fc8019; color: white; padding: 16px; border-radius: 6px; text-align: center; margin-bottom: 20px;">
                    <h2 style="margin: 0;">🎉 Swiggy Instamart Price Drop Alert!</h2>
                    <p style="margin: 4px 0 0 0; font-size: 14px;">We found {len(rows)} significant price drop(s) on your watchlist.</p>
                </div>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #f2f2f2; text-align: left;">
                            <th style="padding: 10px;">Item</th>
                            <th style="padding: 10px;">Old</th>
                            <th style="padding: 10px;">New</th>
                            <th style="padding: 10px;">Savings</th>
                            <th style="padding: 10px; text-align: center;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {html_table_rows}
                    </tbody>
                </table>
                <p style="font-size: 12px; color: #999; margin-top: 24px; text-align: center;">Automated alert generated by Instamart Tracker • HSR Layout Bangalore</p>
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


def compare_prices(target_location=None):
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
    if target_location:
        query += " AND location LIKE ?"
        cursor.execute(query + " ORDER BY price_drop DESC;", (f"%{target_location}%",))
    else:
        cursor.execute(query + " ORDER BY price_drop DESC;")

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



def main():
    parser = argparse.ArgumentParser(description="Swiggy Instamart Live Price Scraper & Tracker")
    parser.add_argument("query", nargs="?", default=None, help="Product query to search (e.g. milk, paneer, eggs)")
    parser.add_argument("--location", "-l", default=DEFAULT_LOCATION, help="Delivery location (default: HSR Layout Bangalore)")
    parser.add_argument("--compare", "-c", action="store_true", help="Run instant database price comparison without opening browser")
    
    args = parser.parse_args()

    if args.compare:
        print(f"Running Instant Database Price Comparison (Location filter: '{args.location}')...\n")
        compare_prices(target_location=args.location)
        return

    location_input_str = args.location
    print(f"Target Delivery Location: '{location_input_str}'")

    if args.query:
        target_queries = [args.query]
        print(f"Scraping user-specified product query: {target_queries}\n")
    else:
        target_queries = TRACKED_KEYWORDS
        print(f"Watchlist product queries to scrape ({len(target_queries)}): {target_queries}\n")


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

        # 1. Access Landing Page & Set Location once
        print("Navigating to Swiggy Instamart...")
        driver.get("https://www.swiggy.com/instamart")
        time.sleep(2)
        
        print(f"Setting location: '{location_input_str}'...")
        search_container = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="search-location"]')))
        search_container.click()
        time.sleep(1)
        
        location_input = wait.until(EC.presence_of_element_located((By.CLASS_NAME, '_1wkJd')))
        driver.execute_script("arguments[0].value = '';", location_input)
        location_input.send_keys(location_input_str)
        
        first_suggestion = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div._2esgM')))
        first_suggestion.click()
        time.sleep(1)
        
        confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Confirm Location")]')))
        confirm_btn.click()
        time.sleep(7)

        # Loop over all target queries for this location
        for q_idx, search_query in enumerate(target_queries):
            print(f"\n[{q_idx + 1}/{len(target_queries)}] Processing search query: '{search_query}'...")
            
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
                    WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div._3Rr1X')))
                except Exception:
                    time.sleep(4)
                
                print(f"   Scrolling page to load full product catalog...")
                last_card_count = 0
                for scroll_step in range(6):
                    cards_in_dom = driver.find_elements(By.CSS_SELECTOR, 'div._3Rr1X')
                    current_count = len(cards_in_dom)
                    if current_count == 0:
                        time.sleep(3)
                        cards_in_dom = driver.find_elements(By.CSS_SELECTOR, 'div._3Rr1X')
                        current_count = len(cards_in_dom)
                    if current_count == 0 or current_count == last_card_count:
                        break
                    last_card_count = current_count
                    driver.execute_script("arguments[0].scrollIntoView(true);", cards_in_dom[-1])
                    time.sleep(2.5)


                soup = BeautifulSoup(driver.page_source, 'html.parser')
                cards = soup.find_all('div', class_='_3Rr1X')
                print(f"   Found {len(cards)} total product cards for '{search_query}'.")
                
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
                        (product_id, search_query, location, item_name, quantity, price, description, web_link, image_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (product_id, search_query, location_input_str, name, weight, numeric_price, desc, web_link, image_url))
                    total_inserted += 1

                conn.commit()
                print(f"   Successfully saved {len(cards)} listings for '{search_query}' (Location: '{location_input_str}').")
                time.sleep(2)

            except Exception as q_err:
                print(f"   ⚠️ Warning: Error processing query '{search_query}': {q_err}. Continuing to next query...")


        print(f"\nAll {len(target_queries)} queries completed for '{location_input_str}'. Total products stored/updated: {total_inserted}")
        conn.close()
        driver.quit()
        print("Browser session closed cleanly.")
        
        # Run price drop comparison for this location
        compare_prices(target_location=location_input_str)
        
    except Exception as e:
        print(f"\nScraping failed with error: {e}")

if __name__ == "__main__":
    main()
