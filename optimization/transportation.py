import pandas as pd
from pulp import *


def optimize_transport():

    # Supply availability (tons)
    supply = {
        "Kolar": 300,
        "Bengaluru": 250,
        "Tumakuru": 200
    }

    # City demand (tons)
    demand = {
        "Mysuru": 180,
        "Mandya": 150,
        "Hassan": 120
    }

    # Load distance data
    distances = pd.read_csv("data/distance_matrix.csv")

    # Transportation cost per ton per km
    cost_per_km = 10


    # Create cost dictionary
    cost = {}

    for source in supply:
        for destination in demand:

            route = distances[
                ((distances["From"] == source) &
                 (distances["To"] == destination)) |
                ((distances["From"] == destination) &
                 (distances["To"] == source))
            ]

            if not route.empty:
                distance = route["Distance_KM"].values[0]
                cost[(source, destination)] = distance * cost_per_km

            else:
                # Very high cost if route missing
                cost[(source, destination)] = 999999


    # Create Linear Programming problem
    model = LpProblem(
        "KSHETRA_Transportation_Optimization",
        LpMinimize
    )


    # Decision variables
    routes = LpVariable.dicts(
        "Transport",
        cost.keys(),
        lowBound=0,
        cat="Continuous"
    )


    # Objective function
    model += lpSum(
        routes[i, j] * cost[i, j]
        for (i, j) in cost
    )


    # Supply constraints
    for source in supply:
        model += (
            lpSum(
                routes[source, city]
                for city in demand
            ) <= supply[source]
        )


    # Demand constraints
    for city in demand:
        model += (
            lpSum(
                routes[source, city]
                for source in supply
            ) >= demand[city]
        )


    # Solve the model
    model.solve()


    # Store results
    results = []

    for (source, city), variable in routes.items():

        quantity = variable.value()

        if quantity > 0:

            results.append({
                "From": source,
                "To": city,
                "Quantity (tons)": quantity,
                "Cost per Ton (₹)": cost[(source, city)],
                "Total Cost (₹)": quantity * cost[(source, city)]
            })


    result_df = pd.DataFrame(results)


    total_cost = result_df["Total Cost (₹)"].sum()


    return result_df, total_cost