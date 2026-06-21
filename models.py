# =============================================================
# models.py — SQLAlchemy Database Models for KSHETRA
# =============================================================
# Run `python flask_app.py` after pip install flask flask_sqlalchemy
# All models are stored in kshetra.db (SQLite)

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Create the SQLAlchemy instance (imported and initialised in flask_app.py)
db = SQLAlchemy()


# -------------------------------------------------------------
# Farmer Model
# Represents a registered farmer on the platform
# -------------------------------------------------------------
class Farmer(db.Model):
    __tablename__ = "farmer"

    id                 = db.Column(db.Integer, primary_key=True)
    name               = db.Column(db.String(120), nullable=False)
    mobile             = db.Column(db.String(15),  nullable=False)
    village            = db.Column(db.String(100), nullable=False)
    district           = db.Column(db.String(100), nullable=False)
    username           = db.Column(db.String(80),  unique=True, nullable=False)
    password           = db.Column(db.String(200), nullable=False)          # stored as plain text for demo; use hashing in prod
    cost_of_production = db.Column(db.Float, default=0.0)                   # ₹ per ton

    # One farmer → many crops
    crops = db.relationship("Crop", backref="farmer", lazy=True)

    def __repr__(self):
        return f"<Farmer {self.username}>"


# -------------------------------------------------------------
# Crop Model
# Each crop entry belongs to a specific farmer
# -------------------------------------------------------------
class Crop(db.Model):
    __tablename__ = "crop"

    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(100), nullable=False)
    quantity       = db.Column(db.Float, nullable=False)                    # in tons
    shelf_life_days = db.Column(db.Integer, default=7)
    farmer_id      = db.Column(db.Integer, db.ForeignKey("farmer.id"), nullable=False)

    # One crop → many price entries (mandi prices posted for this crop)
    price_entries = db.relationship("PriceEntry", backref="crop", lazy=True)

    def __repr__(self):
        return f"<Crop {self.name} ({self.quantity}t)>"


# -------------------------------------------------------------
# MandiAgent Model
# Represents a market / mandi agent who posts daily crop prices
# -------------------------------------------------------------
class MandiAgent(db.Model):
    __tablename__ = "mandi_agent"

    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(120), nullable=False)
    mandi    = db.Column(db.String(150), nullable=False)                    # mandi name
    location = db.Column(db.String(100), nullable=False)                   # city/district
    contact  = db.Column(db.String(15),  nullable=False)
    username = db.Column(db.String(80),  unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # One agent → many price entries
    price_entries = db.relationship("PriceEntry", backref="agent", lazy=True)

    def __repr__(self):
        return f"<MandiAgent {self.mandi}>"


# -------------------------------------------------------------
# PriceEntry Model
# Stores daily crop prices posted by mandi agents
# -------------------------------------------------------------
class PriceEntry(db.Model):
    __tablename__ = "price_entry"

    id             = db.Column(db.Integer, primary_key=True)
    crop_id        = db.Column(db.Integer, db.ForeignKey("crop.id"),        nullable=True)
    mandi_agent_id = db.Column(db.Integer, db.ForeignKey("mandi_agent.id"), nullable=False)
    crop_name      = db.Column(db.String(100), nullable=False)
    price          = db.Column(db.Float,   nullable=False)
    quantity_required = db.Column(db.Float, nullable=True)              # tons the mandi can accept
    date           = db.Column(db.Date,    default=datetime.utcnow().date)

    def __repr__(self):
        return f"<PriceEntry {self.crop_name}@{self.price} on {self.date}>"


# -------------------------------------------------------------
# Disruption Model
# Flags routes as disrupted (strike, flood, closure, etc.)
# Can be created by mandi agents or admin
# -------------------------------------------------------------
class Disruption(db.Model):
    __tablename__ = "disruption"

    id          = db.Column(db.Integer, primary_key=True)
    route       = db.Column(db.String(200), nullable=False)                 # e.g. "Kolar → Bengaluru"
    type        = db.Column(db.String(80),  nullable=False)                 # Strike / Flood / Road Closure / Festival
    description = db.Column(db.String(300), default="")
    start_date  = db.Column(db.Date, nullable=False)
    end_date    = db.Column(db.Date, nullable=True)
    active_flag = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Disruption {self.type} on {self.route}>"


# -------------------------------------------------------------
# PreBooking Model
# Farmers can pre-book / express interest in selling at a mandi
# Mandi agents can view the supply pipeline
# -------------------------------------------------------------
class PreBooking(db.Model):
    __tablename__ = "pre_booking"

    id             = db.Column(db.Integer, primary_key=True)
    farmer_id      = db.Column(db.Integer, db.ForeignKey("farmer.id"),      nullable=False)
    mandi_agent_id = db.Column(db.Integer, db.ForeignKey("mandi_agent.id"), nullable=True)
    crop_name      = db.Column(db.String(100), nullable=False)
    quantity       = db.Column(db.Float, nullable=False)                    # in tons
    preferred_date = db.Column(db.Date, nullable=True)
    status         = db.Column(db.String(30), default="Pending")            # Pending / Confirmed / Cancelled
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    farmer = db.relationship("Farmer",     backref="pre_bookings")
    agent  = db.relationship("MandiAgent", backref="pre_bookings")

    def __repr__(self):
        return f"<PreBooking {self.crop_name} {self.quantity}t by Farmer#{self.farmer_id}>"


# -------------------------------------------------------------
# CropDeal Model
# Tracks the negotiation between a retailer's price entry and a farmer's crop.
# States: pending → requested → accepted / rejected_by_farmer / rejected_by_retailer
# -------------------------------------------------------------
class CropDeal(db.Model):
    __tablename__ = "crop_deal"

    id             = db.Column(db.Integer, primary_key=True)
    price_entry_id = db.Column(db.Integer, db.ForeignKey("price_entry.id"), nullable=False)
    crop_id        = db.Column(db.Integer, db.ForeignKey("crop.id"),         nullable=False)
    farmer_id      = db.Column(db.Integer, db.ForeignKey("farmer.id"),       nullable=False)
    agent_id       = db.Column(db.Integer, db.ForeignKey("mandi_agent.id"),  nullable=False)
    # Status flow: available → requested → accepted | rejected_farmer | rejected_retailer
    status         = db.Column(db.String(30), default="requested", nullable=False)
    transport_cost = db.Column(db.Float,   nullable=True)   # calculated at deal creation
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    price_entry = db.relationship("PriceEntry", backref="deals")
    crop        = db.relationship("Crop",       backref="deals")
    farmer      = db.relationship("Farmer",     backref="deals")
    agent       = db.relationship("MandiAgent", backref="deals")

    def __repr__(self):
        return f"<CropDeal {self.status} crop#{self.crop_id} price#{self.price_entry_id}>"
