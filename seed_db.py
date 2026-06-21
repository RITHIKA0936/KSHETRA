# =============================================================
# seed_db.py — Database Seeder for KSHETRA
# =============================================================
# Populates kshetra.db with demo farmers, mandi agents,
# crops, price entries, and disruptions so the app is
# immediately usable for testing.
#
# Run once:  python seed_db.py
# =============================================================

from flask_app import app
from models    import db, Farmer, Crop, MandiAgent, PriceEntry, Disruption, PreBooking
from datetime  import date, timedelta
import random

# ------------------------------------------------------------------
# Seed data definitions
# ------------------------------------------------------------------

FARMERS_SEED = [
    # ── Demo accounts (always available) ──────────────────────────────
    {"name": "Demo Farmer",   "mobile": "9000000001", "village": "Malur",     "district": "Kolar",    "username": "demofarmer",  "password": "1234",     "cost_of_production": 5000},
    # ── Sample farmers ─────────────────────────────────────────────────
    {"name": "Raju Patil",    "mobile": "9876543210", "village": "Malur",     "district": "Kolar",    "username": "raju",        "password": "raju123",  "cost_of_production": 5000},
    {"name": "Lakshmi Devi",  "mobile": "9845001122", "village": "Sidlaghatta","district": "Kolar",    "username": "lakshmi",    "password": "lak123",   "cost_of_production": 6000},
    {"name": "Venkatesh GK",  "mobile": "9731234567", "village": "Tumkur",    "district": "Tumakuru", "username": "venkat",      "password": "ven123",   "cost_of_production": 4500},
    {"name": "Sunita Reddy",  "mobile": "9632587410", "village": "Mandya",    "district": "Mandya",   "username": "sunita",      "password": "sun123",   "cost_of_production": 7000},
    {"name": "Mahesh Kumar",  "mobile": "8765432109", "village": "Hassan",    "district": "Hassan",   "username": "mahesh",      "password": "mah123",   "cost_of_production": 5500},
]

AGENTS_SEED = [
    # ── Demo accounts (always available) ──────────────────────────────
    {"name": "Demo Retailer", "mandi": "Kolar Mandi", "location": "Kolar",    "contact": "9000000002", "username": "demoretailer", "password": "1234"},
    # ── Sample agents ──────────────────────────────────────────────────
    {"name": "Ravi Kumar",     "mandi": "Kolar Mandi",           "location": "Kolar",    "contact": "9900112233", "username": "ravi_kolar",   "password": "kolar123"},
    {"name": "Suman Nair",     "mandi": "KR Market",             "location": "Bengaluru","contact": "9900223344", "username": "suman_kr",     "password": "kr123"},
    {"name": "Arjun Gowda",    "mandi": "Yeshwanthpur Market",   "location": "Bengaluru","contact": "9900334455", "username": "arjun_yesh",   "password": "yesh123"},
    {"name": "Kavitha Bai",    "mandi": "Mysuru Mandi",          "location": "Mysuru",   "contact": "9900445566", "username": "kavitha_mys",  "password": "mys123"},
    {"name": "Prakash Rao",    "mandi": "Tumakuru Mandi",        "location": "Tumakuru", "contact": "9900556677", "username": "prakash_tum",  "password": "tum123"},
    {"name": "Bhavani Shetty", "mandi": "Mandya Mandi",          "location": "Mandya",   "contact": "9900667788", "username": "bhavani_mdy",  "password": "mdy123"},
    {"name": "Nagaraj MS",     "mandi": "Hassan Mandi",          "location": "Hassan",   "contact": "9900778899", "username": "nagaraj_hsn",  "password": "hsn123"},
]

