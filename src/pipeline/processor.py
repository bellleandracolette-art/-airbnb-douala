
import json
import pandas as pd
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import RAW_LISTINGS_FILE, PROCESSED_LISTINGS_FILE, STATS_FILE


def load_raw():
    data = json.loads(RAW_LISTINGS_FILE.read_text(encoding="utf-8"))
    return pd.DataFrame(data["listings"])


def clean(df):
    df = df.copy()
    df["price_per_night"]  = pd.to_numeric(df["price_per_night"], errors="coerce")
    df["occupancy_rate"]   = pd.to_numeric(df["occupancy_rate"],  errors="coerce")
    df["rating"]           = pd.to_numeric(df["rating"],          errors="coerce")
    df["monthly_revenue"]  = df["price_per_night"] * 30 * df["occupancy_rate"]
    df.dropna(subset=["price_per_night", "occupancy_rate"], inplace=True)
    return df


def neighborhood_stats(df):
    stats = df.groupby("neighborhood").agg(
        listing_count   = ("id",              "count"),
        avg_price       = ("price_per_night", "mean"),
        median_price    = ("price_per_night", "median"),
        avg_occupancy   = ("occupancy_rate",  "mean"),
        avg_rating      = ("rating",          "mean"),
        avg_revenue     = ("monthly_revenue", "mean"),
        superhost_count = ("superhost",       "sum"),
    ).reset_index()
    stats["superhost_pct"] = (stats["superhost_count"] / stats["listing_count"] * 100).round(1)
    return stats.sort_values("avg_revenue", ascending=False)


def run():
    PROCESSED_LISTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    df    = clean(load_raw())
    stats = neighborhood_stats(df)
    df.to_csv(PROCESSED_LISTINGS_FILE, index=False, encoding="utf-8")
    stats.to_csv(STATS_FILE,           index=False, encoding="utf-8")
    print(f"Listings -> {PROCESSED_LISTINGS_FILE} ({len(df)} lignes)")
    print(f"Stats    -> {STATS_FILE}")
    print(stats[["neighborhood","avg_price","avg_occupancy","avg_revenue"]].to_string(index=False))
    return df, stats


if __name__ == "__main__":
    run()
