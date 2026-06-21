# =============================================================
# flask_app.py — Main Flask Application for KSHETRA
# =============================================================
# Smart Agricultural Decision Support System
#
# Run with:
#   pip install flask flask_sqlalchemy requests
#   python flask_app.py
#
# First time: python seed_db.py  (loads demo data)
# =============================================================

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from models import db, Farmer, Crop, MandiAgent, PriceEntry, Disruption, PreBooking, CropDeal
from config  import Config
from datetime import datetime, date, timedelta
import requests
import csv
import os

# ------------------------------------------------------------------
# App Factory
# ------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)

# Initialise SQLAlchemy with the app
db.init_app(app)

# ------------------------------------------------------------------
# Load distance matrix from CSV into memory on startup
# ------------------------------------------------------------------
DISTANCE_MATRIX = {}

def load_distance_matrix():
    """
    Reads data/distance_matrix.csv and builds a bidirectional lookup dict.
    Key: (city_a, city_b)  Value: distance_km (int)
    """
    global DISTANCE_MATRIX
    csv_path = os.path.join(app.root_path, "data", "distance_matrix.csv")
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["From"].strip() and row["To"].strip() and row["Distance_KM"].strip():
                    a = row["From"].strip()
                    b = row["To"].strip()
                    d = int(row["Distance_KM"].strip())
                    DISTANCE_MATRIX[(a, b)] = d
                    DISTANCE_MATRIX[(b, a)] = d   # bidirectional
    except FileNotFoundError:
        # Fallback to config defaults
        DISTANCE_MATRIX = {k: v for k, v in Config.DISTANCE_DEFAULTS.items()}

load_distance_matrix()



def get_distance(city_a, city_b):
    """Return distance in km between two cities. Returns 999 if unknown."""
    if city_a == city_b:
        return 0
    return DISTANCE_MATRIX.get((city_a, city_b),
           DISTANCE_MATRIX.get((city_b, city_a), 999))


# =============================================================
# ===  EXTERNAL API HELPER FUNCTIONS  ========================
# =============================================================

def get_weather_forecast(city):
    """
    Fetch 3-day weather forecast for a city using Open-Meteo (FREE, no key).
    Returns dict with rain_probability (0-100) and max_temp.
    Falls back to dummy data if API is unreachable.

    Open-Meteo docs: https://open-meteo.com/en/docs
    """
    coords = Config.CITY_COORDS.get(city)
    if not coords:
        return {"rain_probability": 0, "max_temp": 28, "description": "Unknown city"}

    try:
        params = {
            "latitude":  coords["lat"],
            "longitude": coords["lon"],
            "daily":     "precipitation_sum,temperature_2m_max",
            "timezone":  "Asia/Kolkata",
            "forecast_days": 3
        }
        resp = requests.get(Config.OPEN_METEO_BASE_URL, params=params, timeout=2)
        data = resp.json()

        # Parse precipitation and temperature from the response
        precip  = data["daily"]["precipitation_sum"]          # list of 3 values (mm)
        temps   = data["daily"]["temperature_2m_max"]         # list of 3 values (°C)
        max_rain = max(precip) if precip else 0
        max_temp = max(temps)  if temps  else 30

        # Convert mm to rough probability (0–100)
        rain_prob = min(int(max_rain * 10), 100)
        return {
            "rain_probability": rain_prob,
            "max_temp":         max_temp,
            "description":      f"Max rain {max_rain}mm, Max temp {max_temp}°C"
        }
    except Exception:
        # Fallback dummy values when offline / API error
        return {"rain_probability": 10, "max_temp": 30, "description": "Forecast unavailable (using defaults)"}


def get_agro_ndvi(district):
    """
    Fetch NDVI satellite crop health index for a district via AgroMonitoring API.
    NDVI range: -1 to 1 (>0.5 = healthy, <0.2 = stressed)
    Uses DUMMY key — replace AGROMONITORING_API_KEY in config.py with a real key.

    AgroMonitoring docs: https://agromonitoring.com/api/get-satellite-images
    """
    # Dummy polygon IDs per district (in production, store real polygon IDs)
    district_polygon_map = {
        "Kolar":          "poly_kolar_001",
        "Bengaluru":      "poly_blr_001",
        "Mysuru":         "poly_mys_001",
        "Tumakuru":       "poly_tum_001",
        "Mandya":         "poly_mdy_001",
        "Hassan":         "poly_hsn_001",
    }
    poly_id = district_polygon_map.get(district, "poly_default_001")

    try:
        url    = f"{Config.AGROMONITORING_BASE_URL}/ndvi/history"
        params = {
            "polyid":  poly_id,
            "appid":   Config.AGROMONITORING_API_KEY,
            "start":   int((datetime.utcnow() - timedelta(days=10)).timestamp()),
            "end":     int(datetime.utcnow().timestamp())
        }
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()

        # Parse latest NDVI value from response
        if isinstance(data, list) and len(data) > 0:
            latest = data[-1]
            ndvi   = latest.get("data", {}).get("mean", 0.45)
        else:
            ndvi   = 0.45   # fallback

        # Health classification
        if ndvi > 0.6:
            health = "Excellent 🌿"
        elif ndvi > 0.4:
            health = "Good ✅"
        elif ndvi > 0.2:
            health = "Moderate ⚠️"
        else:
            health = "Stressed 🔴"

        return {"ndvi": round(ndvi, 3), "health": health}

    except Exception:
        # Return demo values when offline / DUMMY key
        return {"ndvi": 0.52, "health": "Good ✅ (demo)"}


def get_agmarknet_price(crop_name, state="Karnataka"):
    """
    Fetch government mandi prices from Agmarknet via data.gov.in API.
    Used as a fallback when no mandi agent has posted a price.
    Returns a list of {mandi, price} dicts.

    API: https://data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070
    Replace AGMARKNET_API_KEY in config.py with a real data.gov.in API key.
    """
    try:
        params = {
            "api-key":  Config.AGMARKNET_API_KEY,
            "format":   "json",
            "filters[State]":     state,
            "filters[Commodity]": crop_name,
            "limit":    5
        }
        resp = requests.get(Config.AGMARKNET_BASE_URL, params=params, timeout=5)
        data = resp.json()

        # Parse records from API response
        records = data.get("records", [])
        prices  = []
        for rec in records:
            prices.append({
                "mandi": rec.get("Market",   "Unknown"),
                "price": float(rec.get("Modal_Price", 0)) * 1000  # convert ₹/quintal → ₹/ton
            })
        return prices if prices else _agmarknet_fallback(crop_name)

    except Exception:
        return _agmarknet_fallback(crop_name)


def _agmarknet_fallback(crop_name):
    """
    Hardcoded fallback prices for common crops when Agmarknet API is unavailable.
    Based on typical Karnataka mandi prices (₹ per ton).
    """
    fallback = {
        "Tomato":    [{"mandi": "KR Market",       "price": 11000},
                      {"mandi": "Kolar Mandi",      "price": 12500}],
        "Onion":     [{"mandi": "Kolar Mandi",      "price": 14000},
                      {"mandi": "Yeshwanthpur",     "price": 15500}],
        "Potato":    [{"mandi": "Tumakuru Mandi",   "price": 17000},
                      {"mandi": "KR Market",        "price": 18500}],
        "Carrot":    [{"mandi": "Kolar Mandi",      "price": 17000},
                      {"mandi": "Mysuru Mandi",     "price": 18000}],
        "Marigold":  [{"mandi": "Kolar Mandi",      "price": 24000},
                      {"mandi": "KR Market",        "price": 26000}],
        "Rose":      [{"mandi": "Kolar Mandi",      "price": 55000},
                      {"mandi": "KR Market",        "price": 62000}],
        "Ragi":      [{"mandi": "Tumakuru Mandi",   "price": 28000},
                      {"mandi": "Hassan Mandi",     "price": 30000}],
    }
    return fallback.get(crop_name, [{"mandi": "KR Market", "price": 10000}])


