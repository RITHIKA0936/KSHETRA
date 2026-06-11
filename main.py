from optimization.crop_recommendation import recommend_crop
from optimization.mandi_selection import select_best_mandi
from optimization.transportation import optimize_transport
from optimization.vehicle_assignment import assign_vehicles

from simulation.weather_disruption import weather_effect
from simulation.festival_effect import increase_festival_demand
from simulation.crop_failure import crop_failure_effect

from reports.cost_report import generate_cost_report
from reports.profit_report import generate_profit_report
from reports.comparison_report import compare_scenarios
from reports.excel_report import generate_excel_report


def main():

    print("\n========== KSHETRA 🌱 SMART AGRICULTURAL SYSTEM ==========\n")

    # ==================================================
    # MODULE 1: FARMER CROP RECOMMENDATION
    # ==================================================

    farmer_location = "Kolar"
    land = 10

    possible_crops = [
        "Tomato",
        "Carrot",
        "Marigold"
    ]

    crop_results, best_crop = recommend_crop(
        land,
        possible_crops
    )

    print("🌱 FARMER CROP ANALYSIS")
    print(crop_results)

    print("\nBest Crop:")
    print(best_crop)


    # ==================================================
    # MODULE 2: MANDI SELECTION
    # ==================================================

    selected_crop = best_crop["Crop"]
    quantity = best_crop["Production (tons)"]

    mandi_results, best_mandi = select_best_mandi(
        selected_crop,
        quantity,
        farmer_location
    )

    print("\n🏪 MANDI ANALYSIS")
    print(mandi_results)

    print("\nBest Mandi:")
    print(best_mandi)


    # ==================================================
    # MODULE 3: TRANSPORTATION OPTIMIZATION
    # ==================================================

    transport_plan, transport_cost = optimize_transport()

    print("\n🚚 TRANSPORTATION PLAN")
    print(transport_plan)

    print("\nTotal Transportation Cost: ₹", transport_cost)


    # ==================================================
    # MODULE 4: VEHICLE ASSIGNMENT
    # ==================================================

    vehicle_plan = assign_vehicles(transport_plan)

    print("\n🚛 VEHICLE ASSIGNMENT")
    print(vehicle_plan)


    # ==================================================
    # MODULE 5: DISRUPTION SIMULATION
    # ==================================================

    rain_cost = weather_effect(
        transport_cost,
        severity=3
    )

    festival_demand = increase_festival_demand(
        100,
        "Marigold"
    )

    remaining_supply = crop_failure_effect(
        300,
        40
    )

    print("\n🌧️ WEATHER SIMULATION")
    print("Heavy Rain Transportation Cost: ₹", rain_cost)

    print("\n🎉 FESTIVAL SIMULATION")
    print("Marigold Demand After Festival:", festival_demand, "tons")

    print("\n🍅 CROP FAILURE SIMULATION")
    print("Remaining Supply:", remaining_supply, "tons")


    # ==================================================
    # MODULE 6: REPORT GENERATION
    # ==================================================

    cost_report = generate_cost_report(
        transport_cost,
        vehicle_plan
    )

    profit_report = generate_profit_report(
        selected_crop,
        quantity,
        best_mandi["Mandi"],
        best_mandi["Net Profit (₹)"]
    )

    scenario_report = compare_scenarios()

    print("\n📊 COST REPORT")
    print(cost_report)

    print("\n💰 PROFIT REPORT")
    print(profit_report)

    print("\n📈 SCENARIO COMPARISON")
    print(scenario_report)


    # ==================================================
    # MODULE 7: EXCEL EXPORT
    # ==================================================

    final_summary = {
        "Recommended Crop": selected_crop,
        "Production (tons)": quantity,
        "Best Mandi": best_mandi["Mandi"],
        "Expected Profit (₹)": best_mandi["Net Profit (₹)"],
        "Transportation Cost (₹)": transport_cost
    }

    generate_excel_report(
        crop_results,
        mandi_results,
        transport_plan,
        vehicle_plan,
        scenario_report,
        final_summary
    )


    # ==================================================
    # FINAL KSHETRA DECISION
    # ==================================================

    print("\n========== FINAL KSHETRA DECISION ==========")

    print("Recommended Crop:", selected_crop)
    print("Production:", quantity, "tons")
    print("Best Mandi:", best_mandi["Mandi"])
    print("Expected Profit: ₹", best_mandi["Net Profit (₹)"])
    print("Transportation Cost: ₹", transport_cost)

    print("\n🌱 KSHETRA analysis completed successfully!")


if __name__ == "__main__":
    main()