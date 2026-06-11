def generate_cost_report(transport_cost, vehicle_plan):

    total_trips = vehicle_plan["Number of Trips"].sum()

    report = {
        "Transportation Cost (₹)": transport_cost,
        "Total Vehicle Trips": total_trips
    }

    return report