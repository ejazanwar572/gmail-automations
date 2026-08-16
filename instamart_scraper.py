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
import sys
import os
import argparse

# Dynamically resolve instamart_prices.db in the same directory as this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instamart_prices.db")

DEFAULT_LOCATION = "HSR Layout Bangalore"

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
            LAG(scraped_at) OVER (PARTITION BY product_id, location ORDER BY scraped_at ASC) as previous_time
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
    WHERE previous_price IS NOT NULL AND (previous_price - price) > 0
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
    
    for r in rows:
        prod_id, loc, name, qty, old_p, new_p, diff, pct, old_t, new_t, link = r
        print(f"🎉 PRICE DROP! [{loc}] [{qty}] {name}")
        print(f"   Old Price: ₹{old_p} ({old_t})")
        print(f"   New Price: ₹{new_p} ({new_t})")
        print(f"   SAVINGS:   ₹{diff:.2f} ({pct}% price drop!)")
        print(f"   Web Link:  {link}\n")
            
    print(f"Total Price Drops Found: {len(rows)}")
    print("==================================================\n")
    conn.close()

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
        target_queries = get_tracked_search_queries()
        print(f"Auto-discovered tracked product queries from database: {target_queries}\n")

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
                search_btns = driver.find_elements(By.XPATH, '//button[contains(., "Search for")]')
                if search_btns:
                    driver.execute_script("arguments[0].click();", search_btns[0])
                    time.sleep(2)
            except Exception:
                pass
            
            product_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="search"]')))
            driver.execute_script("arguments[0].value = '';", product_input)
            product_input.send_keys(search_query)
            time.sleep(1)
            product_input.send_keys("\n")
            
            print(f"   Waiting for initial listings for '{search_query}' to render...")
            time.sleep(5)
            
            print(f"   Scrolling page to load full product catalog...")
            last_card_count = 0
            for scroll_step in range(6):
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
