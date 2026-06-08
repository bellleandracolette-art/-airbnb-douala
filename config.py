
CITY        = "Douala"
COUNTRY     = "Cameroun"
CURRENCY    = "XAF"

NEIGHBORHOODS = [
    "Bonanjo", "Bonapriso", "Akwa", "Bali",
    "Makepe", "Deido", "New Bell", "Logbessou",
]

PROPERTY_TYPES = [
    "Appartement entier", "Chambre privee", "Studio", "Villa",
]

PRICE_RANGES = {
    "Bonanjo":    (35000, 65000),
    "Bonapriso":  (28000, 55000),
    "Bali":       (25000, 50000),
    "Akwa":       (18000, 40000),
    "Logbessou":  (15000, 35000),
    "Makepe":     (12000, 28000),
    "Deido":      (10000, 22000),
    "New Bell":   ( 8000, 18000),
}

from pathlib import Path
BASE_DIR            = Path(__file__).parent
DATA_RAW_DIR        = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR  = BASE_DIR / "data" / "processed"

RAW_LISTINGS_FILE        = DATA_RAW_DIR / "listings_raw.json"
PROCESSED_LISTINGS_FILE  = DATA_PROCESSED_DIR / "listings_clean.csv"
STATS_FILE               = DATA_PROCESSED_DIR / "neighborhood_stats.csv"

SCRAPER_DELAY_SEC   = 1.5
MAX_LISTINGS        = 1247
REQUEST_TIMEOUT     = 15

API_HOST  = "0.0.0.0"
API_PORT  = 8000
API_DEBUG = True

DASHBOARD_HOST  = "0.0.0.0"
DASHBOARD_PORT  = 8050
