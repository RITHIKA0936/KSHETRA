# =============================================================
# config.py — Application Configuration & API Keys for KSHETRA
# =============================================================

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # -------------------------
    # Flask Core
    # -------------------------
    SECRET_KEY = "kshetra-secret-key-2024"          # Change in production!
    DEBUG      = True

    # -------------------------
    # SQLite Database
    # -------------------------
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "kshetra.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # -------------------------
    # External API Keys (DUMMY — replace with real keys)
    # -------------------------

    # Open-Meteo: Free weather API — no key needed
    # Docs: https://open-meteo.com/en/docs
    OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

    # AgroMonitoring: NDVI / Soil / Satellite crop health
    # Docs: https://agromonitoring.com/api/polygons
    AGROMONITORING_API_KEY = "DUMMY_AGRO_KEY_12345"
    AGROMONITORING_BASE_URL = "https://api.agromonitoring.com/agro/1.0"

    # Agmarknet (Government Mandi Prices)
    # Docs: https://data.gov.in/resource/current-daily-price-various-commodities
    AGMARKNET_API_KEY = "DUMMY_AGMARKNET_KEY_67890"
    AGMARKNET_BASE_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

    # Fast2SMS: SMS / WhatsApp notifications
    # Docs: https://www.fast2sms.com/docs/
    FAST2SMS_API_KEY = "DUMMY_FAST2SMS_KEY_ABCDE"
    FAST2SMS_BASE_URL = "https://www.fast2sms.com/dev/bulkV2"

    # Google Maps / OSRM (routing & distance)
    # Using OSRM public demo server (no key required for demo)
    OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving"

    # -------------------------
    # Transport Cost Rates (₹ per km per ton)
    # -------------------------
    TRANSPORT_RATES = {
        "Bullock Cart": 8,
        "Tractor":      12,
        "Truck":        18,
        "Mini Truck":   14
    }

    # -------------------------
    # City Coordinates for Weather API
    # -------------------------
    CITY_COORDS = {
        "Bengaluru":      {"lat": 12.9716, "lon": 77.5946},
        "Kolar":          {"lat": 13.1368, "lon": 78.1294},
        "Mysuru":         {"lat": 12.2958, "lon": 76.6394},
        "Tumakuru":       {"lat": 13.3379, "lon": 77.1173},
        "Mandya":         {"lat": 12.5218, "lon": 76.8951},
        "Hassan":         {"lat": 13.0033, "lon": 76.1004},
        "Chikkaballapur": {"lat": 13.4355, "lon": 77.7290},
        "Ramanagara":     {"lat": 12.7164, "lon": 77.2793},
    }

    # -------------------------
    # Distance Matrix (km) — loaded from CSV in flask_app.py
    # These are fallback defaults
    # -------------------------
    DISTANCE_DEFAULTS = {
        ("Kolar",    "Bengaluru"):  70,
        ("Kolar",    "Mysuru"):    170,
        ("Kolar",    "Tumakuru"): 130,
        ("Kolar",    "Mandya"):   150,
        ("Bengaluru","Mysuru"):   145,
        ("Bengaluru","Tumakuru"):  70,
        ("Bengaluru","Hassan"):   200,
        ("Tumakuru", "Hassan"):   120,
        ("Mandya",   "Mysuru"):    45,
        ("Mandya",   "Hassan"):   120,
        ("Hassan",   "Mysuru"):   120,
        ("Kolar",    "Chikkaballapur"): 40,
    }
