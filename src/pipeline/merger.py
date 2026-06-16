import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path.home() / "Desktop" / "airbnb-douala"))
from config import DATA_RAW_DIR, DATA_PROCESSED_DIR, PROCESSED_LISTINGS_FILE, STATS_FILE

REAL_FILE = DATA_RAW_DIR / "listings_real_raw.json"
SIMULATED_FILE = DATA_RAW_DIR / "listings_raw.json"
OUTPUT_MERGED = DATA_PROCESSED_DIR / "listings_merged.csv"

print("Merging real + simulated listings...")
print("")

real_data = json.loads(REAL_FILE.read_text(encoding="utf-8"))
real_listings = real_data["results"]
print("Real listings loaded: " + str(len(real_listings)))

sim_data = json.loads(SIMULATED_FILE.read_text(encoding="utf-8"))
sim_listings = sim_data["listings"]
print("Simulated listings loaded: " + str(len(sim_listings)))

real_rows = []
for l in real_listings:
    title = l.get("title") or ""
    neighborhood = l.get("neighborhood") or "Douala"
    if "Logpom" in title: neighborhood = "Logpom"
    elif "Kotto" in title: neighborhood = "Kotto"
    elif "Bonanjo" in title: neighborhood = "Bonanjo"
    elif "Akwa" in title: neighborhood = "Akwa"
    elif "Bonapriso" in title: neighborhood = "Bonapriso"
    elif "Bali" in title: neighborhood = "Bali"
    elif "Makepe" in title: neighborhood = "Makepe"
    elif "Deido" in title: neighborhood = "Deido"

    price_raw = l.get("price_raw") or ""
    price_eur = None
    import re
    m = re.search(r"([\d\s]+)\s*€", price_raw)
    if m:
        try:
            price_eur = float(m.group(1).replace(" ", "").replace(" ", ""))
        except:
            pass
    price_xaf = round(price_eur * 655.957) if price_eur else None

    real_rows.append({
        "id": "REAL-" + str(l["index"] + 1).zfill(3),
        "title": title,
        "neighborhood": neighborhood,
        "type": l.get("property_type") or "Appartement entier",
        "price_per_night": round(price_xaf / 5) if price_xaf else None,
        "price_total_xaf": price_xaf,
        "rating": l.get("rating"),
        "reviews": l.get("reviews"),
        "occupancy_rate": None,
        "monthly_revenue": None,
        "superhost": False,
        "source": "real",
        "scraped_at": l.get("scraped_at")
    })

df_real = pd.DataFrame(real_rows)
df_real["price_per_night"] = pd.to_numeric(df_real["price_per_night"], errors="coerce")
df_real["price_per_night"].fillna(df_real["price_per_night"].median(), inplace=True)

sim_rows = []
for l in sim_listings:
    sim_rows.append({
        "id": l["id"],
        "title": l["title"],
        "neighborhood": l["neighborhood"],
        "type": l["type"],
        "price_per_night": l["price_per_night"],
        "price_total_xaf": None,
        "rating": l["rating"],
        "reviews": l["reviews"],
        "occupancy_rate": l["occupancy_rate"],
        "monthly_revenue": l["monthly_revenue"],
        "superhost": l["superhost"],
        "source": "simulated",
        "scraped_at": l["scraped_at"]
    })

df_sim = pd.DataFrame(sim_rows)

df_merged = pd.concat([df_real, df_sim], ignore_index=True)
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
df_merged.to_csv(OUTPUT_MERGED, index=False, encoding="utf-8")

print("")
print("=================================")
print("MERGED DATASET")
print("Real listings:      " + str(len(df_real)))
print("Simulated listings: " + str(len(df_sim)))
print("TOTAL:              " + str(len(df_merged)))
print("Saved to: " + str(OUTPUT_MERGED))
print("")
print("Real listings preview:")
print(df_real[["id","title","neighborhood","price_per_night","source"]].head(5).to_string(index=False))
