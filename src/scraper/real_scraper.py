import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path.home() / "Desktop" / "airbnb-douala"))
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from config import DATA_RAW_DIR

DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_RAW_DIR / "listings_real_raw.json"

URL = "https://www.airbnb.com/s/Douala/homes?flexible_trip_lengths%5B%5D=one_week&date_picker_type=flexible_dates"

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

print("Starting Chrome...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

all_results = []
seen = set()
page_num = 0

def extract_cards():
    cards = driver.find_elements(By.CSS_SELECTOR, "[itemprop='itemListElement']")
    if not cards:
        cards = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='card-container']")
    return cards

def parse_card(text, index, page):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    parsed = {
        "index": index, "page": page,
        "property_type": None, "neighborhood": None,
        "title": None, "price_raw": None,
        "rating": None, "reviews": None,
        "raw_text": text[:300],
        "scraped_at": datetime.now().isoformat()
    }
    if lines:
        first = lines[0]
        for sep in ["\u00b7", "\u22c5", "-"]:
            if sep in first:
                parts = first.split(sep)
                parsed["property_type"] = parts[0].strip()
                if len(parts) > 1:
                    parsed["neighborhood"] = parts[1].strip()
                break
        else:
            parsed["property_type"] = first
    if len(lines) > 1:
        parsed["title"] = lines[1]
    for line in lines:
        if "\u20ac" in line or "XAF" in line or "FCFA" in line:
            parsed["price_raw"] = line
        m = re.match(r"^(\d[.,]\d{1,2})", line)
        if m and not parsed["rating"]:
            try:
                parsed["rating"] = float(m.group(1).replace(",", "."))
            except:
                pass
    return parsed

try:
    print("Opening: " + URL)
    driver.get(URL)
    time.sleep(30)

    while True:
        page_num += 1
        print("--- Page " + str(page_num) + " ---")

        # Scroll to load all cards
        for i in range(8):
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(1)

        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        cards = extract_cards()
        print("Cards found: " + str(len(cards)))

        new = 0
        for card in cards:
            try:
                text = card.text
                if not text.strip():
                    continue
                key = text[:80]
                if key in seen:
                    continue
                seen.add(key)
                all_results.append(parse_card(text, len(all_results), page_num))
                new += 1
            except:
                pass

        print("New: " + str(new) + " | Total: " + str(len(all_results)))

        # Click next button
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "a[aria-label='Suivant']")
            if not next_btn:
                next_btn = driver.find_element(By.CSS_SELECTOR, "a[aria-label='Next']")
            driver.execute_script("arguments[0].click();", next_btn)
            print("Clicked Next button")
            time.sleep(5)
        except:
            print("No Next button found - end of results")
            break

        if page_num >= 60:
            break

    OUTPUT_FILE.write_text(
        json.dumps({"results": all_results, "total": len(all_results)}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("")
    print("=================================")
    print("TOTAL UNIQUE LISTINGS: " + str(len(all_results)))
    print("Saved to: " + str(OUTPUT_FILE))

finally:
    time.sleep(5)
    driver.quit()
