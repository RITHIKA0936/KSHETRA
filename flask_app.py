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
from models import db, Farmer, Crop, MandiAgent, PriceEntry, Disruption, PreBooking
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
        resp = requests.get(Config.OPEN_METEO_BASE_URL, params=params, timeout=5)
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
    Calculate transport cost based on distance, quantity and transport mode.
    Rate (₹/km/ton) is fetched from Config.TRANSPORT_RATES.
    """
    rate = Config.TRANSPORT_RATES.get(mode, 18)
    return round(distance_km * quantity_tons * rate, 2)


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
    """
    # Fetch all mandi agents
    agents  = MandiAgent.query.all()
    results = []

    # Active disruptions (used to penalise routes)
    disruptions = Disruption.query.filter_by(active_flag=True).all()
    disrupted_routes = [d.route.lower() for d in disruptions]

    for agent in agents:
        mandi_location = agent.location   # city name

        # 1. Get mandi price for this crop (last posted by this agent)
        entry = (PriceEntry.query
                 .filter_by(mandi_agent_id=agent.id, crop_name=crop.name)
                 .order_by(PriceEntry.date.desc())
                 .first())

        if entry:
            mandi_price = entry.price
        else:
            # Fallback to Agmarknet government price
            gov_prices  = get_agmarknet_price(crop.name)
            mandi_price = gov_prices[0]["price"] if gov_prices else 10000

        # 2. Distance & transport cost
        distance = get_distance(farmer.district, mandi_location)
        transport_cost = calculate_transport_cost(distance, crop.quantity, "Truck")

        # 3. Net profit per ton
        net_profit = (mandi_price - farmer.cost_of_production) * crop.quantity - transport_cost

        # 4. Weather penalty
        weather    = get_weather_forecast(mandi_location)
        rain_prob  = weather["rain_probability"]
        if rain_prob > 60:
            net_profit *= 0.90   # −10% for high rain risk

        # 5. Disruption penalty
        route_key = f"{farmer.district.lower()} → {mandi_location.lower()}"
        route_key2 = f"{mandi_location.lower()} → {farmer.district.lower()}"
        is_disrupted = any(route_key in r or route_key2 in r for r in disrupted_routes)
        if is_disrupted:
            net_profit *= 0.80   # −20% for active disruption

        results.append({
            "agent":          agent,
            "mandi":          agent.mandi,
            "location":       mandi_location,
            "mandi_price":    mandi_price,
            "distance_km":    distance,
            "transport_cost": transport_cost,
            "net_profit":     round(net_profit, 2),
            "rain_prob":      rain_prob,
            "weather_desc":   weather["description"],
            "is_disrupted":   is_disrupted,
        })

    # Sort by net profit descending
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
    crops       = Crop.query.filter_by(farmer_id=farmer.id).all()
    disruptions = Disruption.query.filter_by(active_flag=True).all()

    # NDVI crop health for farmer's district
    ndvi_data   = get_agro_ndvi(farmer.district)

    # Pending pre-bookings for this farmer
    bookings    = PreBooking.query.filter_by(farmer_id=farmer.id).order_by(
                      PreBooking.created_at.desc()).limit(5).all()

    return render_template(
        "farmer_dashboard.html",
        farmer=farmer,
        crops=crops,
        disruptions=disruptions,
        ndvi=ndvi_data,
        bookings=bookings
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

    return render_template(
        "recommend.html",
        farmer=farmer,
        crop=crop,
        crops=crops,
        recommendations=recommendations
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
    Mandi Agent's dashboard:
    - Recent prices posted by this agent
    - Pre-bookings / supply pipeline from farmers
    - Active disruptions
    """
    if session.get("role") != "mandi":
        flash("Please login as a mandi agent.", "warning")
        return redirect(url_for("login_mandi"))

    agent       = MandiAgent.query.get(session["agent_id"])
    # Recent prices (last 7 days) posted by this agent
    since       = date.today() - timedelta(days=7)
    prices      = (PriceEntry.query
                   .filter_by(mandi_agent_id=agent.id)
                   .filter(PriceEntry.date >= since)
                   .order_by(PriceEntry.date.desc())
                   .all())

    # Supply pipeline: pending pre-bookings directed at this agent
    supply      = PreBooking.query.filter_by(
                      mandi_agent_id=agent.id, status="Pending").all()

    disruptions = Disruption.query.filter_by(active_flag=True).all()

    return render_template(
        "mandi_dashboard.html",
        agent=agent,
        prices=prices,
        supply=supply,
        disruptions=disruptions
    )


@app.route("/post_price", methods=["POST"])
def post_price():
    """
    POST: Mandi agent posts today's price for a specific crop.
    Form fields: crop_name, price
    Looks up any existing crop with that name, or creates a reference entry.
    """
    if session.get("role") != "mandi":
        return redirect(url_for("login_mandi"))

    crop_name = request.form.get("crop_name", "").strip().title()
    price_val = float(request.form.get("price", 0))

    if not crop_name or price_val <= 0:
        flash("Please enter valid crop name and price.", "danger")
        return redirect(url_for("mandi_dashboard"))

    # Find first crop with this name in the DB (any farmer's crop)
    crop = Crop.query.filter(Crop.name.ilike(crop_name)).first()
    crop_id = crop.id if crop else None

    entry = PriceEntry(
        crop_id=crop_id,          # may be None if no farmer has added it yet
        mandi_agent_id=session["agent_id"],
        crop_name=crop_name,
        price=price_val,
        date=date.today()
    )
    db.session.add(entry)
    db.session.commit()
    flash(f"Price posted: ₹{price_val:,.0f}/ton for {crop_name}", "success")
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
# ===  ROUTES — TRANSPORT COST CALCULATOR (API)  =============
# =============================================================

@app.route("/api/transport_cost")
def api_transport_cost():
    """
    JSON API: Calculate transport cost.
    Query params: from_city, to_city, quantity_tons, mode
    Returns: { distance_km, rate, cost }
    """
    from_city = request.args.get("from_city", "Kolar")
    to_city   = request.args.get("to_city",   "Bengaluru")
    qty       = float(request.args.get("quantity_tons", 1))
    mode      = request.args.get("mode", "Truck")

    dist      = get_distance(from_city, to_city)
    cost      = calculate_transport_cost(dist, qty, mode)
    rate      = Config.TRANSPORT_RATES.get(mode, 18)

    return jsonify({
        "from_city":    from_city,
        "to_city":      to_city,
        "distance_km":  dist,
        "quantity_tons": qty,
        "mode":         mode,
        "rate_per_km_ton": rate,
        "total_cost":   cost
    })


@app.route("/api/weather")
def api_weather():
    """
    JSON API: Get weather forecast for a city.
    Query param: city
    Returns: { rain_probability, max_temp, description }
    """
    city = request.args.get("city", "Bengaluru")
    return jsonify(get_weather_forecast(city))


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
