import pandas as pd


def compare_scenarios():

    data = [
        {
            "Scenario": "Normal",
            "Transportation Cost": 250000,
            "Demand Change": "No",
            "Supply Change": "No"
        },
        {
            "Scenario": "Heavy Rain",
            "Transportation Cost": 320000,
            "Demand Change": "No",
            "Supply Change": "No"
        },
        {
            "Scenario": "Festival",
            "Transportation Cost": 380000,
            "Demand Change": "Increased",
            "Supply Change": "No"
        },
        {
            "Scenario": "Crop Disease",
            "Transportation Cost": 420000,
            "Demand Change": "No",
            "Supply Change": "Reduced"
        }
    ]

    return pd.DataFrame(data)