def calculate_transport_cost(distance_km, quantity_tons, mode="Truck"):
    """
    Accurate agricultural transport cost model for Karnataka.

    Formula breaks cost into four real components:

    1. VARIABLE COST  — fuel/fodder per km × distance × trips needed
    2. LOADING/UNLOADING — fixed labour charge per ton
    3. TOLL / ROAD TAX  — per km on state highways (Truck/Mini Truck only)
    4. DRIVER ALLOWANCE — per trip flat charge (Truck/Mini Truck only)

    Vehicle specs (Karnataka agricultural transport norms):
    ┌──────────────┬──────────┬───────────────┬────────────────┬──────────────┐
    │ Mode         │ Capacity │ Fuel ₹/km     │ Load/Unload ₹/t│ Toll ₹/km   │
    ├──────────────┼──────────┼───────────────┼────────────────┼──────────────┤
    │ Bullock Cart │ 0.75 t   │ 4 (fodder)    │ 80             │ 0            │
    │ Tractor      │ 3 t      │ 18 (diesel)   │ 100            │ 0            │
    │ Mini Truck   │ 3 t      │ 22 (diesel)   │ 120            │ 0.80         │
    │ Truck        │ 10 t     │ 35 (diesel)   │ 150            │ 1.20         │
    └──────────────┴──────────┴───────────────┴────────────────┴──────────────┘

    Returns a dict with itemised breakdown + grand total.
    """
    SPECS = {
        "Bullock Cart": {"capacity": 0.75, "fuel_per_km":  4, "load_per_ton":  80, "toll_per_km": 0,    "driver_per_trip":   0},
        "Tractor":      {"capacity": 3.0,  "fuel_per_km": 18, "load_per_ton": 100, "toll_per_km": 0,    "driver_per_trip": 300},
        "Mini Truck":   {"capacity": 3.0,  "fuel_per_km": 22, "load_per_ton": 120, "toll_per_km": 0.80, "driver_per_trip": 500},
        "Truck":        {"capacity": 10.0, "fuel_per_km": 35, "load_per_ton": 150, "toll_per_km": 1.20, "driver_per_trip": 800},
    }

    spec = SPECS.get(mode, SPECS["Truck"])

    import math
    trips = math.ceil(quantity_tons / spec["capacity"])

    fuel_cost    = round(spec["fuel_per_km"] * distance_km * trips, 2)
    loading_cost = round(spec["load_per_ton"] * quantity_tons, 2)
    toll_cost    = round(spec["toll_per_km"] * distance_km * trips, 2)
    driver_cost  = round(spec["driver_per_trip"] * trips, 2)
    total        = round(fuel_cost + loading_cost + toll_cost + driver_cost, 2)

    return {
        "trips":        trips,
        "capacity_ton": spec["capacity"],
        "fuel_cost":    fuel_cost,
        "loading_cost": loading_cost,
        "toll_cost":    toll_cost,
        "driver_cost":  driver_cost,
        "total":        total,
    }


def send_sms_notification(mobile, message):
    """
    Send SMS/WhatsApp via Fast2SMS API.
    Replace FAST2SMS_API_KEY in config.py with a real key.

    Fast2SMS docs: https://www.fast2sms.com/docs/
    """
    try:
        headers = {
            "authorization": Config.FAST2SMS_API_KEY,
            "Content-Type":  "application/json"
        }
        payload = {
            "route":   "q",            # Quick SMS route
            "message": message,
            "language":"english",
            "flash":   0,
            "numbers": mobile
        }
        resp = requests.post(Config.FAST2SMS_BASE_URL,
                             json=payload, headers=headers, timeout=5)
        data = resp.json()
        return data.get("return", False)
    except Exception:
        # Log error in production; return False here
        return False


# =============================================================
# ===  NOMINATIM GEOCODING (OSM)  ============================
# =============================================================

def geocode_location(query, limit=1):
    """
    Convert a village/city name to lat/lon using OSM Nominatim.
    Free, no API key. Rate limit: 1 req/sec.
    Returns: {"lat": float, "lon": float, "display_name": str} or None.

    Nominatim docs: https://nominatim.org/release-docs/develop/api/Search/
    """
    try:
        params = {
            "q":      f"{query}, Karnataka, India",
            "format": "json",
            "limit":  limit,
        }
        headers = {"User-Agent": "KSHETRA-AgriApp/1.0"}
        resp = requests.get(
            f"{Config.NOMINATIM_BASE_URL}/search",
            params=params, headers=headers, timeout=5
        )
        results = resp.json()
        if results:
            r = results[0]
            return {
                "lat":          float(r["lat"]),
                "lon":          float(r["lon"]),
                "display_name": r.get("display_name", query)
            }
    except Exception:
        pass

    # Fallback to config coords
    coords = Config.CITY_COORDS.get(query)
    if coords:
        return {"lat": coords["lat"], "lon": coords["lon"], "display_name": query}
    return None


# =============================================================
# ===  OSRM ROUTE POLYLINE  ==================================
# =============================================================

def get_osrm_route(origin_lon, origin_lat, dest_lon, dest_lat):
    """
    Fetch a driving route from OSRM (free, no key).
    Returns: {
        "distance_km": float,
        "duration_min": float,
        "geometry": [[lat, lon], ...]   # decoded polyline for Leaflet
    }
    Falls back to straight line if OSRM is unreachable.

    OSRM docs: http://project-osrm.org/docs/v5.24.0/api/
    """
    try:
        url = f"{Config.OSRM_BASE_URL}/{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
        params = {
            "overview":    "full",
            "geometries":  "geojson",
            "steps":       "false"
        }
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()

        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            coords = route["geometry"]["coordinates"]
            # GeoJSON is [lon, lat] → Leaflet needs [lat, lon]
            polyline = [[c[1], c[0]] for c in coords]
            return {
                "distance_km":  round(route["distance"] / 1000, 1),
                "duration_min": round(route["duration"] / 60, 1),
                "geometry":     polyline
            }
    except Exception:
        pass

    # Fallback: straight line
    return {
        "distance_km":  0,
        "duration_min": 0,
        "geometry":     [[origin_lat, origin_lon], [dest_lat, dest_lon]]
    }


# =============================================================
# ===  OVERPASS API — NEARBY FACILITIES  ======================
# =============================================================

def get_nearby_facilities(lat, lon, radius_m=None):
    """
    Find nearby agricultural facilities using OSM Overpass API.
    Searches for: cold storage, fuel stations, warehouses, marketplaces.
    Returns a list of {"name", "type", "lat", "lon"} dicts.

    Overpass docs: https://wiki.openstreetmap.org/wiki/Overpass_API
    """
    if radius_m is None:
        radius_m = Config.OVERPASS_SEARCH_RADIUS_M

    # Overpass QL: search for relevant POI types
    query = f"""
    [out:json][timeout:10];
    (
      node["landuse"="cold_storage"](around:{radius_m},{lat},{lon});
      node["amenity"="fuel"](around:{radius_m},{lat},{lon});
      node["building"="warehouse"](around:{radius_m},{lat},{lon});
      node["amenity"="marketplace"](around:{radius_m},{lat},{lon});
      node["shop"="agrarian"](around:{radius_m},{lat},{lon});
      node["industrial"="warehouse"](around:{radius_m},{lat},{lon});
    );
    out body 30;
    """

    FACILITY_TYPE_MAP = {
        "cold_storage": "Cold Storage",
        "fuel":         "Petrol Pump",
        "warehouse":    "Warehouse",
        "marketplace":  "Marketplace",
        "agrarian":     "Agri Shop",
    }

    try:
        resp = requests.post(
            Config.OVERPASS_BASE_URL,
            data={"data": query},
            timeout=12
        )
        data = resp.json()
        facilities = []

        for el in data.get("elements", []):
            tags = el.get("tags", {})
            # Determine type
            ftype = "Other"
            for key_tag in ["landuse", "amenity", "building", "shop", "industrial"]:
                val = tags.get(key_tag, "")
                if val in FACILITY_TYPE_MAP:
                    ftype = FACILITY_TYPE_MAP[val]
                    break

            facilities.append({
                "name": tags.get("name", f"{ftype}"),
                "type": ftype,
                "lat":  el.get("lat", lat),
                "lon":  el.get("lon", lon),
            })

        return facilities

    except Exception:
        return []


# =============================================================
# ===  OPENWEATHERMAP — ENHANCED WEATHER  ====================
# =============================================================

