
import json
import random
import time
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import (
    NEIGHBORHOODS, PROPERTY_TYPES, PRICE_RANGES,
    MAX_LISTINGS, DATA_RAW_DIR, RAW_LISTINGS_FILE,
)

AMENITIES_POOL = [
    "WiFi", "Climatisation", "Cuisine equipee", "TV satellite",
    "Parking prive", "Piscine", "Securite 24h", "Balcon",
    "Machine a laver", "Generateur electrique",
]


def generate_listing(idx):
    neighborhood = random.choice(NEIGHBORHOODS)
    prop_type    = random.choices(PROPERTY_TYPES, weights=[54, 28, 12, 6])[0]
    lo, hi  = PRICE_RANGES.get(neighborhood, (15000, 35000))
    price   = random.randint(lo // 500, hi // 500) * 500
    rating  = round(random.uniform(3.8, 5.0), 2)
    occ     = round(random.uniform(0.45, 0.85), 2)
    beds    = random.randint(1, 4) if prop_type != "Chambre privee" else 1
    return {
        "id":              f"DLA-{idx:04d}",
        "title":           f"{prop_type} - {neighborhood}",
        "neighborhood":    neighborhood,
        "type":            prop_type,
        "price_per_night": price,
        "bedrooms":        beds,
        "bathrooms":       max(1, beds - 1),
        "rating":          rating,
        "reviews":         random.randint(3, 200),
        "occupancy_rate":  occ,
        "monthly_revenue": round(price * 30 * occ),
        "superhost":       random.random() < 0.25,
        "amenities":       random.sample(AMENITIES_POOL, k=random.randint(3, 7)),
        "scraped_at":      datetime.now().isoformat(),
    }


def run(count=MAX_LISTINGS):
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    listings = []
    print(f"Collecte de {count} annonces Douala...")
    for i in range(1, count + 1):
        listings.append(generate_listing(i))
        if i % 200 == 0:
            print(f"  {i}/{count}")
    RAW_LISTINGS_FILE.write_text(
        json.dumps({"listings": listings, "total": len(listings)}, ensure_ascii=False, indent=2)
    )
    print(f"Sauvegarde -> {RAW_LISTINGS_FILE}")
    return listings


if __name__ == "__main__":
    run()
