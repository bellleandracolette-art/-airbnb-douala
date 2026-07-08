import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import mysql.connector

DATA_DIR = Path.home() / "Desktop" / "airbnb-douala" / "data" / "raw"
OUTPUT = DATA_DIR / "listings_details.json"

conn = mysql.connector.connect(host="localhost", user="root", password="root", database="airbnb_douala")
cursor = conn.cursor()

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

print("Starting Chrome...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

BASE_URL = "https://www.airbnb.com/s/Douala/homes?flexible_trip_lengths%5B%5D=one_week&date_picker_type=flexible_dates"


def extract_bool(text, keywords):
    return any(k in text.lower() for k in keywords)


def extract_parking(text):
    t = text.lower()
    if any(k in t for k in ["parking gratuit", "stationnement gratuit", "free parking"]):
        return "gratuit"
    elif any(k in t for k in ["parking", "stationnement"]):
        return "payant"
    return "non"


def extract_int(text, pattern):
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None


def extract_price_eur(text):
    for pat in [r"([\d\u202f ]+)\s*€\s*la nuit", r"([\d\u202f ]+)\s*€\s*/\s*nuit", r"([\d\u202f ]+)\s*€"]:
        m = re.search(pat, text)
        if m:
            try:
                val = float(m.group(1).replace("\u202f", "").replace(" ", ""))
                if 5 < val < 2000:
                    return val
            except:
                pass
    return None


def scrape_detail(url, listing_id):
    d = {
        "id": listing_id, "url": url, "titre": None,
        "quartier": None, "type_bien": None,
        "max_voyageurs": None, "nb_chambres": None,
        "nb_lits": None, "nb_salles_bain": None,
        "prix_nuit_eur": None, "prix_nuit_xaf": None,
        "note": None, "nb_avis": None,
        "superhost": False, "nom_hote": None,
        "wifi": False, "parking": "non",
        "piscine": False, "climatisation": False,
        "cuisine_equipee": False, "lave_linge": False,
        "tv": False, "generateur": False,
        "securite": False, "annulation_gratuite": False,
        "sejour_min_nuits": None,
        "date_collecte": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        driver.get(url)
        time.sleep(5)

        # Check if session is still alive
        _ = driver.title

        text = driver.find_element(By.TAG_NAME, "body").text

        d["max_voyageurs"] = extract_int(text, r"(\d+)\s*voyageur")
        d["nb_chambres"] = extract_int(text, r"(\d+)\s*chambre")
        d["nb_lits"] = extract_int(text, r"(\d+)\s*lit[^s\w]")
        d["nb_salles_bain"] = extract_int(text, r"(\d+)\s*salle\s*de\s*bain")
        d["sejour_min_nuits"] = extract_int(text, r"(\d+)\s*nuit.*minimum")

        prix = extract_price_eur(text)
        if prix:
            d["prix_nuit_eur"] = prix
            d["prix_nuit_xaf"] = round(prix * 655.957)

        m = re.search(r"(\d[.,]\d{1,2})\s*\((\d+)\s*(?:avis|comment)", text)
        if m:
            d["note"] = float(m.group(1).replace(",", "."))
            d["nb_avis"] = int(m.group(2))

        m = re.search(r"(?:H\u00f4te|Hosted by|Par)\s+([A-Z][a-zA-Z\u00e0-\u00ff]+(?:\s[A-Z][a-zA-Z]+)?)", text)
        if m:
            d["nom_hote"] = m.group(1)

        page = text.lower()
        d["superhost"] = "superhost" in page or "super h\u00f4te" in page
        d["wifi"] = extract_bool(text, ["wifi", "wi-fi", "internet"])
        d["parking"] = extract_parking(text)
        d["piscine"] = extract_bool(text, ["piscine", "pool"])
        d["climatisation"] = extract_bool(text, ["climatisation", "clim", "air conditionn"])
        d["cuisine_equipee"] = extract_bool(text, ["cuisine \u00e9quip", "kitchen", "kitchenette"])
        d["lave_linge"] = extract_bool(text, ["lave-linge", "machine \u00e0 laver", "washer"])
        d["tv"] = extract_bool(text, ["t\u00e9l\u00e9vision", "t\u00e9l\u00e9", "tv ", "hdtv"])
        d["generateur"] = extract_bool(text, ["g\u00e9n\u00e9rateur", "\u00e9lectrog\u00e8ne", "groupe \u00e9lectro"])
        d["securite"] = extract_bool(text, ["s\u00e9curit\u00e9", "gardien", "surveillance", "vigil"])
        d["annulation_gratuite"] = extract_bool(text, ["annulation gratuite", "free cancellation"])

        try:
            h1 = driver.find_element(By.TAG_NAME, "h1")
            d["titre"] = h1.text[:255]
        except:
            pass

        for t in ["Villa", "Appartement", "Studio", "Maison", "H\u00f4tel", "Chambre", "Bungalow", "Loft"]:
            if t.lower() in page:
                d["type_bien"] = t
                break

        for q in ["Bonanjo", "Bonapriso", "Akwa", "Bali", "Makepe", "Deido", "Logpom", "Kotto", "Ndokoti", "Bepanda", "Yassa", "Bonamoussadi"]:
            if q.lower() in page:
                d["quartier"] = q
                break

    except Exception as e:
        print("  Error: " + str(e)[:100])

    return d


all_details = []
urls_collected = []

# STEP 1 - collect all URLs
print("Step 1: Collecting listing URLs...")
driver.get(BASE_URL)
time.sleep(6)

page_num = 0
while True:
    page_num += 1

    for _ in range(8):
        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(0.8)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

    js_urls = driver.execute_script("""
        var links = document.querySelectorAll('a');
        var rooms = [];
        for(var i=0; i<links.length; i++){
            var h = links[i].href;
            if(h && h.includes('/rooms/') && !rooms.includes(h.split('?')[0])){
                rooms.push(h.split('?')[0]);
            }
        }
        return rooms;
    """)

    new_count = 0
    for url in js_urls:
        if url not in urls_collected:
            urls_collected.append(url)
            new_count += 1

    print("  Page " + str(page_num) + " - new: " + str(new_count) + " | total: " + str(len(urls_collected)))

    try:
        nb = driver.find_element(By.CSS_SELECTOR, "a[aria-label='Suivant']")
        driver.execute_script("arguments[0].click();", nb)
        time.sleep(5)
    except:
        print("  No more pages - stopping")
        break

    if page_num >= 20:
        break

print("Total URLs: " + str(len(urls_collected)))
print("")

# Save URLs to file as checkpoint
urls_file = DATA_DIR / "urls_collected.json"
urls_file.write_text(json.dumps({"urls": urls_collected}, ensure_ascii=False, indent=2), encoding="utf-8")
print("URLs saved to: " + str(urls_file))
print("")

# STEP 2 - scrape each listing (Chrome stays open)
print("Step 2: Visiting each listing page...")
cursor.execute("DELETE FROM listings_details")
conn.commit()

try:
    for i, url in enumerate(urls_collected):
        listing_id = "REAL-" + str(i + 1).zfill(3)
        print("  [" + str(i + 1) + "/" + str(len(urls_collected)) + "] " + url[-50:])

        d = scrape_detail(url, listing_id)
        all_details.append(d)

        try:
            cursor.execute(
                "INSERT INTO listings_details "
                "(id, url, titre, quartier, type_bien, max_voyageurs, nb_chambres, "
                "nb_lits, nb_salles_bain, prix_nuit_eur, prix_nuit_xaf, note, "
                "nb_avis, superhost, nom_hote, wifi, parking, piscine, "
                "climatisation, cuisine_equipee, lave_linge, tv, generateur, "
                "securite, annulation_gratuite, sejour_min_nuits, date_collecte) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (d["id"], d["url"], d["titre"], d["quartier"], d["type_bien"],
                 d["max_voyageurs"], d["nb_chambres"], d["nb_lits"], d["nb_salles_bain"],
                 d["prix_nuit_eur"], d["prix_nuit_xaf"], d["note"], d["nb_avis"],
                 d["superhost"], d["nom_hote"], d["wifi"], d["parking"], d["piscine"],
                 d["climatisation"], d["cuisine_equipee"], d["lave_linge"],
                 d["tv"], d["generateur"], d["securite"],
                 d["annulation_gratuite"], d["sejour_min_nuits"], d["date_collecte"])
            )
            conn.commit()
        except Exception as e:
            print("  DB error: " + str(e)[:80])

        if (i + 1) % 10 == 0:
            # Save checkpoint JSON
            OUTPUT.write_text(
                json.dumps({"details": all_details, "total": len(all_details)}, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print("  --- Checkpoint " + str(i + 1) + " saved ---")

        time.sleep(3)

finally:
    # Always save final results
    OUTPUT.write_text(
        json.dumps({"details": all_details, "total": len(all_details)}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    conn.close()
    print("")
    print("=================================")
    print("TOTAL SCRAPED: " + str(len(all_details)))
    print("MySQL: listings_details table updated")
    print("JSON: " + str(OUTPUT))
    print("Closing browser in 5 seconds...")
    time.sleep(5)
    driver.quit()
