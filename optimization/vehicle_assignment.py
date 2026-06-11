import pandas as pd
import math


def assign_vehicles(transport_plan):

    # Load available vehicles
    vehicles = pd.read_csv("data/vehicles.csv")

    # Arrange vehicles from highest capacity to lowest
    vehicles = vehicles.sort_values(
        by="Capacity_Tons",
        ascending=False
    )

    assignments = []

    for _, route in transport_plan.iterrows():

        source = route["From"]
        destination = route["To"]
        quantity = route["Quantity (tons)"]

        remaining_quantity = quantity

        for _, vehicle in vehicles.iterrows():

            vehicle_name = vehicle["Vehicle"]
            capacity = vehicle["Capacity_Tons"]

            # Number of trips needed for this vehicle
            trips = math.floor(
                remaining_quantity / capacity
            )

            if trips > 0:

                assigned_quantity = trips * capacity

                assignments.append({
                    "From": source,
                    "To": destination,
                    "Vehicle": vehicle_name,
                    "Capacity per Trip (tons)": capacity,
                    "Number of Trips": trips,
                    "Quantity Transported": assigned_quantity
                })

                remaining_quantity -= assigned_quantity


        # If some quantity is still remaining
        if remaining_quantity > 0:

            smallest_vehicle = vehicles.iloc[-1]

            assignments.append({
                "From": source,
                "To": destination,
                "Vehicle": smallest_vehicle["Vehicle"],
                "Capacity per Trip (tons)": smallest_vehicle["Capacity_Tons"],
                "Number of Trips": 1,
                "Quantity Transported": remaining_quantity
            })

    assignment_df = pd.DataFrame(assignments)

    return assignment_df