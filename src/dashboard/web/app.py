from flask import Flask, send_file, request, jsonify
from flask_cors import CORS
from pathlib import Path
import mysql.connector
import requests as req
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

BASE = Path(__file__).parent


def get_conn():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="airbnb_douala"
    )


@app.route("/")
def index():
    return send_file(str(BASE / "index.html"))


@app.route("/api/listings")
def api_listings():
    quartier = request.args.get("quartier", "all")
    type_bien = request.args.get("type", "all")
    prix_max = request.args.get("prix_max", "999999")
    source = request.args.get("source", "all")

    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM listings WHERE 1=1"
        params = []

        if quartier != "all":
            query += " AND neighborhood = %s"
            params.append(quartier)
        if type_bien != "all":
            query += " AND type = %s"
            params.append(type_bien)
        if prix_max:
            query += " AND price_per_night <= %s"
            params.append(int(prix_max))
        if source != "all":
            query += " AND source = %s"
            params.append(source)

        query += " ORDER BY price_per_night DESC LIMIT 500"
        cursor.execute(query, params)
        listings = cursor.fetchall()

        for d in listings:
            for k, v in d.items():
                if hasattr(v, "isoformat"):
                    d[k] = str(v)
                elif v is None:
                    d[k] = None

        kpi_query = "SELECT COUNT(*) as total, AVG(price_per_night) as avg_price, AVG(rating) as avg_rating, AVG(occupancy_rate) as avg_occ FROM listings WHERE 1=1"
        kpi_params = []
        if quartier != "all":
            kpi_query += " AND neighborhood = %s"
            kpi_params.append(quartier)
        if source != "all":
            kpi_query += " AND source = %s"
            kpi_params.append(source)

        cursor.execute(kpi_query, kpi_params)
        kpis = cursor.fetchone()
        conn.close()

        return jsonify({"listings": listings, "total": len(listings), "kpis": kpis})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats")
def api_stats():
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM stats_quartiers ORDER BY prix_moyen DESC")
        stats_q = cursor.fetchall()
        cursor.execute("SELECT * FROM stats_types ORDER BY total DESC")
        stats_t = cursor.fetchall()
        conn.close()
        return jsonify({"stats_quartiers": stats_q, "stats_types": stats_t})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    data = request.json or {}
    quartier = data.get("quartier", "Douala")

    try:
        url = "https://www.airbnb.com/s/" + quartier.replace(" ", "-") + "--Cameroon/homes?flexible_trip_lengths%5B%5D=one_week&date_picker_type=flexible_dates"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        }

        r = req.get(url, headers=headers, timeout=15)
        text = r.text

        room_ids = list(set(re.findall(r"/rooms/(\d+)", text)))
        prices_eur = []
        for m in re.findall(r"(\d{2,4})\s*&euro;|(\d{2,4})\s*€", text):
            val = m[0] or m[1]
            try:
                v = float(val)
                if 5 < v < 2000:
                    prices_eur.append(round(v * 655.957))
            except:
                pass

        avg_price = round(sum(prices_eur) / len(prices_eur)) if prices_eur else None

        return jsonify({
            "success": True,
            "quartier": quartier,
            "annonces_trouvees": len(room_ids),
            "prix_moyen_xaf": avg_price,
            "status_http": r.status_code,
            "scrape_at": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("Serveur Airbnb Douala demarre...")
    print("Ouvrir: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)