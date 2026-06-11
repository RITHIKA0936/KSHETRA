import pandas as pd


def recommend_crop(land_acres, possible_crops):
    
    # Load crop database
    crops = pd.read_csv("data/crops.csv")

    results = []

    for crop in possible_crops:

        crop_data = crops[crops["Crop"] == crop]

        if crop_data.empty:
            print(f"{crop} data not found")
            continue

        yield_per_acre = crop_data["Expected_Yield_Ton_Per_Acre"].values[0]
        price = crop_data["Average_Price_Per_Ton"].values[0]

        production = land_acres * yield_per_acre

        revenue = production * price

        results.append({
            "Crop": crop,
            "Production (tons)": production,
            "Expected Revenue (₹)": revenue
        })


    result_df = pd.DataFrame(results)

    best_crop = result_df.loc[
        result_df["Expected Revenue (₹)"].idxmax()
    ]

    return result_df, best_crop