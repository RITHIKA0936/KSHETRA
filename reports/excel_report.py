import pandas as pd


def generate_excel_report(
    crop_analysis,
    mandi_analysis,
    transport_plan,
    vehicle_plan,
    scenario_report,
    final_summary
):

    file_name = "output/final_kshetra_report.xlsx"

    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:

        # Crop Analysis Sheet
        crop_analysis.to_excel(
            writer,
            sheet_name="Crop Analysis",
            index=False
        )

        # Mandi Analysis Sheet
        mandi_analysis.to_excel(
            writer,
            sheet_name="Mandi Analysis",
            index=False
        )

        # Transportation Sheet
        transport_plan.to_excel(
            writer,
            sheet_name="Transportation",
            index=False
        )

        # Vehicle Assignment Sheet
        vehicle_plan.to_excel(
            writer,
            sheet_name="Vehicle Plan",
            index=False
        )

        # Scenario Comparison Sheet
        scenario_report.to_excel(
            writer,
            sheet_name="Scenario Comparison",
            index=False
        )

        # Final Summary Sheet
        summary_df = pd.DataFrame(
            [final_summary]
        )

        summary_df.to_excel(
            writer,
            sheet_name="Final Summary",
            index=False
        )

    print("\n📄 Excel Report Generated Successfully!")
    print("Saved at: output/final_kshetra_report.xlsx")