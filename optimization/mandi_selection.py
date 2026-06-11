import pandas as pd


def select_best_mandi(crop, quantity, farmer_location):
    
    # Mandi selling prices (₹ per ton)
    mandi_prices = {
        "Kolar": 12000,
        "Bengaluru": 14000,
        "Mysuru": 13500
    }

    # Load distance data
    distances = pd.read_csv("data/distance_matrix.csv")

    results = []

    for mandi, price in mandi_prices.items():

        # Same location → zero distance
        if mandi == farmer_location:
            distance = 0

        else:
            route = distances[
                ((distances["From"] == farmer_location) &
                 (distances["To"] == mandi))
                |
                ((distances["From"] == mandi) &
                 (distances["To"] == farmer_location))
            ]

            if route.empty:
                print(f"No distance data found for {mandi}")
                continue

            distance = route["Distance_KM"].values[0]

        # Calculations
        revenue = quantity * price

        transport_cost = distance * quantity * 10

        profit = revenue - transport_cost

        results.append({
            "Mandi": mandi,
            "Distance (KM)": distance,
            "Selling Price (₹/Ton)": price,
            "Revenue (₹)": revenue,
            "Transportation Cost (₹)": transport_cost,
            "Net Profit (₹)": profit
        })

    # Create comparison table
    result_df = pd.DataFrame(results)

    # Find best mandi
    best_mandi = result_df.loc[
        result_df["Net Profit (₹)"].idxmax()
    ]

    return result_df, best_mandi