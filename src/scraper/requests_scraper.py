import json
import time
import re
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
import mysql.connector

DATA_DIR = Path.home() / "Desktop" / "airbnb-douala" / "data" / "raw"
OUTPUT = DATA_DIR / "listings_details.json"
URLS_FILE = DATA_DIR / "urls_collected.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

conn = mysql.connector.connect(host="localhost", user="root", password="root", database="airbnb_douala")
cursor = conn.cursor()


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
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        text = soup.get_text(" ", strip=True)

        # Titre
        h1 = soup.find("h1")
        if h1:
            d["titre"] = h1.get_text(strip=True)[:255]

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

        for t in ["Villa", "Appartement", "Studio", "Maison", "H\u00f4tel", "Chambre", "Bungalow", "Loft"]:
            if t.lower() in page:
                d["type_bien"] = t
                break

        for q in ["Bonanjo", "Bonapriso", "Akwa", "Bali", "Makepe", "Deido", "Logpom", "Kotto", "Ndokoti", "Bepanda", "Yassa", "Bonamoussadi"]:
            if q.lower() in page:
                d["quartier"] = q
                break

    except Exception as e:
        print("  Error: " + str(e)[:80])

    return d


# Load URLs from previous scrape
print("Loading URLs from previous scrape...")
if URLS_FILE.exists():
    urls = json.loads(URLS_FILE.read_text(encoding="utf-8"))["urls"]
    print("URLs loaded from file: " + str(len(urls)))
else:
    # Use hardcoded URLs from listings_real_raw.json
    raw = json.loads((DATA_DIR / "listings_real_raw.json").read_text(encoding="utf-8"))
    urls = []
    for r in raw["results"]:
        rt = r.get("raw_text", "")
        m = re.search(r"airbnb\.[a-z]+/rooms/(\d+)", rt)
        if m:
            urls.append("https://www.airbnb.fr/rooms/" + m.group(1))
    print("URLs extracted from raw data: " + str(len(urls)))

# If still no URLs, use the ones we know worked
if not urls:
    print("Using known URLs from previous successful scrape...")
    urls = [
        "https://www.airbnb.fr/rooms/1634845470640158977",
        "https://www.airbnb.fr/rooms/1698428704779855510",
        "https://www.airbnb.fr/rooms/1678499901267917484",
        "https://www.airbnb.fr/rooms/978600704606406460",
        "https://www.airbnb.fr/rooms/1654435777578850685",
    ]

print("Total URLs to scrape: " + str(len(urls)))
print("")

# Scrape each listing
all_details = []
cursor.execute("DELETE FROM listings_details")
conn.commit()

for i, url in enumerate(urls):
    listing_id = "REAL-" + str(i + 1).zfill(3)
    print("[" + str(i + 1) + "/" + str(len(urls)) + "] " + url[-50:])

    d = scrape_detail(url, listing_id)
    all_details.append(d)

    if d["titre"]:
        print("  titre: " + str(d["titre"])[:50])
    print("  chambres: " + str(d["nb_chambres"]) + " | wifi: " + str(d["wifi"]) + " | parking: " + d["parking"])

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
        OUTPUT.write_text(
            json.dumps({"details": all_details, "total": len(all_details)}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print("--- Checkpoint " + str(i + 1) + " saved ---")

    time.sleep(2)

OUTPUT.write_text(
    json.dumps({"details": all_details, "total": len(all_details)}, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
conn.close()

print("")
print("=================================")
print("TOTAL SCRAPED: " + str(len(all_details)))
print("MySQL table listings_details: updated")
print("JSON: " + str(OUTPUT))