def get_openweather_forecast(city):
    """
    Fetch current weather + 5-day forecast from OpenWeatherMap.
    Free tier: 1000 calls/day with API key.
    Falls back to Open-Meteo if OWM key is dummy/invalid.

    Returns: {
        "rain_probability": 0-100,
        "max_temp": float,
        "description": str,
        "icon": str,          # OWM icon code (e.g. "10d")
        "humidity": int,
        "wind_speed": float,  # m/s
        "alerts": [str],      # severe weather alerts
        "source": "openweathermap" | "open-meteo"
    }
    """
    coords = Config.CITY_COORDS.get(city)
    if not coords:
        return get_weather_forecast(city)

    api_key = Config.OPENWEATHERMAP_API_KEY

    # If key is dummy, fall back to Open-Meteo
    if "DUMMY" in api_key or "REPLACE" in api_key:
        result = get_weather_forecast(city)
        result["source"] = "open-meteo"
        result["icon"]   = "02d"
        result["humidity"]   = 65
        result["wind_speed"] = 3.5
        result["alerts"]     = []
        return result

    try:
        # Current weather
        params = {
            "lat":   coords["lat"],
            "lon":   coords["lon"],
            "appid": api_key,
            "units": "metric"
        }
        resp = requests.get(
            f"{Config.OPENWEATHERMAP_BASE_URL}/weather",
            params=params, timeout=5
        )
        current = resp.json()

        # 5-day forecast for rain probability
        resp2 = requests.get(
            f"{Config.OPENWEATHERMAP_BASE_URL}/forecast",
            params=params, timeout=5
        )
        forecast = resp2.json()

        # Extract max rain probability from forecast
        rain_prob = 0
        max_temp = current.get("main", {}).get("temp_max", 30)
        for entry in forecast.get("list", [])[:8]:  # next 24h
            pop = entry.get("pop", 0) * 100  # probability of precipitation
            rain_prob = max(rain_prob, pop)
            t = entry.get("main", {}).get("temp_max", 0)
            max_temp = max(max_temp, t)

        # Weather alerts (if available via OneCall — needs paid tier)
        alerts = []

        icon = "02d"
        weather_list = current.get("weather", [])
        if weather_list:
            icon = weather_list[0].get("icon", "02d")

        desc = current.get("weather", [{}])[0].get("description", "clear sky").title()

        return {
            "rain_probability": int(rain_prob),
            "max_temp":         round(max_temp, 1),
            "description":      f"{desc}. Max {max_temp}°C, Rain {int(rain_prob)}%",
            "icon":             icon,
            "humidity":         current.get("main", {}).get("humidity", 50),
            "wind_speed":       current.get("wind", {}).get("speed", 0),
            "alerts":           alerts,
            "source":           "openweathermap"
        }

    except Exception:
        # Fall back to Open-Meteo
        result = get_weather_forecast(city)
        result["source"]     = "open-meteo"
        result["icon"]       = "02d"
        result["humidity"]   = 65
        result["wind_speed"] = 3.5
        result["alerts"]     = []
        return result


# =============================================================
# ===  MANDI RECOMMENDATION ALGORITHM  =======================
# =============================================================

def recommend_mandis(farmer, crop):
    """
    Core recommendation engine.
    Scores each mandi for a given crop using:
        Net Profit = Mandi Price − Cost of Production − Transport Cost
    Additional penalties:
        - Active disruptions on route → subtract 20% of profit
        - Rain probability > 60%      → subtract 10% of profit
    Returns a sorted list of mandi recommendations (best first).

    Weather is fetched once per unique city (not once per agent) to avoid
    multiple blocking HTTP calls.
    """
    agents      = MandiAgent.query.all()
    results     = []
    disruptions = Disruption.query.filter_by(active_flag=True).all()
    disrupted_routes = [d.route.lower() for d in disruptions]

    # --- Pre-fetch weather in parallel for all unique cities ---
    unique_cities = list({a.location for a in agents})
    weather_cache = {}

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=len(unique_cities) or 1) as pool:
        future_map = {pool.submit(get_weather_forecast, city): city for city in unique_cities}
        for future in as_completed(future_map):
            city = future_map[future]
            try:
                weather_cache[city] = future.result()
            except Exception:
                weather_cache[city] = {"rain_probability": 10, "max_temp": 30, "description": "N/A"}

    for agent in agents:
        mandi_location = agent.location

        # 1. Mandi price
        entry = (PriceEntry.query
                 .filter_by(mandi_agent_id=agent.id, crop_name=crop.name)
                 .order_by(PriceEntry.date.desc())
                 .first())

        if entry:
            mandi_price = entry.price
        else:
            gov_prices  = _agmarknet_fallback(crop.name)   # use local fallback directly — no HTTP
            mandi_price = gov_prices[0]["price"] if gov_prices else 10000

        # 2. Distance & transport cost
        distance       = get_distance(farmer.district, mandi_location)
        transport_cost = calculate_transport_cost(distance, crop.quantity, "Truck")["total"]

        # 3. Net profit
        net_profit = (mandi_price - farmer.cost_of_production) * crop.quantity - transport_cost

        # 4. Weather penalty (from cache)
        weather   = weather_cache.get(mandi_location, {"rain_probability": 10, "max_temp": 30, "description": "N/A"})
        rain_prob = weather["rain_probability"]
        if rain_prob > 60:
            net_profit *= 0.90

        # 5. Disruption penalty
        route_key  = f"{farmer.district.lower()} → {mandi_location.lower()}"
        route_key2 = f"{mandi_location.lower()} → {farmer.district.lower()}"
        is_disrupted = any(route_key in r or route_key2 in r for r in disrupted_routes)
        if is_disrupted:
            net_profit *= 0.80

        # Get coordinates for the mandi
        coords = Config.MANDI_COORDS.get(agent.mandi) or Config.CITY_COORDS.get(mandi_location)
        if not coords:
            coords = geocode_location(mandi_location) or {"lat": 12.9716, "lon": 77.5946}

        results.append({
            "agent_name":     agent.name,
            "agent_id":       agent.id,
            "mandi":          agent.mandi,
            "location":       mandi_location,
            "mandi_price":    mandi_price,
            "distance_km":    distance,
            "transport_cost": transport_cost,
            "net_profit":     round(net_profit, 2),
            "rain_prob":      rain_prob,
            "weather_desc":   weather["description"],
            "is_disrupted":   is_disrupted,
            "lat":            coords.get("lat"),
            "lon":            coords.get("lon"),
        })

    results.sort(key=lambda x: x["net_profit"], reverse=True)
    return results


# =============================================================
# ===  ROUTES — GENERAL  =====================================
# =============================================================

@app.route("/")
def index():
    """Landing page — links to farmer and mandi agent login/register."""
    return render_template("index.html")


# =============================================================
# ===  ROUTES — FARMER  ======================================
# =============================================================

