from flask_app import app, get_distance, calculate_transport_cost
from models import db, Farmer, Crop, PriceEntry
from datetime import date, timedelta

with app.app_context():
    farmer = Farmer.query.filter_by(username='demofarmer').first()
    since = date.today() - timedelta(days=2)
    entries = PriceEntry.query.filter(
        PriceEntry.date >= since,
        PriceEntry.quantity_required != None
    ).all()

    print(f"Farmer: {farmer.name}, district={farmer.district}, cop={farmer.cost_of_production}")
    print(f"Farmer crops: {[(c.name, c.quantity) for c in farmer.crops]}")
    print(f"Entries with qty_required: {len(entries)}")
    print()

    for entry in entries:
        agent = entry.agent
        if not agent:
            print(f"  Entry {entry.id}: NO AGENT, skipping")
            continue

        matching_crop = None
        for crop in farmer.crops:
            if crop.name.lower() == entry.crop_name.lower():
                print(f"  Entry {entry.id} ({entry.crop_name}): name match found, crop qty={crop.quantity}, required={entry.quantity_required}, qty ok={crop.quantity >= entry.quantity_required}")
                if crop.quantity >= entry.quantity_required:
                    matching_crop = crop

        if not matching_crop:
            print(f"  Entry {entry.id} ({entry.crop_name}): NO matching crop with sufficient qty")
            continue

        dist = get_distance(farmer.district, agent.location)
        tc_result = calculate_transport_cost(dist, entry.quantity_required, "Truck")
        total_tc = tc_result["total"]
        farmer_price_per_ton = farmer.cost_of_production + (total_tc / entry.quantity_required)

        print(f"  Entry {entry.id} ({entry.crop_name}): dist={dist}km, tc={total_tc:.0f}, farmer_min={farmer_price_per_ton:.0f}, retailer_offers={entry.price}")
        print(f"    -> price ok (retailer >= farmer_min)? {entry.price >= farmer_price_per_ton}")
        print(f"    -> MATCH? {entry.price >= farmer_price_per_ton}")
        print()
