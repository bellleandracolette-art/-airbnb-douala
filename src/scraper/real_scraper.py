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
from webdriver_manager.chrome import ChromeDriverManager

from config import DATA_RAW_DIR

DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_RAW_DIR / "listings_real_raw.json"

BASE_URL = "https://www.airbnb.com/s/Douala/homes"
MAX_PAGES = 15

print("Real Airbnb Scraper v2 - Douala (multi-page)")
print("")

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

print("Starting Chrome browser...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

all_results = []
seen_titles = set()

def parse_card(card_text, index, page_num):
    lines = [l.strip() for l in card_text.split("\n") if l.strip()]
    parsed = {
        "index": index,
        "page": page_num,
        "property_type": None,
        "neighborhood": None,
        "title": None,
        "price_raw": None,
        "rating": None,
        "reviews": None,
        "raw_text": card_text[:400],
        "scraped_at": datetime.now().isoformat()
    }
    if lines:
        first = lines[0]
        if "\u00b7" in first or "\u22c5" in first:
            sep = "\u00b7" if "\u00b7" in first else "\u22c5"
            parts = first.split(sep)
            parsed["property_type"] = parts[0].strip()
            if len(parts) > 1:
                parsed["neighborhood"] = parts[1].strip()
        else:
            parsed["property_type"] = first
    if len(lines) > 1:
        parsed["title"] = lines[1]
    for line in lines:
        if "\u20ac" in line or "FCFA" in line or "XAF" in line:
            parsed["price_raw"] = line
        m = re.match(r"^(\d[.,]\d{1,2})", line)
        if m and parsed["rating"] is None:
            try:
                parsed["rating"] = float(m.group(1).replace(",", "."))
            except:
                pass
        m2 = re.search(r"\((\d+)", line)
        if m2 and parsed["reviews"] is None:
            try:
                parsed["reviews"] = int(m2.group(1))
            except:
                pass
    return parsed

try:
    for page_num in range(MAX_PAGES):
        offset = page_num * 18
        url = BASE_URL if offset == 0 else BASE_URL + "?items_offset=" + str(offset)

        print("--- Page " + str(page_num + 1) + " ---")
        driver.get(url)
        time.sleep(4)

        for scroll in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

        cards = driver.find_elements(By.CSS_SELECTOR, "[itemprop='itemListElement']")
        if len(cards) == 0:
            cards = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='card-container']")

        print("Cards found: " + str(len(cards)))

        new_count = 0
        for i, card in enumerate(cards):
            try:
                text = card.text
                if not text.strip():
                    continue
                key = text[:80]
                if key in seen_titles:
                    continue
                seen_titles.add(key)
                parsed = parse_card(text, len(all_results), page_num + 1)
                all_results.append(parsed)
                new_count += 1
            except Exception as e:
                print("Error card " + str(i) + ": " + str(e))

        print("New unique listings: " + str(new_count))
        print("Total so far: " + str(len(all_results)))

        if new_count == 0 and page_num > 0:
            print("No new listings - stopping")
            break

        time.sleep(2)

    OUTPUT_FILE.write_text(
        json.dumps({"results": all_results, "total": len(all_results)}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("")
    print("=================================")
    print("TOTAL UNIQUE LISTINGS: " + str(len(all_results)))
    print("Saved to: " + str(OUTPUT_FILE))
    if all_results:
        print("")
        print("--- SAMPLE PARSED LISTING ---")
        for k, v in all_results[0].items():
            if k != "raw_text":
                print("  " + str(k) + ": " + str(v))

finally:
    time.sleep(5)
    driver.quit()