@app.route("/register_farmer", methods=["GET", "POST"])
def register_farmer():
    """
    GET  → Show registration form
    POST → Validate & save new Farmer to DB
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        name     = request.form.get("name", "").strip()
        mobile   = request.form.get("mobile", "").strip()
        village  = request.form.get("village", "").strip()
        district = request.form.get("district", "").strip()
        password = request.form.get("password", "").strip()
        cop      = float(request.form.get("cost_of_production", 0))

        # Validation
        if not all([username, name, mobile, village, district, password]):
            flash("All fields are required.", "danger")
            return redirect(url_for("register_farmer"))

        if Farmer.query.filter_by(username=username).first():
            flash("Username already exists. Choose another.", "warning")
            return redirect(url_for("register_farmer"))

        farmer = Farmer(
            name=name, mobile=mobile, village=village,
            district=district, username=username,
            password=password,        # store hash in production
            cost_of_production=cop
        )
        db.session.add(farmer)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login_farmer"))

    return render_template("register.html", role="farmer")


@app.route("/login_farmer", methods=["GET", "POST"])
def login_farmer():
    """
    Authenticate a Farmer using username + password.
    Stores farmer_id in Flask session on success.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        farmer = Farmer.query.filter_by(username=username).first()

        if farmer and farmer.password == password:
            session.clear()
            session["farmer_id"]   = farmer.id
            session["farmer_name"] = farmer.name
            session["role"]        = "farmer"
            flash(f"Welcome back, {farmer.name}! 👨‍🌾", "success")
            return redirect(url_for("farmer_dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html", role="farmer")


@app.route("/farmer_dashboard")
def farmer_dashboard():
    """
    Farmer's main dashboard showing:
    - List of their crops
    - NDVI / crop health via AgroMonitoring
    - Active disruptions warning
    - Quick access to mandi recommendations & pre-bookings
    """
    if session.get("role") != "farmer":
        flash("Please login as a farmer.", "warning")
        return redirect(url_for("login_farmer"))

    farmer      = Farmer.query.get(session["farmer_id"])
    crops       = Crop.query.filter_by(farmer_id=farmer.id).order_by(Crop.shelf_life_days.asc()).all()
    disruptions = Disruption.query.order_by(
                      Disruption.active_flag.desc(),
                      Disruption.start_date.desc()).all()
    active_disruptions = [d for d in disruptions if d.active_flag]

    # NDVI crop health for farmer's district
    ndvi_data   = get_agro_ndvi(farmer.district)

    # All pre-bookings for this farmer
    bookings    = PreBooking.query.filter_by(farmer_id=farmer.id).order_by(
                      PreBooking.created_at.desc()).all()

    # All mandi agents for pre-booking form
    agents      = MandiAgent.query.all()

    # Market prices (last 48 hours) for the prices tab
    since       = date.today() - timedelta(days=2)
    price_entries = (PriceEntry.query
                     .filter(PriceEntry.date >= since)
                     .order_by(PriceEntry.date.desc(), PriceEntry.price.desc())
                     .all())

    # Active tab from query param (default: platform)
    active_tab  = request.args.get("tab", "platform")
    max_price_id = db.session.query(db.func.max(PriceEntry.id)).scalar() or 0

    # Calculate coordinates for map
    farmer_coords = geocode_location(farmer.village) or geocode_location(farmer.district)
    
    mandi_coords = []
    for agent in agents:
        coords = Config.MANDI_COORDS.get(agent.mandi) or Config.CITY_COORDS.get(agent.location)
        if not coords:
            coords = geocode_location(agent.location)
        if coords:
            mandi_coords.append({
                "name": agent.mandi,
                "location": agent.location,
                "lat": coords["lat"],
                "lon": coords["lon"]
            })

    return render_template(
        "farmer_dashboard.html",
        farmer=farmer,
        crops=crops,
        disruptions=disruptions,
        active_disruptions=active_disruptions,
        ndvi=ndvi_data,
        bookings=bookings,
        agents=agents,
        price_entries=price_entries,
        active_tab=active_tab,
        today=date.today().strftime("%Y-%m-%d"),
        farmer_coords=farmer_coords,
        mandi_coords=mandi_coords,
        max_price_id=max_price_id
    )


@app.route("/add_crop", methods=["POST"])
def add_crop():
    """
    POST: Add a new crop for the logged-in farmer.
    Form fields: name, quantity, shelf_life_days
    """
    if session.get("role") != "farmer":
        return redirect(url_for("login_farmer"))

    name            = request.form.get("crop_name", "").strip().title()
    quantity        = float(request.form.get("quantity", 0))
    shelf_life_days = int(request.form.get("shelf_life_days", 7))

    if not name or quantity <= 0:
        flash("Please enter valid crop details.", "danger")
        return redirect(url_for("farmer_dashboard"))

    crop = Crop(
        name=name,
        quantity=quantity,
        shelf_life_days=shelf_life_days,
        farmer_id=session["farmer_id"]
    )
    db.session.add(crop)
    db.session.commit()
    flash(f"Crop '{name}' added successfully!", "success")
    return redirect(url_for("farmer_dashboard"))


@app.route("/delete_crop/<int:crop_id>", methods=["POST"])
def delete_crop(crop_id):
    """Delete a crop belonging to the logged-in farmer."""
    if session.get("role") != "farmer":
        return redirect(url_for("login_farmer"))
    crop = Crop.query.get_or_404(crop_id)
    if crop.farmer_id != session["farmer_id"]:
        flash("Unauthorised.", "danger")
        return redirect(url_for("farmer_dashboard"))
    db.session.delete(crop)
    db.session.commit()
    flash(f"Crop '{crop.name}' deleted.", "info")
    return redirect(url_for("farmer_dashboard"))


@app.route("/edit_crop/<int:crop_id>", methods=["POST"])
def edit_crop(crop_id):
    """Update quantity and shelf_life_days for a crop."""
    if session.get("role") != "farmer":
        return redirect(url_for("login_farmer"))
    crop = Crop.query.get_or_404(crop_id)
    if crop.farmer_id != session["farmer_id"]:
        flash("Unauthorised.", "danger")
        return redirect(url_for("farmer_dashboard"))
    quantity        = request.form.get("quantity", type=float)
    shelf_life_days = request.form.get("shelf_life_days", type=int)
    if quantity and quantity > 0:
        crop.quantity = quantity
    if shelf_life_days and shelf_life_days > 0:
        crop.shelf_life_days = shelf_life_days
    db.session.commit()
    flash(f"Crop '{crop.name}' updated.", "success")
    return redirect(url_for("farmer_dashboard"))


@app.route("/recommend_mandi")
def recommend_mandi():
    """
    GET: Returns mandi recommendations for the farmer's first crop.
    Algorithm: sorts mandis by net_profit = (price - COP) * qty - transport_cost
    Weather and disruption penalties applied.
    """
    if session.get("role") != "farmer":
        flash("Please login as a farmer.", "warning")
        return redirect(url_for("login_farmer"))

    farmer = Farmer.query.get(session["farmer_id"])
    crops  = Crop.query.filter_by(farmer_id=farmer.id).all()

    if not crops:
        flash("Please add at least one crop before requesting recommendations.", "info")
        return redirect(url_for("farmer_dashboard"))

    # Allow crop selection via query param ?crop_id=X
    crop_id = request.args.get("crop_id", type=int)
    if crop_id:
        crop = Crop.query.get(crop_id)
    else:
        crop = crops[0]   # default to first crop

    recommendations = recommend_mandis(farmer, crop)
    farmer_coords = geocode_location(farmer.village) or geocode_location(farmer.district)

    return render_template(
        "recommend.html",
        farmer=farmer,
        crop=crop,
        crops=crops,
        recommendations=recommendations,
        farmer_coords=farmer_coords
    )


# =============================================================
# ===  ROUTES — MANDI AGENT  =================================
# =============================================================

@app.route("/register_mandi", methods=["GET", "POST"])
def register_mandi():
    """
    GET  → Show mandi agent registration form
    POST → Validate & save new MandiAgent to DB
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        name     = request.form.get("name", "").strip()
        mandi    = request.form.get("mandi", "").strip()
        location = request.form.get("location", "").strip()
        contact  = request.form.get("contact", "").strip()
        password = request.form.get("password", "").strip()

        if not all([username, name, mandi, location, contact, password]):
            flash("All fields are required.", "danger")
            return redirect(url_for("register_mandi"))

        if MandiAgent.query.filter_by(username=username).first():
            flash("Username already taken.", "warning")
            return redirect(url_for("register_mandi"))

        agent = MandiAgent(
            name=name, mandi=mandi, location=location,
            contact=contact, username=username, password=password
        )
        db.session.add(agent)
        db.session.commit()
        flash("Mandi Agent registered successfully! Please login.", "success")
        return redirect(url_for("login_mandi"))

    return render_template("register.html", role="mandi")


@app.route("/login_mandi", methods=["GET", "POST"])
def login_mandi():
    """
    Authenticate a MandiAgent using username + password.
    Stores agent_id in Flask session on success.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        agent = MandiAgent.query.filter_by(username=username).first()

        if agent and agent.password == password:
            session.clear()
            session["agent_id"]   = agent.id
            session["agent_name"] = agent.name
            session["role"]       = "mandi"
            flash(f"Welcome, {agent.name}! 🏪", "success")
            return redirect(url_for("mandi_dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html", role="mandi")


@app.route("/mandi_dashboard")
def mandi_dashboard():
    """
    Mandi Agent's dashboard with sidebar tabs:
    - Platform: post price + prices this week
    - Supply Pipeline: pre-bookings
    - Market Prices: all recent prices
    - All Alerts: disruptions
    """
    if session.get("role") != "mandi":
        flash("Please login as a mandi agent.", "warning")
        return redirect(url_for("login_mandi"))

    agent  = MandiAgent.query.get(session["agent_id"])

    # Prices posted by this agent (last 7 days)
    since  = date.today() - timedelta(days=7)
    prices = (PriceEntry.query
              .filter_by(mandi_agent_id=agent.id)
              .filter(PriceEntry.date >= since)
              .order_by(PriceEntry.date.desc())
              .all())

    # All supply pipeline bookings for this agent
    supply_all   = PreBooking.query.filter_by(mandi_agent_id=agent.id).order_by(
                       PreBooking.created_at.desc()).all()
    supply       = [b for b in supply_all if b.status == "Pending"]

    # All market price entries (last 48h) for market prices tab
    since_48     = date.today() - timedelta(days=2)
    all_prices   = (PriceEntry.query
                    .filter(PriceEntry.date >= since_48)
                    .order_by(PriceEntry.date.desc(), PriceEntry.price.desc())
                    .all())

    # All disruptions for alerts tab
    all_disrupt  = Disruption.query.order_by(
                       Disruption.active_flag.desc(),
                       Disruption.start_date.desc()).all()
    active_disrupt = [d for d in all_disrupt if d.active_flag]

    # Route options for flag form
    route_options = sorted(set(f"{a} → {b}" for (a, b) in DISTANCE_MATRIX.keys() if a < b))

    active_tab = request.args.get("tab", "platform")

    return render_template(
        "mandi_dashboard.html",
        agent=agent,
        prices=prices,
        supply=supply,
        supply_all=supply_all,
        disruptions=active_disrupt,
        all_disruptions=all_disrupt,
        all_prices=all_prices,
        route_options=route_options,
        active_tab=active_tab,
        today=date.today().strftime("%Y-%m-%d"),
    )


@app.route("/post_price", methods=["POST"])
def post_price():
    """
    POST: Mandi agent posts today's price for a specific crop.
    Form fields: crop_name, price, quantity_required
    """
    if session.get("role") != "mandi":
        return redirect(url_for("login_mandi"))

    crop_name         = request.form.get("crop_name", "").strip().title()
    price_val         = float(request.form.get("price", 0))
    qty_req_str       = request.form.get("quantity_required", "").strip()
    quantity_required = float(qty_req_str) if qty_req_str else None

    if not crop_name or price_val <= 0:
        flash("Please enter valid crop name and price.", "danger")
        return redirect(url_for("mandi_dashboard"))

    crop    = Crop.query.filter(Crop.name.ilike(crop_name)).first()
    crop_id = crop.id if crop else None

    entry = PriceEntry(
        crop_id=crop_id,
        mandi_agent_id=session["agent_id"],
        crop_name=crop_name,
        price=price_val,
        quantity_required=quantity_required,
        date=date.today()
    )
    db.session.add(entry)
    db.session.commit()
    qty_str = f" · {quantity_required}t required" if quantity_required else ""
    flash(f"Price posted: ₹{price_val:,.0f}/ton for {crop_name}{qty_str}", "success")
    return redirect(url_for("mandi_dashboard"))


@app.route("/delete_price/<int:entry_id>", methods=["POST"])
def delete_price(entry_id):
    """Delete a price entry posted by the logged-in mandi agent."""
    if session.get("role") != "mandi":
        return redirect(url_for("login_mandi"))
    entry = PriceEntry.query.get_or_404(entry_id)
    if entry.mandi_agent_id != session["agent_id"]:
        flash("Unauthorised.", "danger")
        return redirect(url_for("mandi_dashboard"))
    db.session.delete(entry)
    db.session.commit()
    flash(f"Price entry for {entry.crop_name} deleted.", "info")
    return redirect(url_for("mandi_dashboard"))


@app.route("/edit_price/<int:entry_id>", methods=["POST"])
def edit_price(entry_id):
    """Update price and/or quantity_required for a price entry."""
    if session.get("role") != "mandi":
        return redirect(url_for("login_mandi"))
    entry = PriceEntry.query.get_or_404(entry_id)
    if entry.mandi_agent_id != session["agent_id"]:
        flash("Unauthorised.", "danger")
        return redirect(url_for("mandi_dashboard"))
    price    = request.form.get("price", type=float)
    qty_req  = request.form.get("quantity_required", "").strip()
    if price and price > 0:
        entry.price = price
    entry.quantity_required = float(qty_req) if qty_req else None
    db.session.commit()
    flash(f"{entry.crop_name} updated — ₹{entry.price:,.0f}/ton.", "success")
    return redirect(url_for("mandi_dashboard"))


@app.route("/view_prices")
def view_prices():
    """
    Public view: latest prices for all crops across all mandis.
    Shows today + yesterday's entries.
    """
    since   = date.today() - timedelta(days=2)
    entries = (PriceEntry.query
               .filter(PriceEntry.date >= since)
               .order_by(PriceEntry.date.desc(), PriceEntry.price.desc())
               .all())
    return render_template("view_prices.html", entries=entries)


# =============================================================
# ===  ROUTES — DISRUPTIONS  =================================
# =============================================================

@app.route("/view_disruptions")
def view_disruptions():
    """
    List all disruptions (active and past).
    Accessible to both farmers and mandi agents.
    """
    disruptions = Disruption.query.order_by(
        Disruption.active_flag.desc(),
        Disruption.start_date.desc()
    ).all()
    return render_template("disruption.html", disruptions=disruptions,
                           show_form=False, today=date.today().strftime("%Y-%m-%d"))


@app.route("/add_disruption", methods=["GET", "POST"])
def add_disruption():
    """
    GET  → Form to add a new disruption
    POST → Save disruption to DB
    Only mandi agents or admin can add disruptions.
    """
    if session.get("role") not in ("mandi", "admin"):
        flash("Only mandi agents can report disruptions.", "warning")
        return redirect(url_for("login_mandi"))

    if request.method == "POST":
        route       = request.form.get("route", "").strip()
        dtype       = request.form.get("type", "").strip()
        description = request.form.get("description", "").strip()
        start_str   = request.form.get("start_date", "")
        end_str     = request.form.get("end_date", "")

        if not route or not dtype or not start_str:
            flash("Route, type and start date are required.", "danger")
            return redirect(url_for("add_disruption"))

        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date   = datetime.strptime(end_str,   "%Y-%m-%d").date() if end_str else None

        d = Disruption(
            route=route, type=dtype,
            description=description,
            start_date=start_date,
            end_date=end_date,
            active_flag=True
        )
        db.session.add(d)
        db.session.commit()
        flash(f"Disruption on '{route}' reported successfully.", "success")
        return redirect(url_for("view_disruptions"))

    # Provide route options for dropdown (from distance matrix)
    route_options = sorted(set(f"{a} → {b}" for (a, b) in DISTANCE_MATRIX.keys() if a < b))
    return render_template("disruption.html",
                           disruptions=Disruption.query.all(),
                           route_options=route_options,
                           show_form=True,
                           today=date.today().strftime("%Y-%m-%d"))


@app.route("/resolve_disruption/<int:disruption_id>", methods=["POST"])
def resolve_disruption(disruption_id):
    """Mark a disruption as resolved (active_flag = False)."""
    if session.get("role") not in ("mandi", "admin"):
        flash("Unauthorised.", "danger")
        return redirect(url_for("view_disruptions"))

    d = Disruption.query.get_or_404(disruption_id)
    d.active_flag = False
    db.session.commit()
    flash("Disruption resolved.", "success")
    return redirect(url_for("view_disruptions"))


# =============================================================
# ===  ROUTES — PRICE HISTORY  ===============================
# =============================================================

@app.route("/price_history/<int:crop_id>")
def price_history(crop_id):
    """
    Shows a 30-day price trend chart for a given crop across all mandis.
    Chart is rendered client-side using Chart.js (data injected as JSON).
    """
    crop   = Crop.query.get_or_404(crop_id)
    since  = date.today() - timedelta(days=30)

    entries = (PriceEntry.query
               .filter_by(crop_id=crop_id)
               .filter(PriceEntry.date >= since)
               .order_by(PriceEntry.date.asc())
               .all())

    # Build data series per mandi for Chart.js
    mandi_series = {}
    for e in entries:
        mandi_name = e.agent.mandi if e.agent else "Unknown"
        if mandi_name not in mandi_series:
            mandi_series[mandi_name] = []
        mandi_series[mandi_name].append({
            "date":  e.date.strftime("%d %b"),
            "price": e.price
        })

    return render_template(
        "price_history.html",
        crop=crop,
        mandi_series=mandi_series,
        entries=entries
    )


@app.route("/api/price_history/<int:crop_id>")
def api_price_history(crop_id):
    """
    JSON API endpoint for price history (used by Chart.js frontend).
    Returns: { mandi_name: [{date, price}, ...], ... }
    """
    since   = date.today() - timedelta(days=30)
    entries = (PriceEntry.query
               .filter_by(crop_id=crop_id)
               .filter(PriceEntry.date >= since)
               .order_by(PriceEntry.date.asc())
               .all())

    data = {}
    for e in entries:
        mandi_name = e.agent.mandi if e.agent else "Unknown"
        if mandi_name not in data:
            data[mandi_name] = []
        data[mandi_name].append({"date": e.date.strftime("%d %b"), "price": e.price})

    return jsonify(data)


# =============================================================
# ===  ROUTES — NOTIFICATIONS  ===============================
# =============================================================

@app.route("/notify_farmer/<int:farmer_id>", methods=["POST"])
def notify_farmer(farmer_id):
    """
    POST: Build top mandi recommendation message and send via Fast2SMS.
    Requires mandi agent or admin session.
    """
    farmer = Farmer.query.get_or_404(farmer_id)
    crops  = Crop.query.filter_by(farmer_id=farmer.id).all()

    if not crops:
        flash("Farmer has no crops. Cannot send recommendation.", "warning")
        return redirect(url_for("farmer_dashboard"))

    crop            = crops[0]
    recommendations = recommend_mandis(farmer, crop)

    if not recommendations:
        flash("No recommendations available.", "info")
        return redirect(url_for("farmer_dashboard"))

    top    = recommendations[0]
    msg    = (
        f"KSHETRA Alert: Best mandi for your {crop.name} is "
        f"{top['mandi']} ({top['location']}). "
        f"Price: Rs.{top['mandi_price']}/ton. "
        f"Est. Net Profit: Rs.{top['net_profit']}. "
        f"Distance: {top['distance_km']}km."
    )

    success = send_sms_notification(farmer.mobile, msg)
    if success:
        flash(f"SMS sent to {farmer.name} ({farmer.mobile}).", "success")
    else:
        flash(f"SMS failed (demo mode). Message: {msg}", "info")

    return redirect(url_for("farmer_dashboard"))


# =============================================================
# ===  ROUTES — PRE-BOOKING (Bulk Sell)  =====================
# =============================================================

@app.route("/prebooking", methods=["GET", "POST"])
def prebooking():
    """
    GET  → Show pre-booking form (farmer) or supply pipeline (mandi agent)
    POST → Farmer submits a pre-booking for bulk sell
    """
    if session.get("role") == "farmer":
        if request.method == "POST":
            crop_name      = request.form.get("crop_name", "").strip().title()
            quantity       = float(request.form.get("quantity", 0))
            pref_date_str  = request.form.get("preferred_date", "")
            agent_id       = request.form.get("agent_id", type=int)

            if not crop_name or quantity <= 0:
                flash("Please enter valid crop name and quantity.", "danger")
                return redirect(url_for("prebooking"))

            pref_date = (datetime.strptime(pref_date_str, "%Y-%m-%d").date()
                         if pref_date_str else None)

            booking = PreBooking(
                farmer_id=session["farmer_id"],
                mandi_agent_id=agent_id,
                crop_name=crop_name,
                quantity=quantity,
                preferred_date=pref_date,
                status="Pending"
            )
            db.session.add(booking)
            db.session.commit()
            flash("Pre-booking submitted successfully!", "success")
            return redirect(url_for("farmer_dashboard"))

        agents   = MandiAgent.query.all()
        bookings = PreBooking.query.filter_by(
                       farmer_id=session["farmer_id"]).order_by(
                       PreBooking.created_at.desc()).all()
        return render_template("prebooking.html",
                               agents=agents, bookings=bookings, role="farmer")

    elif session.get("role") == "mandi":
        # Mandi agent: view supply pipeline
        supply = PreBooking.query.filter_by(
                     mandi_agent_id=session["agent_id"]).order_by(
                     PreBooking.created_at.desc()).all()
        return render_template("prebooking.html", supply=supply, role="mandi")

    flash("Please login first.", "warning")
    return redirect(url_for("index"))


@app.route("/confirm_booking/<int:booking_id>", methods=["POST"])
def confirm_booking(booking_id):
    """Mandi agent confirms a farmer's pre-booking."""
    if session.get("role") != "mandi":
        flash("Unauthorised.", "danger")
        return redirect(url_for("login_mandi"))
    booking        = PreBooking.query.get_or_404(booking_id)
    booking.status = "Confirmed"
    db.session.commit()
    flash("Booking confirmed!", "success")
    return redirect(url_for("prebooking"))


# =============================================================
# ===  ROUTES — CROP DEAL (Retailer ↔ Farmer negotiation)  ===
# =============================================================

@app.route("/api/deal/available_matches")
def deal_available_matches():
    """
    JSON: For the logged-in mandi agent's price entries (last 48h),
    return farmer crops that match — same crop name, farmer quantity >= required,
    and farmer's asking price (cost_of_production + transport) <= entry price.
    Response: { price_entry_id: [{ crop_id, farmer_id, farmer_name, ... }] }
    """
    if session.get("role") != "mandi":
        return jsonify({}), 403

    agent     = MandiAgent.query.get(session["agent_id"])
    since     = date.today() - timedelta(days=2)
    entries   = (PriceEntry.query
                 .filter_by(mandi_agent_id=agent.id)
                 .filter(PriceEntry.date >= since)
                 .all())

    result = {}
    for entry in entries:
        if not entry.quantity_required:
            continue
        # Find all farmer crops with same name and quantity smaller or equal to required
        crops = (Crop.query
                 .filter(Crop.name.ilike(entry.crop_name))
                 .filter(Crop.quantity <= entry.quantity_required)
                 .all())
        matches = []
        for crop in crops:
            farmer = crop.farmer
            # Transport cost from farmer's district to mandi
            dist  = get_distance(farmer.district, agent.location)
            tc    = calculate_transport_cost(dist, entry.quantity_required, "Truck")["total"]
            # Farmer's effective price = cost_of_production + transport per ton
            farmer_price_per_ton = farmer.cost_of_production + (tc / entry.quantity_required if entry.quantity_required else 0)
            # Only show if retailer's offered price covers farmer's cost
            if entry.price < farmer_price_per_ton:
                continue
            # Check if a deal already exists for this pair
            existing = CropDeal.query.filter_by(
                price_entry_id=entry.id,
                crop_id=crop.id
            ).order_by(CropDeal.created_at.desc()).first()
            if existing and existing.status in ("rejected_retailer", "rejected_farmer"):
                existing = None
            deal_status = existing.status if existing else "available"
            deal_id     = existing.id     if existing else None


            matches.append({
                "crop_id":           crop.id,
                "farmer_id":         farmer.id,
                "farmer_name":       farmer.name,
                "farmer_village":    farmer.village,
                "farmer_district":   farmer.district,
                "farmer_mobile":     farmer.mobile,
                "crop_name":         crop.name,
                "crop_quantity":     crop.quantity,
                "distance_km":       dist,
                "transport_cost":    round(tc, 0),
                "farmer_cop":        farmer.cost_of_production,
                "farmer_price_per_ton": round(farmer_price_per_ton, 0),
                "retailer_price":    entry.price,
                "deal_status":       deal_status,
                "deal_id":           deal_id,
            })
        if matches:
            result[str(entry.id)] = matches

    return jsonify(result)


@app.route("/api/deal/request", methods=["POST"])
def deal_request():
    """Retailer requests a deal with a specific farmer crop."""
    if session.get("role") != "mandi":
        return jsonify({"error": "Unauthorised"}), 403
    data           = request.get_json()
    price_entry_id = int(data["price_entry_id"])
    crop_id        = int(data["crop_id"])

    entry  = PriceEntry.query.get_or_404(price_entry_id)
    crop   = Crop.query.get_or_404(crop_id)
    agent  = MandiAgent.query.get(session["agent_id"])

    # Check no active deal exists
    existing = CropDeal.query.filter_by(
        price_entry_id=price_entry_id, crop_id=crop_id
    ).filter(CropDeal.status.notin_(["rejected_retailer","rejected_farmer"])).first()
    if existing:
        return jsonify({"error": "Deal already exists", "deal_id": existing.id, "status": existing.status})

    dist = get_distance(crop.farmer.district, agent.location)
    tc   = calculate_transport_cost(dist, entry.quantity_required or crop.quantity, "Truck")["total"]

    deal = CropDeal(
        price_entry_id=price_entry_id,
        crop_id=crop_id,
        farmer_id=crop.farmer_id,
        agent_id=session["agent_id"],
        status="requested",
        transport_cost=round(tc, 2),
    )
    db.session.add(deal)
    db.session.commit()
    return jsonify({"ok": True, "deal_id": deal.id, "status": "requested"})


@app.route("/api/deal/retailer_reject", methods=["POST"])
def deal_retailer_reject():
    """Retailer rejects / cancels a deal request."""
    if session.get("role") != "mandi":
        return jsonify({"error": "Unauthorised"}), 403
    deal_id = int(request.get_json()["deal_id"])
    deal    = CropDeal.query.get_or_404(deal_id)
    deal.status = "rejected_retailer"
    db.session.commit()
    return jsonify({"ok": True, "status": "rejected_retailer"})


@app.route("/api/deal/farmer_accept", methods=["POST"])
def deal_farmer_accept():
    """Farmer accepts a deal request — status becomes 'accepted'."""
    if session.get("role") != "farmer":
        return jsonify({"error": "Unauthorised"}), 403
    deal_id = int(request.get_json()["deal_id"])
    deal    = CropDeal.query.get_or_404(deal_id)
    deal.status = "accepted"
    db.session.commit()
    return jsonify({"ok": True, "status": "accepted"})


@app.route("/api/deal/farmer_reject", methods=["POST"])
def deal_farmer_reject():
    """Farmer rejects a deal request — status becomes 'rejected_farmer'."""
    if session.get("role") != "farmer":
        return jsonify({"error": "Unauthorised"}), 403
    deal_id = int(request.get_json()["deal_id"])
    deal    = CropDeal.query.get_or_404(deal_id)
    deal.status = "rejected_farmer"
    db.session.commit()
    return jsonify({"ok": True, "status": "rejected_farmer"})


@app.route("/api/deal/crop_deals")
def deal_crop_deals():
    """
    JSON: Return all active deals relevant to the logged-in farmer.
    Matches by crop_name across all of this farmer's crops so the badge
    appears even when the retailer booked against a different farmer's crop
    of the same name.
    """
    if session.get("role") != "farmer":
        return jsonify({}), 403

    farmer_id = session["farmer_id"]
    my_crops  = Crop.query.filter_by(farmer_id=farmer_id).all()

    crop_by_name = {c.name.lower(): c for c in my_crops}
    crop_by_id   = {c.id: c for c in my_crops}

    # All non-rejected deals in the system
    all_deals = (CropDeal.query
                 .filter(CropDeal.status.notin_(["rejected_retailer", "rejected_farmer"]))
                 .all())

    priority = {"requested": 1, "accepted": 2}
    result   = {}

    for d in all_deals:
        # Try to match this deal to one of my crops
        matched_crop = crop_by_id.get(d.crop_id)
        if not matched_crop:
            entry_name = d.price_entry.crop_name.lower() if d.price_entry else ""
            matched_crop = crop_by_name.get(entry_name)
        if not matched_crop:
            continue

        key      = str(matched_crop.id)
        existing = result.get(key)
        if existing and priority.get(existing["status"], 0) >= priority.get(d.status, 0):
            continue   # keep higher-priority status

        agent = d.agent
        entry = d.price_entry
        result[key] = {
            "deal_id":        d.id,
            "status":         d.status,
            "agent_name":     agent.name      if agent else "",
            "mandi":          agent.mandi     if agent else "",
            "location":       agent.location  if agent else "",
            "contact":        agent.contact   if agent else "",
            "crop_name":      entry.crop_name if entry else matched_crop.name,
            "price_per_ton":  entry.price     if entry else 0,
            "qty_required":   entry.quantity_required if entry else None,
            "transport_cost": d.transport_cost,
        }

    return jsonify(result)


@app.route("/api/deal/farmer_matches")
def deal_farmer_matches():
    """
    JSON: For the logged-in farmer's crops, return price entries posted by
    mandi agents that match — same crop name, retailer qty_required <= farmer qty,
    and retailer offered price >= farmer's asking price (COP + transport).
    Response: { price_entry_id: { crop_id, crop_name, qty_available, dist, tc,
                                   farmer_price_per_ton, retailer_price,
                                   retailer_name, retailer_mandi, retailer_location,
                                   retailer_contact, qty_required, deal_status, deal_id } }
    """
    if session.get("role") != "farmer":
        return jsonify({}), 403

    farmer  = Farmer.query.get(session["farmer_id"])
    crops   = Crop.query.filter_by(farmer_id=farmer.id).all()
    since   = date.today() - timedelta(days=2)
    entries = (PriceEntry.query
               .filter(PriceEntry.date >= since)
               .filter(PriceEntry.quantity_required.isnot(None))
               .all())

    result = {}
    for entry in entries:
        if not entry.quantity_required:
            continue
        agent = entry.agent
        if not agent:
            continue
        # Find the farmer's crop matching this entry's crop name with quantity <= required
        matching_crop = None
        for crop in crops:
            if crop.name.lower() == entry.crop_name.lower() and crop.quantity <= entry.quantity_required:
                matching_crop = crop
                break

        if not matching_crop:
            continue
        # Calculate transport cost & farmer's minimum selling price
        dist = get_distance(farmer.district, agent.location)
        qty  = entry.quantity_required
        tc   = calculate_transport_cost(dist, qty, "Truck")["total"]
        tc_breakdown = calculate_transport_cost(dist, qty, "Truck")
        farmer_price_per_ton = farmer.cost_of_production + (tc / qty if qty else 0)
        # Only show if retailer's price covers farmer's cost
        if entry.price < farmer_price_per_ton:
            continue
        # Check existing deal
        existing = CropDeal.query.filter_by(
            price_entry_id=entry.id, crop_id=matching_crop.id
        ).order_by(CropDeal.created_at.desc()).first()
        if existing and existing.status in ("rejected_retailer", "rejected_farmer"):
            existing = None
        deal_status = existing.status if existing else "available"
        deal_id     = existing.id     if existing else None

        result[str(entry.id)] = {
            "crop_id":              matching_crop.id,
            "crop_name":            matching_crop.name,
            "qty_available":        matching_crop.quantity,
            "farmer_village":       farmer.village,
            "farmer_district":      farmer.district,
            "distance_km":          dist,
            "transport_cost":       round(tc, 0),
            "transport_breakdown": {
                "trips":        tc_breakdown["trips"],
                "fuel_cost":    round(tc_breakdown["fuel_cost"], 0),
                "loading_cost": round(tc_breakdown["loading_cost"], 0),
                "toll_cost":    round(tc_breakdown.get("toll_cost", 0), 0),
                "driver_cost":  round(tc_breakdown.get("driver_cost", 0), 0),
            },
            "farmer_cop":           farmer.cost_of_production,
            "farmer_price_per_ton": round(farmer_price_per_ton, 0),
            "retailer_price":       entry.price,
            "qty_required":         entry.quantity_required,
            "retailer_name":        agent.name,
            "retailer_mandi":       agent.mandi,
            "retailer_location":    agent.location,
            "retailer_contact":     agent.contact,
            "deal_status":          deal_status,
            "deal_id":              deal_id,
        }

    return jsonify(result)


@app.route("/api/deal/farmer_book", methods=["POST"])
def deal_farmer_book():
    """Farmer initiates a deal request — creates CropDeal with status='requested'."""
    if session.get("role") != "farmer":
        return jsonify({"error": "Unauthorised"}), 403
    data           = request.get_json()
    price_entry_id = int(data["price_entry_id"])
    crop_id        = int(data["crop_id"])

    entry  = PriceEntry.query.get_or_404(price_entry_id)
    crop   = Crop.query.get_or_404(crop_id)
    if crop.farmer_id != session["farmer_id"]:
        return jsonify({"error": "Unauthorised"}), 403

    # Check no active deal exists
    existing = CropDeal.query.filter_by(
        price_entry_id=price_entry_id, crop_id=crop_id
    ).filter(CropDeal.status.notin_(["rejected_retailer", "rejected_farmer"])).first()
    if existing:
        return jsonify({"error": "Deal already exists", "deal_id": existing.id, "status": existing.status})

    agent = entry.agent
    dist  = get_distance(crop.farmer.district, agent.location)
    tc    = calculate_transport_cost(dist, entry.quantity_required or crop.quantity, "Truck")["total"]

    deal = CropDeal(
        price_entry_id=price_entry_id,
        crop_id=crop_id,
        farmer_id=session["farmer_id"],
        agent_id=entry.mandi_agent_id,
        status="requested",
        transport_cost=round(tc, 2),
    )
    db.session.add(deal)
    db.session.commit()
    return jsonify({"ok": True, "deal_id": deal.id, "status": "requested"})


# =============================================================
# ===  ROUTES — TRANSPORT COST CALCULATOR (API)  =============
# =============================================================

@app.route("/api/transport_cost")
def api_transport_cost():
    """
    JSON API: Calculate accurate transport cost with itemised breakdown.
    Query params: from_city, to_city, quantity_tons, mode
    """
    from_city = request.args.get("from_city", "Tumakuru")
    to_city   = request.args.get("to_city",   "Bengaluru")
    qty       = float(request.args.get("quantity_tons", 1))
    mode      = request.args.get("mode", "Truck")

    dist      = get_distance(from_city, to_city)
    breakdown = calculate_transport_cost(dist, qty, mode)

    from_coords = Config.CITY_COORDS.get(from_city, {"lat": 12.9716, "lon": 77.5946})
    to_coords   = Config.CITY_COORDS.get(to_city, {"lat": 12.9716, "lon": 77.5946})

    return jsonify({
        "from_city":     from_city,
        "to_city":       to_city,
        "from_coords":   from_coords,
        "to_coords":     to_coords,
        "distance_km":   dist,
        "quantity_tons": qty,
        "mode":          mode,
        "trips":         breakdown["trips"],
        "capacity_ton":  breakdown["capacity_ton"],
        "fuel_cost":     breakdown["fuel_cost"],
        "loading_cost":  breakdown["loading_cost"],
        "toll_cost":     breakdown["toll_cost"],
        "driver_cost":   breakdown["driver_cost"],
        "total_cost":    breakdown["total"],
    })


@app.route("/api/weather")
def api_weather():
    """
    JSON API: Get weather forecast for a city (enhanced with OpenWeatherMap).
    Query param: city
    Returns: { rain_probability, max_temp, description, icon, humidity, wind_speed, alerts, source }
    """
    city = request.args.get("city", "Bengaluru")
    return jsonify(get_openweather_forecast(city))


@app.route("/api/new_prices")
def api_new_prices():
    """
    JSON API: Polling endpoint for real-time price alerts on the farmer dashboard.
    Query param: after_id
    """
    after_id = int(request.args.get("after_id", 0))
    # Get all new price entries
    new_entries = PriceEntry.query.filter(PriceEntry.id > after_id).order_by(PriceEntry.id.asc()).all()
    
    results = []
    for p in new_entries:
        agent = MandiAgent.query.get(p.mandi_agent_id)
        agent_name = agent.name if agent else "A retailer"
        mandi_name = agent.mandi if agent else ""
        results.append({
            "id": p.id,
            "crop_name": p.crop_name,
            "price": p.price,
            "agent": f"{agent_name} ({mandi_name})",
            "quantity": p.quantity_required
        })
        
    return jsonify({"prices": results})


# =============================================================
# ===  NEW API ROUTES — MAPS & GEOLOCATION  ===================
# =============================================================

@app.route("/api/map_data")
def api_map_data():
    """
    JSON API: Return all coordinates for Leaflet map rendering.
    If farmer is logged in, includes farmer's location + mandi markers.
    If a crop_id is provided, includes OSRM routes to each mandi.
    Query params: crop_id (optional)
    """
    data = {
        "cities":     [],
        "mandis":     [],
        "farmer":     None,
        "routes":     [],
        "disruptions": []
    }

    # All city markers
    for city, coords in Config.CITY_COORDS.items():
        data["cities"].append({
            "name": city,
            "lat":  coords["lat"],
            "lon":  coords["lon"],
        })

    # All mandi markers
    for mandi, coords in Config.MANDI_COORDS.items():
        data["mandis"].append({
            "name": mandi,
            "lat":  coords["lat"],
            "lon":  coords["lon"],
        })

    # Farmer location (if logged in)
    if session.get("role") == "farmer":
        farmer = Farmer.query.get(session.get("farmer_id"))
        if farmer:
            farmer_coords = Config.CITY_COORDS.get(farmer.district)
            if farmer_coords:
                data["farmer"] = {
                    "name":     farmer.name,
                    "district": farmer.district,
                    "village":  farmer.village,
                    "lat":      farmer_coords["lat"],
                    "lon":      farmer_coords["lon"],
                }

    # Active disruptions for map overlay
    disruptions = Disruption.query.filter_by(active_flag=True).all()
    for d in disruptions:
        # Parse route robustly (handles '→', '->', '-') to get coordinates
        route_clean = d.route.replace("->", "→").replace("-", "→").replace("→", "→")
        parts = route_clean.split("→")
        if len(parts) == 2:
            city_a = parts[0].strip()
            city_b = parts[1].strip()
            coords_a = Config.CITY_COORDS.get(city_a)
            coords_b = Config.CITY_COORDS.get(city_b)
            if coords_a and coords_b:
                data["disruptions"].append({
                    "route":       d.route,
                    "type":        d.type,
                    "description": d.description,
                    "from_lat":    coords_a["lat"],
                    "from_lon":    coords_a["lon"],
                    "to_lat":      coords_b["lat"],
                    "to_lon":      coords_b["lon"],
                })

    return jsonify(data)


@app.route("/api/osrm_route")
def api_osrm_route():
    """
    JSON API: Get OSRM driving route between two points.
    Query params: from_city, to_city  OR  from_lat, from_lon, to_lat, to_lon
    Returns: { distance_km, duration_min, geometry: [[lat,lon],...] }
    """
    # Support both city names and raw coordinates
    from_city = request.args.get("from_city")
    to_city   = request.args.get("to_city")

    if from_city and to_city:
        coords_a = Config.CITY_COORDS.get(from_city)
        coords_b = Config.CITY_COORDS.get(to_city)
        if not coords_a or not coords_b:
            return jsonify({"error": "Unknown city"}), 400
        origin_lat, origin_lon = coords_a["lat"], coords_a["lon"]
        dest_lat,   dest_lon   = coords_b["lat"], coords_b["lon"]
    else:
        origin_lat = float(request.args.get("from_lat", 0))
        origin_lon = float(request.args.get("from_lon", 0))
        dest_lat   = float(request.args.get("to_lat", 0))
        dest_lon   = float(request.args.get("to_lon", 0))

    result = get_osrm_route(origin_lon, origin_lat, dest_lon, dest_lat)
    return jsonify(result)


@app.route("/api/nearby_facilities")
def api_nearby_facilities():
    """
    JSON API: Find nearby cold storages, petrol pumps, warehouses using Overpass.
    Query params: lat, lon, radius (optional, metres)
    Returns: [{ name, type, lat, lon }, ...]
    """
    lat    = float(request.args.get("lat", 13.1368))
    lon    = float(request.args.get("lon", 78.1294))
    radius = int(request.args.get("radius", Config.OVERPASS_SEARCH_RADIUS_M))

    facilities = get_nearby_facilities(lat, lon, radius)
    return jsonify(facilities)


@app.route("/api/geocode")
def api_geocode():
    """
    JSON API: Geocode a place name to lat/lon using Nominatim.
    Query param: q (place name)
    Returns: { lat, lon, display_name }
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    result = geocode_location(query)
    if result:
        return jsonify(result)
    return jsonify({"error": f"Could not geocode '{query}'"}), 404


# =============================================================
# ===  LOGOUT  ===============================================
# =============================================================

@app.route("/logout")
def logout():
    """Clear session and redirect to landing page."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# =============================================================
# ===  APP ENTRY POINT  ======================================
# =============================================================

if __name__ == "__main__":
    with app.app_context():
        # Create all tables on first run
        db.create_all()
        # Load distance matrix CSV into memory
        load_distance_matrix()
        print("=" * 50)
        print("  KSHETRA Flask App Starting...")
        print("  Database: kshetra.db (SQLite)")
        print("  Run seed_db.py first for demo data")
        print("  URL: http://127.0.0.1:5000")
        print("=" * 50)

    # Load distance matrix for all requests (outside app context block)
    load_distance_matrix()
    app.run(debug=True, port=5000)
