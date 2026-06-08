
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from config import PROCESSED_LISTINGS_FILE, STATS_FILE, DASHBOARD_PORT

app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "Airbnb Douala Intelligence"

def load_data():
    if not PROCESSED_LISTINGS_FILE.exists():
        return pd.DataFrame(), pd.DataFrame()
    df    = pd.read_csv(PROCESSED_LISTINGS_FILE)
    stats = pd.read_csv(STATS_FILE) if STATS_FILE.exists() else pd.DataFrame()
    return df, stats

df, stats = load_data()

app.layout = dbc.Container([
    html.H1("Airbnb Douala Intelligence", className="my-4 text-center"),
    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardBody([
            html.H5("Annonces actives"),
            html.H2(f"{len(df):,}")
        ])]), width=3),
        dbc.Col(dbc.Card([dbc.CardBody([
            html.H5("Prix moyen / nuit"),
            html.H2(f"{int(df['price_per_night'].mean()):,} XAF" if not df.empty else "-")
        ])]), width=3),
        dbc.Col(dbc.Card([dbc.CardBody([
            html.H5("Taux occupation moyen"),
            html.H2(f"{df['occupancy_rate'].mean()*100:.1f}%" if not df.empty else "-")
        ])]), width=3),
        dbc.Col(dbc.Card([dbc.CardBody([
            html.H5("Note moyenne"),
            html.H2(f"{df['rating'].mean():.2f}" if not df.empty else "-")
        ])]), width=3),
    ], className="mb-4"),
    dbc.Row([
        dbc.Col([
            dcc.Graph(
                figure=px.bar(
                    stats.sort_values("avg_revenue", ascending=False),
                    x="neighborhood", y="avg_revenue",
                    title="Revenu mensuel moyen par quartier (XAF)",
                    color="avg_occupancy",
                    color_continuous_scale="teal",
                    template="plotly_dark",
                ) if not stats.empty else {}
            )
        ], width=8),
        dbc.Col([
            dcc.Graph(
                figure=px.pie(
                    df, names="type",
                    title="Repartition par type de bien",
                    template="plotly_dark",
                ) if not df.empty else {}
            )
        ], width=4),
    ]),
    dbc.Row([
        dbc.Col([
            dcc.Graph(
                figure=px.box(
                    df, x="neighborhood", y="price_per_night",
                    title="Distribution des prix par quartier (XAF)",
                    template="plotly_dark",
                    color="neighborhood",
                ) if not df.empty else {}
            )
        ])
    ]),
], fluid=True)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=DASHBOARD_PORT)
