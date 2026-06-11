def generate_profit_report(crop, production, mandi, profit):

    report = {
        "Recommended Crop": crop,
        "Expected Production (tons)": production,
        "Selected Mandi": mandi,
        "Expected Profit (₹)": profit
    }

    return report