CROPS_SEED = [
    # (farmer_index, crop_name, quantity_tons, shelf_life_days)
    (0, "Tomato",   8.0,  5),
    (0, "Carrot",   3.0, 20),
    (1, "Rose",     1.5,  3),
    (1, "Marigold", 2.0,  2),
    (2, "Ragi",     5.0, 180),
    (2, "Maize",    4.0, 180),
    (3, "Paddy",   10.0, 365),
    (3, "Onion",    6.0,  30),
    (4, "Potato",   7.0,  60),
    (4, "Beans",    2.5,   4),
]

# Base prices (₹/ton) per mandi per crop for seeding 30 days of history
BASE_PRICES = {
    ("Kolar Mandi",         "Tomato"):   12500,
    ("Kolar Mandi",         "Carrot"):   17500,
    ("Kolar Mandi",         "Rose"):     58000,
    ("Kolar Mandi",         "Marigold"): 24500,
    ("KR Market",           "Tomato"):   11800,
    ("KR Market",           "Onion"):    15200,
    ("KR Market",           "Marigold"): 25800,
    ("KR Market",           "Potato"):   18200,
    ("Yeshwanthpur Market", "Tomato"):   12200,
    ("Yeshwanthpur Market", "Ragi"):     29500,
    ("Yeshwanthpur Market", "Maize"):    18100,
    ("Mysuru Mandi",        "Carrot"):   18200,
    ("Mysuru Mandi",        "Rose"):     60000,
    ("Mysuru Mandi",        "Paddy"):    21500,
    ("Tumakuru Mandi",      "Ragi"):     30000,
    ("Tumakuru Mandi",      "Maize"):    18500,
    ("Tumakuru Mandi",      "Potato"):   17000,
    ("Mandya Mandi",        "Paddy"):    22000,
    ("Mandya Mandi",        "Onion"):    14500,
    ("Hassan Mandi",        "Beans"):    26000,
    ("Hassan Mandi",        "Potato"):   17500,
    ("Hassan Mandi",        "Ragi"):     29000,
}

DISRUPTIONS_SEED = [
    {
        "route":       "Kolar → Bengaluru",
        "type":        "Road Closure",
        "description": "NH-75 highway maintenance work underway",
        "start_date":  date.today() - timedelta(days=2),
        "end_date":    date.today() + timedelta(days=3),
        "active_flag": True
    },
    {
        "route":       "Mandya → Mysuru",
        "type":        "Festival",
        "description": "Dasara festival — heavy traffic congestion expected",
        "start_date":  date.today() - timedelta(days=1),
        "end_date":    date.today() + timedelta(days=2),
        "active_flag": True
    },
    {
        "route":       "Tumakuru → Hassan",
        "type":        "Flood",
        "description": "River overflow affecting NH-48 near Tiptur",
        "start_date":  date.today() - timedelta(days=5),
        "end_date":    date.today() - timedelta(days=1),
        "active_flag": False   # already resolved
    },
]


# ------------------------------------------------------------------
# Seeder function
# ------------------------------------------------------------------
def ensure_demo_accounts():
    """Always upsert the two demo accounts regardless of seed state."""
    # Demo farmer
    df = Farmer.query.filter_by(username="demofarmer").first()
    if not df:
        df = Farmer(
            name="Demo Farmer", mobile="9000000001",
            village="Malur", district="Kolar",
            username="demofarmer", password="1234",
            cost_of_production=5000
        )
        db.session.add(df)
        db.session.commit()
        print("  [OK] demofarmer account created")

        # Give demo farmer some crops so the dashboard is populated
        for crop_name, qty, shelf in [("Tomato", 8.0, 5), ("Carrot", 3.0, 20)]:
            db.session.add(Crop(name=crop_name, quantity=qty,
                                shelf_life_days=shelf, farmer_id=df.id))
        db.session.commit()
        print("  [OK] demo farmer crops added")
    else:
        # Ensure password is correct even if account existed before
        df.password = "1234"
        db.session.commit()

    # Demo retailer (mandi agent)
    dr = MandiAgent.query.filter_by(username="demoretailer").first()
    if not dr:
        dr = MandiAgent(
            name="Demo Retailer", mandi="Kolar Mandi",
            location="Kolar", contact="9000000002",
            username="demoretailer", password="1234"
        )
        db.session.add(dr)
        db.session.commit()
        print("  [OK] demoretailer account created")
    else:
        dr.password = "1234"
        db.session.commit()


