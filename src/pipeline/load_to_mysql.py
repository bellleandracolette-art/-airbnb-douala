import sys
import pandas as pd
import mysql.connector
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'Desktop' / 'airbnb-douala'))
from config import DATA_PROCESSED_DIR

MERGED_FILE = DATA_PROCESSED_DIR / 'listings_merged.csv'

print('Connecting to MySQL...')
conn = mysql.connector.connect(host='localhost', user='root', password='root', database='airbnb_douala')
cursor = conn.cursor()
print('Connected.')

print('Loading CSV...')
df = pd.read_csv(MERGED_FILE)
df['price_per_night'] = pd.to_numeric(df['price_per_night'], errors='coerce').fillna(0).astype(int)
df['price_total_xaf'] = pd.to_numeric(df['price_total_xaf'], errors='coerce').fillna(0).astype(int)
df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
df['reviews'] = pd.to_numeric(df['reviews'], errors='coerce').fillna(0).astype(int)
df['occupancy_rate'] = pd.to_numeric(df['occupancy_rate'], errors='coerce')
df['monthly_revenue'] = pd.to_numeric(df['monthly_revenue'], errors='coerce').fillna(0).astype(int)
df['superhost'] = df['superhost'].fillna(False).astype(bool)
df['scraped_at'] = pd.to_datetime(df['scraped_at'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
df['title'] = df['title'].fillna('').astype(str)
df['neighborhood'] = df['neighborhood'].fillna('').astype(str)
df['type'] = df['type'].fillna('').astype(str)
df['source'] = df['source'].fillna('').astype(str)

print('Inserting ' + str(len(df)) + ' rows into MySQL...')
cursor.execute('DELETE FROM listings')
conn.commit()

q = ('INSERT INTO listings (id, title, neighborhood, type, price_per_night, price_total_xaf, rating, reviews, occupancy_rate, monthly_revenue, superhost, source, scraped_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)')

inserted = 0
errors = 0
for _, row in df.iterrows():
    try:
        cursor.execute(q, (str(row['id']), str(row['title'])[:255], str(row['neighborhood'])[:100], str(row['type'])[:100], int(row['price_per_night']), int(row['price_total_xaf']), float(row['rating']) if pd.notna(row['rating']) else None, int(row['reviews']), float(row['occupancy_rate']) if pd.notna(row['occupancy_rate']) else None, int(row['monthly_revenue']), bool(row['superhost']), str(row['source']), str(row['scraped_at']) if str(row['scraped_at']) != 'nan' else None))
        inserted += 1
    except Exception as e:
        errors += 1

conn.commit()
cursor.close()
conn.close()

print('')
print('=================================')
print('ROWS INSERTED: ' + str(inserted))
print('ERRORS: ' + str(errors))
print('MySQL database airbnb_douala is ready for Power BI')
print('=================================')