def seed():
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Always ensure demo accounts exist (even if DB was already seeded)
        ensure_demo_accounts()

        # Skip full seed if data already exists
        if Farmer.query.count() > 1:   # >1 because demofarmer was just added
            print("Database already seeded. Skipping full seed.")
            return

        print("Seeding database...")

        # ---- Farmers ----
        farmers = []
        for f in FARMERS_SEED:
            farmer = Farmer(**f)
            db.session.add(farmer)
            farmers.append(farmer)
        db.session.commit()
        print(f"  [OK] {len(farmers)} farmers added")
        db.session.commit()

        # ---- Mandi Agents ----
        agents = []
        for a in AGENTS_SEED:
            agent = MandiAgent(**a)
            db.session.add(agent)
            agents.append(agent)
        db.session.commit()
        print(f"  [OK] {len(agents)} mandi agents added")

        # ---- Crops ----
        crops = []
        for (farmer_idx, crop_name, qty, shelf) in CROPS_SEED:
            crop = Crop(
                name=crop_name,
                quantity=qty,
                shelf_life_days=shelf,
                farmer_id=farmers[farmer_idx].id
            )
            db.session.add(crop)
            crops.append(crop)
        db.session.commit()
        print(f"  [OK] {len(crops)} crops added")

        # ---- Price Entries (30 days of history) ----
        price_count = 0
        for agent in agents:
            for crop in crops:
                key = (agent.mandi, crop.name)
                if key in BASE_PRICES:
                    base = BASE_PRICES[key]
                    # Generate daily prices for last 30 days with +/-5% variation
                    for days_ago in range(30, 0, -1):
                        price_date = date.today() - timedelta(days=days_ago)
                        variation  = random.uniform(-0.05, 0.05)
                        price_val  = round(base * (1 + variation), 0)
                        entry = PriceEntry(
                            crop_id=crop.id,
                            mandi_agent_id=agent.id,
                            crop_name=crop.name,
                            price=price_val,
                            date=price_date
                        )
                        db.session.add(entry)
                        price_count += 1

        db.session.commit()
        print(f"  [OK] {price_count} price entries added (30 days history)")

        # ---- Disruptions ----
        for d in DISRUPTIONS_SEED:
            disruption = Disruption(**d)
            db.session.add(disruption)
        db.session.commit()
        print(f"  [OK] {len(DISRUPTIONS_SEED)} disruptions added")

        # ---- Sample Pre-Bookings ----
        bookings = [
            PreBooking(farmer_id=farmers[0].id, mandi_agent_id=agents[1].id,
                       crop_name="Tomato",  quantity=5.0,
                       preferred_date=date.today() + timedelta(days=2), status="Pending"),
            PreBooking(farmer_id=farmers[1].id, mandi_agent_id=agents[0].id,
                       crop_name="Rose",    quantity=1.0,
                       preferred_date=date.today() + timedelta(days=1), status="Confirmed"),
            PreBooking(farmer_id=farmers[2].id, mandi_agent_id=agents[4].id,
                       crop_name="Ragi",    quantity=4.0,
                       preferred_date=date.today() + timedelta(days=3), status="Pending"),
        ]
        for b in bookings:
            db.session.add(b)
        db.session.commit()
        print(f"  [OK] {len(bookings)} pre-bookings added")

        print("\nDatabase seeding complete!")
        print("\nDemo Login Credentials:")
        print("  ┌─────────────────────────────────────────────┐")
        print("  │  Farmer portal  →  demofarmer  / 1234       │")
        print("  │  Retailer portal→  demoretailer / 1234      │")
        print("  └─────────────────────────────────────────────┘")


if __name__ == "__main__":
    seed()
