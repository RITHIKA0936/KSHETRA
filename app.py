import streamlit as st
import pandas as pd

# -------------------------------------
# Page Configuration
# -------------------------------------

st.set_page_config(
    page_title="KSHETRA",
    page_icon="🌱",
    layout="centered"
)


# -------------------------------------
# Session Variables
# -------------------------------------

if "page" not in st.session_state:
    st.session_state.page = "welcome"


if "users" not in st.session_state:
    st.session_state.users = {}


if "farmer_name" not in st.session_state:
    st.session_state.farmer_name = ""


if "farm_data" not in st.session_state:
    st.session_state.farm_data = {}

if "crop_production" not in st.session_state:
    st.session_state.crop_production = []

if "best_crop" not in st.session_state:
    st.session_state.best_crop = {}

if "mandi_results" not in st.session_state:
    st.session_state.mandi_results = []

if "transport_results" not in st.session_state:
    st.session_state.transport_results = []

if "weather_results" not in st.session_state:
    st.session_state.weather_results = []

if "priority_results" not in st.session_state:
    st.session_state.priority_results = []

if "final_report" not in st.session_state:
    st.session_state.final_report = {}

if "smart_score" not in st.session_state:
    st.session_state.smart_score = []


# -------------------------------------
# Welcome Page
# -------------------------------------

if st.session_state.page == "welcome":

    st.title("🌱 KSHETRA")

    st.subheader(
        "Smart Agricultural Decision Support System"
    )

    st.write("---")

    st.write("""
    Welcome to KSHETRA.

    A smart platform that helps farmers make
    agricultural decisions using Operations Research,
    optimization, and supply chain analysis.
    """)


    st.write("### 👨‍🌾 Farmer Access")


    col1, col2 = st.columns(2)


    with col1:

        if st.button(
            "🔐 Farmer Login",
            use_container_width=True
        ):

            st.session_state.page = "login"

            st.rerun()


    with col2:

        if st.button(
            "📝 New Registration",
            use_container_width=True
        ):

            st.session_state.page = "register"

            st.rerun()
            # -------------------------------------
# Login Page
# -------------------------------------

elif st.session_state.page == "login":

    st.title("🔐 Farmer Login")


    username = st.text_input(
        "Username"
    )


    password = st.text_input(
        "Password",
        type="password"
    )


    if st.button(
        "Login",
        use_container_width=True
    ):


        if username in st.session_state.users:


            user = st.session_state.users[username]


            if password == user["password"]:


                st.session_state.farmer_name = user["name"]


                st.success(
                    f"Welcome {user['name']} 👨‍🌾"
                )


                st.session_state.page = "farm_details"


                st.rerun()


            else:


                st.error(
                    "Incorrect Password. Please try again."
                )


        else:


            st.warning(
                "User is not registered. Please register first."
            )


    if st.button(
        "⬅ Back",
        use_container_width=True
    ):


        st.session_state.page = "welcome"


        st.rerun()



# -------------------------------------
# Registration Page
# -------------------------------------

elif st.session_state.page == "register":


    st.title("📝 New Farmer Registration")


    name = st.text_input(
        "👨‍🌾 Farmer Name"
    )


    mobile = st.text_input(
        "📞 Mobile Number"
    )


    village = st.text_input(
        "🏡 Village Name"
    )


    district = st.selectbox(
        "📍 District",
        [
            "Kolar",
            "Bengaluru",
            "Tumakuru",
            "Mysuru",
            "Mandya",
            "Hassan"
        ]
    )


    username = st.text_input(
        "👤 Create Username"
    )


    password = st.text_input(
        "🔑 Create Password",
        type="password"
    )


    if st.button(
        "Register",
        use_container_width=True
    ):


        if (
            name and
            mobile and
            village and
            username and
            password
        ):


            if username in st.session_state.users:


                st.warning(
                    "Username already exists. Choose another username."
                )


            else:


                st.session_state.users[username] = {


                    "name": name,

                    "mobile": mobile,

                    "village": village,

                    "district": district,

                    "password": password

                }


                st.success(
                    "Registration Successful! Please go to Login."
                )


        else:


            st.error(
                "Please fill all the details."
            )


    if st.button(
        "⬅ Back",
        use_container_width=True
    ):


        st.session_state.page = "welcome"


        st.rerun()
        # -------------------------------------
# Farm Information Page
# -------------------------------------

elif st.session_state.page == "farm_details":

    st.title("🌾 Farm Information")

    st.success(
        f"Welcome {st.session_state.farmer_name} 👨‍🌾"
    )


    # Farm Location

    location = st.selectbox(
        "📍 Select Farm Location",
        [
            "Kolar",
            "Bengaluru",
            "Tumakuru",
            "Mysuru",
            "Mandya",
            "Hassan"
        ]
    )


    # Land Area

    land = st.number_input(
        "🌾 Enter Land Area (Acres)",
        min_value=1,
        max_value=500,
        value=10
    )


    # Available Crops

    crops_input = st.text_area(
        "🌱 Enter Available Crops",
        placeholder="""
Example:
Tomato
Potato
Onion
Ragi
Carrot
Marigold
""",
        height=150
    )


    # Convert user input into list

    crops = [

        crop.strip()

        for crop in crops_input.replace(
            "\n",
            ","
        ).split(",")

        if crop.strip()

    ]


    # Season Selection

    season = st.selectbox(
        "🌦️ Select Growing Season",
        [
            "Kharif",
            "Rabi",
            "Summer"
        ]
    )


    # Analyze Button

    if st.button(
        "🔍 Analyze My Farm",
        use_container_width=True
    ):


        if len(crops) == 0:


            st.warning(
                "Please enter at least one crop."
            )


        else:


            # Save farmer inputs

            st.session_state.farm_data = {

                "location": location,

                "land": land,

                "crops": crops,

                "season": season

            }


            st.success(
                "Farm details saved successfully!"
            )


            # Move to next module

            st.session_state.page = (
                "crop_recommendation"
            )


            st.rerun()
            # -------------------------------------
# Crop Recommendation Page
# -------------------------------------

elif st.session_state.page == "crop_recommendation":

    st.title("🌱 Crop Recommendation & Profit Analysis")


    farm = st.session_state.farm_data


    st.subheader("📋 Farmer Input Summary")


    st.write("📍 Location:", farm["location"])

    st.write("🌾 Land Area:", farm["land"], "Acres")

    st.write("🌱 Available Crops:", ", ".join(farm["crops"]))

    st.write("🌦️ Season:", farm["season"])


    st.write("---")


    st.subheader(
        "📊 Crop Profit Comparison"
    )


    # Crop Database
    crop_database = {

        "Tomato": {
            "production_per_acre": 15,
            "price_per_ton": 12000
        },

        "Carrot": {
            "production_per_acre": 10,
            "price_per_ton": 18000
        },

        "Marigold": {
            "production_per_acre": 6,
            "price_per_ton": 25000
        },

        "Potato": {
            "production_per_acre": 12,
            "price_per_ton": 15000
        },

        "Onion": {
            "production_per_acre": 14,
            "price_per_ton": 14000
        },

        "Ragi": {
            "production_per_acre": 3,
            "price_per_ton": 30000
        }
    }


    results = []


    for crop in farm["crops"]:


        crop_name = crop.title()


        if crop_name in crop_database:


            production = (
                farm["land"] *
                crop_database[crop_name]["production_per_acre"]
            )


            revenue = (
                production *
                crop_database[crop_name]["price_per_ton"]
            )


            results.append({

                "Crop": crop_name,

                "Production (tons)": production,

                "Selling Price ₹/Ton":
                crop_database[crop_name]["price_per_ton"],

                "Expected Revenue (₹)": revenue

            })


    # Check if crops are available in database

    if len(results) == 0:

        st.error(
            "No crop data available. Please enter crops like Tomato, Carrot, Marigold, Potato, Onion or Ragi."
        )


    else:

        st.table(results)


        # Select best crop using profit maximization

        best_crop = max(
            results,
            key=lambda x: x["Expected Revenue (₹)"]
        )


        st.success(
            f"""
🌟 Recommended Crop: {best_crop["Crop"]}

🌾 Expected Production:
{best_crop["Production (tons)"]} tons

💰 Expected Revenue:
₹ {best_crop["Expected Revenue (₹)"]}
"""
        )


        # Save best crop for next module

        st.session_state.best_crop = best_crop


        if st.button(
            "🏪 Continue to Mandi Selection",
            use_container_width=True
        ):


            st.session_state.page = "mandi_selection"


            st.rerun()
            # -------------------------------------
# Vehicle Assignment Page
# -------------------------------------

elif st.session_state.page == "vehicle_assignment":

    st.title("🚛 Vehicle Assignment System")


    st.subheader("Available Vehicles")


    vehicles = [
        {
            "Vehicle": "Mini Truck",
            "Capacity": 5
        },
        {
            "Vehicle": "Medium Truck",
            "Capacity": 10
        },
        {
            "Vehicle": "Large Truck",
            "Capacity": 20
        }
    ]


    st.table(vehicles)


    quantity = st.session_state.transport_data["Quantity"]


    st.write("### Quantity to Transport")

    st.info(
        f"Total Quantity: {quantity} Tons"
    )


    remaining = quantity

    assignments = []


    for vehicle in sorted(
        vehicles,
        key=lambda x: x["Capacity"],
        reverse=True
    ):


        trips = remaining // vehicle["Capacity"]


        if trips > 0:


            assignments.append({

                "Vehicle": vehicle["Vehicle"],

                "Trips": int(trips),

                "Quantity Transported":
                int(trips * vehicle["Capacity"])

            })


            remaining = (
                remaining -
                trips * vehicle["Capacity"]
            )


    if remaining > 0:


        assignments.append({

            "Vehicle": "Mini Truck",

            "Trips": 1,

            "Quantity Transported": remaining

        })


    st.subheader("🚚 Assigned Vehicles")

    st.table(assignments)


    st.success(
        "Vehicle Assignment Completed Successfully!"
    )


    st.session_state.vehicle_data = assignments


    if st.button(
        "🌧️ Continue to Disruption Simulation",
        use_container_width=True
    ):


        st.session_state.page = "disruption"

        st.rerun()
        # -------------------------------------
# Disruption Simulation Page
# -------------------------------------

elif st.session_state.page == "disruption":

    st.title("🌧️ Disruption & Scenario Simulation")


    st.subheader("Select a Scenario")


    scenario = st.selectbox(
        "Choose a real-world situation",
        [
            "Normal Day",
            "Heavy Rain",
            "Road Block",
            "Festival Demand Increase",
            "Crop Disease"
        ]
    )


    # Original values
    transport_cost = (
        st.session_state.transport_data["Transportation Cost"]
    )

    quantity = (
        st.session_state.transport_data["Quantity"]
    )


    new_cost = transport_cost
    new_quantity = quantity
    message = ""


    # Scenario Calculations

    if scenario == "Heavy Rain":

        new_cost = transport_cost * 1.5

        message = (
            "Roads are slow due to rain. "
            "Transportation cost increased by 50%."
        )


    elif scenario == "Road Block":

        new_cost = transport_cost * 2

        message = (
            "Alternative routes are used. "
            "Transportation cost doubled."
        )


    elif scenario == "Festival Demand Increase":

        new_quantity = quantity * 1.3

        message = (
            "Market demand increased by 30%."
        )


    elif scenario == "Crop Disease":

        new_quantity = quantity * 0.7

        message = (
            "Crop production reduced by 30% due to disease."
        )


    else:

        message = (
            "No disruption. Normal supply chain operation."
        )


    st.write("---")


    st.subheader("📊 Simulation Result")


    st.info(message)


    st.write(
        "🚚 Transportation Cost:",
        f"₹ {new_cost}"
    )


    st.write(
        "🌾 Available Quantity:",
        f"{new_quantity} Tons"
    )


    # Save scenario data
    st.session_state.scenario_data = {

        "Scenario": scenario,

        "Transportation Cost": new_cost,

        "Quantity": new_quantity

    }


    st.success(
        "Scenario Analysis Completed!"
    )


    if st.button(
        "🍅 Continue to Wastage Management",
        use_container_width=True
    ):

        st.session_state.page = "wastage"

        st.rerun()
        # -------------------------------------
# Wastage Reduction & Priority Management
# -------------------------------------

elif st.session_state.page == "wastage":

    st.title("🍅 Perishable Wastage Reduction System")


    st.subheader("Crop Shelf Life Analysis")


    crop = st.session_state.best_crop["Crop"]


    # Shelf life database
    shelf_life = {

        "Tomato": 5,
        "Carrot": 20,
        "Marigold": 2

    }


    days = shelf_life.get(
        crop,
        7
    )


    st.write(
        "Selected Crop:",
        crop
    )


    st.write(
        "Shelf Life:",
        days,
        "days"
    )


    st.write("---")


    # Priority Decision

    if days <= 3:

        priority = "High Priority 🚨"

        recommendation = (
            "Deliver immediately using the fastest route "
            "to avoid wastage."
        )

        wastage = "2%"


    elif days <= 7:

        priority = "Medium Priority ⚠️"

        recommendation = (
            "Deliver within a few days with optimized transportation."
        )

        wastage = "5%"


    else:

        priority = "Low Priority ✅"

        recommendation = (
            "Normal transportation schedule is sufficient."
        )

        wastage = "8%"


    st.subheader("📋 Wastage Management Decision")


    st.success(
        f"Priority Level: {priority}"
    )


    st.write(
        "Recommendation:",
        recommendation
    )


    st.write(
        "Estimated Wastage:",
        wastage
    )


    # Save for final report

    st.session_state.wastage_data = {

        "Crop": crop,
        "Shelf Life": days,
        "Priority": priority,
        "Estimated Wastage": wastage

    }


    if st.button(
        "📊 Continue to Scenario Comparison",
        use_container_width=True
    ):

        st.session_state.page = "comparison"

        st.rerun()
        # -------------------------------------
# Scenario Comparison Page
# -------------------------------------

elif st.session_state.page == "comparison":

    st.title("📊 Scenario Comparison Analysis")


    st.subheader(
        "KSHETRA Scenario Evaluation"
    )


    comparison_data = [

        {
            "Scenario": "Normal Day",
            "Transportation Cost (₹)": 250000,
            "Demand Change": "No Change",
            "Supply Change": "No Change",
            "Wastage": "2%"
        },

        {
            "Scenario": "Heavy Rain",
            "Transportation Cost (₹)": 320000,
            "Demand Change": "No Change",
            "Supply Change": "No Change",
            "Wastage": "5%"
        },

        {
            "Scenario": "Festival Demand",
            "Transportation Cost (₹)": 380000,
            "Demand Change": "+30%",
            "Supply Change": "No Change",
            "Wastage": "3%"
        },

        {
            "Scenario": "Crop Disease",
            "Transportation Cost (₹)": 420000,
            "Demand Change": "No Change",
            "Supply Change": "-30%",
            "Wastage": "8%"
        }

    ]


    st.write(
        """
        This comparison helps farmers and supply
        managers understand the effect of different
        real-world situations.
        """
    )


    st.table(comparison_data)


    st.success(
        """
        KSHETRA recommends selecting the plan
        with minimum cost and minimum wastage
        while maintaining supply demand balance.
        """
    )


    # Save comparison information

    st.session_state.comparison_data = comparison_data


    if st.button(
        "📄 Generate Final KSHETRA Report",
        use_container_width=True
    ):

        st.session_state.page = "final_report"

        st.rerun()
        # -------------------------------------
# Final KSHETRA Report Page
# -------------------------------------

elif st.session_state.page == "final_report":

    st.title("📄 Final KSHETRA Smart Agricultural Report")


    st.write(
        """
        Complete Agricultural Decision Report
        generated using Operations Research.
        """
    )

    st.write("---")


   
# -------------------------------
# Farmer Production Details
# -------------------------------

st.header("👨‍🌾 Farmer Production Details")


location = st.selectbox(
    "📍 Farm Location",
    [
        "Kolar",
        "Bengaluru",
        "Tumakuru",
        "Mysuru",
        "Mandya",
        "Hassan"
    ]
)


land = st.number_input(
    "🌾 Total Land Area (Acres)",
    min_value=1,
    max_value=1000,
    value=10
)


st.write("---")


crop_count = st.number_input(
    "🌱 How many different crops have you grown?",
    min_value=1,
    max_value=10,
    value=1
)


crop_data = []


for i in range(crop_count):

    st.subheader(f"Crop {i+1}")


    crop_name = st.text_input(
        "Crop Name",
        key=f"crop_{i}"
    )


    quantity = st.number_input(
        "Quantity Produced (Tons)",
        min_value=0.0,
        key=f"quantity_{i}"
    )


    crop_data.append({
        "crop": crop_name,
        "quantity": quantity
    })


if st.button(
    "🔍 Analyze Market & Supply Chain",
    use_container_width=True
):

    valid_crop_data = [
        crop for crop in crop_data
        if crop["crop"] != "" and crop["quantity"] > 0
    ]


    if len(valid_crop_data) == 0:

        st.warning(
            "Please enter crop names and quantities."
        )

    else:

        st.session_state.farm_data = {
            "location": location,
            "land": land,
            "crops": valid_crop_data
        }


        st.success(
            "Farm production details saved successfully!"
        )


        st.session_state.page = "market_analysis"

        st.rerun()

    # -------------------------------
    # Crop Recommendation
    # -------------------------------

    st.header("🌱 Recommended Crop")

    crop = st.session_state.best_crop

    st.write(
        "Best Crop:",
        crop["Crop"]
    )

    st.write(
        "Expected Production:",
        crop["Expected Production (tons)"],
        "tons"
    )

    st.write(
        "Expected Revenue: ₹",
        crop["Expected Revenue (₹)"]
    )


    # -------------------------------
    # Mandi Selection
    # -------------------------------

    st.header("🏪 Best Mandi Selection")


    mandi = st.session_state.mandi_data


    st.write(
        "Selected Mandi:",
        mandi["Mandi"]
    )


    st.write(
        "Expected Profit: ₹",
        mandi["Net Profit (₹)"]
    )


    # -------------------------------
    # Transportation
    # -------------------------------

    st.header("🚚 Transportation Optimization")


    transport = st.session_state.transport_data


    st.write(
        "Quantity Transported:",
        transport["Quantity"],
        "tons"
    )


    st.write(
        "Transportation Cost: ₹",
        transport["Transportation Cost"]
    )


    # -------------------------------
    # Vehicle Assignment
    # -------------------------------

    st.header("🚛 Vehicle Assignment")


    st.table(
        st.session_state.vehicle_data
    )


    # -------------------------------
    # Disruption Simulation
    # -------------------------------

    st.header("🌧️ Disruption Analysis")


    disruption = st.session_state.scenario_data


    st.write(
        "Selected Scenario:",
        disruption["Scenario"]
    )


    st.write(
        "Updated Transportation Cost: ₹",
        disruption["Transportation Cost"]
    )


    st.write(
        "Available Quantity:",
        disruption["Quantity"],
        "tons"
    )


    # -------------------------------
    # Wastage Reduction
    # -------------------------------

    st.header("🍅 Wastage Management")


    wastage = st.session_state.wastage_data


    st.write(
        "Crop:",
        wastage["Crop"]
    )

    st.write(
        "Shelf Life:",
        wastage["Shelf Life"],
        "days"
    )

    st.write(
        "Priority:",
        wastage["Priority"]
    )

    st.write(
        "Estimated Wastage:",
        wastage["Estimated Wastage"]
    )


    # -------------------------------
    # Scenario Comparison
    # -------------------------------

    st.header("📊 Scenario Comparison")


    st.table(
        st.session_state.comparison_data
    )


    # -------------------------------
    # Final Decision
    # -------------------------------

    st.header("🎯 KSHETRA Final Recommendation")


    st.success(
        f"""
        Recommended Crop: {crop['Crop']}

        Sell at: {mandi['Mandi']} Mandi

        Expected Profit: ₹ {mandi['Net Profit (₹)']}

        Follow optimized transportation
        and priority delivery to reduce
        wastage and maximize farmer income.
        """
    )


    st.balloons()


    st.write("---")

    st.write(
        "🌱 Thank you for using KSHETRA - Smart Agricultural Decision Support System"
    )

    # -------------------------------------
# Market Analysis & Mandi Selection
# -------------------------------------

elif st.session_state.page == "market_analysis":

    st.title("🏪 Mandi Market Analysis")

    st.write(
        "KSHETRA is analyzing today's market prices and profits."
    )

    farmer_location = st.session_state.farm_data["location"]

    crops = st.session_state.farm_data["crops"]

    # Load datasets
    mandi_data = pd.read_csv("data/mandis.csv")
    distance_data = pd.read_csv("data/distance_matrix.csv")

    final_results = []


    for item in crops:

        crop_name = item["crop"].title()
        quantity = item["quantity"]

        st.header(f"🌱 {crop_name}")

        crop_mandis = mandi_data[
            mandi_data["Crop"].str.lower()
            ==
            crop_name.lower()
        ]


        results = []


        for index, row in crop_mandis.iterrows():

            mandi = row["Mandi"]

            price = row["Price_per_kg"]


            distance_row = distance_data[
                (distance_data["From"] == farmer_location)
                &
                (distance_data["To"] == mandi)
            ]


            if distance_row.empty:

                continue


            distance = distance_row.iloc[0]["Distance_km"]


            # Revenue Calculation
            revenue = quantity * 1000 * price


            # Transport cost
            transport_cost = quantity * distance * 10


            # Final Profit
            profit = revenue - transport_cost


            results.append({

                "Mandi": mandi,

                "Price ₹/kg": price,

                "Distance (km)": distance,

                "Revenue ₹": revenue,

                "Transport Cost ₹": transport_cost,

                "Net Profit ₹": profit

            })


        if results:

            result_df = pd.DataFrame(results)


            st.table(result_df)


            best = result_df.loc[
                result_df["Net Profit ₹"].idxmax()
            ]


            st.success(
                f"""
                ⭐ Best Mandi for {crop_name}

                🏪 Mandi: {best['Mandi']}

                💰 Expected Profit: ₹{best['Net Profit ₹']}
                """
            )


            final_results.append({

                "Crop": crop_name,

                "Quantity": quantity,

                "Best Mandi": best["Mandi"],

                "Profit": best["Net Profit ₹"]

            })


    st.session_state.mandi_results = final_results


    if st.button(
        "🚚 Continue to Transportation Optimization",
        use_container_width=True
    ):

        st.session_state.page = "transportation"

        st.rerun()
        # -------------------------------------
# Transportation Optimization
# -------------------------------------

elif st.session_state.page == "transportation":

    st.title("🚚 Transportation Optimization")


    st.write(
        "KSHETRA is finding the most efficient transportation plan."
    )


    distance_data = pd.read_csv(
        "data/distance_matrix.csv"
    )


    farmer_location = (
        st.session_state.farm_data["location"]
    )


    mandi_results = (
        st.session_state.mandi_results
    )


    transport_list = []


    for item in mandi_results:


        crop = item["Crop"]

        quantity = item["Quantity"]

        mandi = item["Best Mandi"]


        route = distance_data[
            (distance_data["From"] == farmer_location)
            &
            (distance_data["To"] == mandi)
        ]


        if route.empty:
            continue


        distance = route.iloc[0]["Distance_km"]


        # Transportation assumptions
        cost_per_km_per_ton = 10


        transport_cost = (
            distance *
            quantity *
            cost_per_km_per_ton
        )


        # Delivery Time Estimation
        average_speed = 50


        travel_time = (
            distance /
            average_speed
        )


        transport_list.append({

            "Crop": crop,

            "Route":
            f"{farmer_location} ➡ {mandi}",

            "Quantity (tons)":
            quantity,

            "Distance (km)":
            distance,

            "Estimated Time (hours)":
            round(travel_time, 2),

            "Transport Cost (₹)":
            transport_cost

        })


    transport_df = pd.DataFrame(
        transport_list
    )


    st.subheader(
        "Optimized Transportation Plan"
    )


    st.table(
        transport_df
    )


    total_cost = transport_df[
        "Transport Cost (₹)"
    ].sum()


    st.success(
        f"""
        Total Transportation Cost:
        ₹ {total_cost}
        """
    )


    st.session_state.transport_results = (
        transport_list
    )


    if st.button(
        "🌧️ Continue to Weather Simulation",
        use_container_width=True
    ):


        st.session_state.page = (
            "weather_simulation"
        )


        st.rerun()
        # -------------------------------------
# Weather & Disruption Simulation
# -------------------------------------

elif st.session_state.page == "weather_simulation":

    st.title("🌧️ Weather & Disruption Simulation")


    st.write(
        "Simulate real-world conditions and analyze supply chain impact."
    )


    situation = st.radio(
        "Select Current Situation",
        [
            "☀️ Normal Day",
            "🌧️ Heavy Rain",
            "🎉 Festival Demand",
            "🚧 Road Block",
            "🦠 Crop Disease"
        ]
    )


    original_data = st.session_state.transport_results


    updated_plan = []


    for item in original_data:


        cost = item["Transport Cost (₹)"]

        time = item["Estimated Time (hours)"]

        quantity = item["Quantity (tons)"]


        # Normal condition
        if situation == "☀️ Normal Day":

            cost_multiplier = 1
            time_multiplier = 1


        # Heavy Rain
        elif situation == "🌧️ Heavy Rain":

            cost_multiplier = 1.30
            time_multiplier = 1.50


        # Festival Demand
        elif situation == "🎉 Festival Demand":

            cost_multiplier = 1.10
            time_multiplier = 1.20


        # Road Block
        elif situation == "🚧 Road Block":

            cost_multiplier = 1.50
            time_multiplier = 2.00


        # Crop Disease
        elif situation == "🦠 Crop Disease":

            cost_multiplier = 1
            time_multiplier = 1
            quantity = quantity * 0.70


        new_cost = cost * cost_multiplier
        new_time = time * time_multiplier


        updated_plan.append({

            "Crop": item["Crop"],

            "Route": item["Route"],

            "Available Quantity (tons)": round(quantity,2),

            "Delivery Time (hours)": round(new_time,2),

            "Updated Transportation Cost (₹)": round(new_cost,2)

        })


    st.subheader(
        "Updated Supply Chain Plan"
    )


    st.table(updated_plan)


    total_cost = sum(
        x["Updated Transportation Cost (₹)"]
        for x in updated_plan
    )


    st.success(
        f"Total Updated Transportation Cost: ₹ {total_cost}"
    )


    if situation == "🚧 Road Block":

        st.warning(
            "Road disruption detected. Alternative route is recommended."
        )


    if situation == "🦠 Crop Disease":

        st.error(
            "Crop availability reduced due to disease."
        )


    st.session_state.weather_results = updated_plan


    if st.button(
        "🚛 Continue to Vehicle Assignment",
        use_container_width=True
    ):

        st.session_state.page = "vehicle_assignment"

        st.rerun()
# -------------------------------------
# Shelf Life & Priority Management
# -------------------------------------

elif st.session_state.page == "priority_management":

    st.title("🍅 Perishable Priority Management")

    st.write(
        "KSHETRA is prioritizing crops based on shelf life to reduce wastage."
    )


    crop_database = pd.read_csv("data/crops.csv")


    priority_list = []


    for item in st.session_state.weather_results:


        crop_name = item["Crop"]


        crop_info = crop_database[
            crop_database["Crop"].str.lower()
            ==
            crop_name.lower()
        ]


        if crop_info.empty:

            shelf_life = 30

        else:

            shelf_life = crop_info.iloc[0]["Shelf_Life_Days"]


        if shelf_life <= 3:

            priority = "🔴 Very High Priority"

        elif shelf_life <= 7:

            priority = "🟠 High Priority"

        elif shelf_life <= 30:

            priority = "🟡 Medium Priority"

        else:

            priority = "🟢 Low Priority"


        priority_list.append({

            "Crop": crop_name,

            "Shelf Life (Days)": shelf_life,

            "Transport Priority": priority

        })


    priority_df = pd.DataFrame(priority_list)


    priority_df = priority_df.sort_values(
        by="Shelf Life (Days)"
    )


    st.subheader("Priority Transport Order")


    st.table(priority_df)


    st.success(
        "Crops with the lowest shelf life are scheduled for first delivery."
    )


    st.session_state.priority_results = (
        priority_list
    )


    if st.button(
        "📊 Continue to Final KSHETRA Report",
        use_container_width=True
    ):

        st.session_state.page = "final_report"

        st.rerun()
        # -------------------------------------
# KSHETRA OR Smart Score
# -------------------------------------

elif st.session_state.page == "smart_score":

    st.title("🧠 KSHETRA OR Smart Recommendation")


    st.write(
        """
        Calculating the best decision using
        Profit, Distance, Demand, Weather,
        and Shelf Life.
        """
    )


    mandi = pd.DataFrame(
        st.session_state.mandi_results
    )


    transport = pd.DataFrame(
        st.session_state.transport_results
    )


    scores = []


    for i in range(len(mandi)):


        crop = mandi.iloc[i]["Crop"]

        profit = mandi.iloc[i]["Profit"]


        distance = transport.iloc[i]["Distance (km)"]


        # Normalize Scores

        profit_score = (
            profit /
            mandi["Profit"].max()
        ) * 100


        distance_score = (
            1 -
            distance /
            transport["Distance (km)"].max()
        ) * 100


        # Temporary values
        demand_score = 80
        weather_score = 85


        shelf_score = 90


        final_score = (

            0.4 * profit_score +
            0.2 * distance_score +
            0.2 * demand_score +
            0.1 * weather_score +
            0.1 * shelf_score

        )


        scores.append({

            "Crop": crop,

            "Profit Score": round(profit_score,2),

            "Distance Score": round(distance_score,2),

            "Demand Score": demand_score,

            "Weather Score": weather_score,

            "Shelf Life Score": shelf_score,

            "Final KSHETRA Score (%)":
            round(final_score,2)

        })


    result = pd.DataFrame(scores)


    st.table(result)


    best = result.loc[
        result["Final KSHETRA Score (%)"].idxmax()
    ]


    st.success(
        f"""
        🏆 Best Overall Decision

        Crop:
        {best['Crop']}

        KSHETRA Smart Score:
        {best['Final KSHETRA Score (%)']} %
        """
    )


    st.session_state.smart_score = scores


    if st.button(
        "📄 Continue to Final Report",
        use_container_width=True
    ):

        st.session_state.page = "final_report"

        st.rerun()
# -------------------------------------
# Final KSHETRA Report
# -------------------------------------

elif st.session_state.page == "final_report":

    st.title("📄 FINAL KSHETRA DECISION REPORT")

    st.write("---")


    # Farmer Details
    st.header("👨‍🌾 Farmer Information")

    farm = st.session_state.farm_data

    st.write("📍 Location:", farm["location"])
    st.write("🌾 Land Area:", farm["land"], "Acres")
    st.write("🌦️ Season:", farm["season"])


    st.write("---")


    # Mandi Recommendation
    st.header("🏪 Best Mandi Recommendation")

    mandi_data = pd.DataFrame(
        st.session_state.mandi_results
    )

    st.table(mandi_data)


    total_profit = mandi_data["Profit"].sum()

    st.success(
        f"💰 Total Expected Profit: ₹ {total_profit:,.2f}"
    )


    st.write("---")


    # Transportation Details
    st.header("🚚 Transportation Summary")

    transport_data = pd.DataFrame(
        st.session_state.transport_results
    )

    st.table(transport_data)


    total_transport = transport_data[
        "Transport Cost (₹)"
    ].sum()


    st.info(
        f"🚚 Total Transportation Cost: ₹ {total_transport:,.2f}"
    )


    st.write("---")


    # Weather Impact
    st.header("🌧️ Current Scenario Analysis")

    weather_data = pd.DataFrame(
        st.session_state.weather_results
    )

    st.table(weather_data)


    st.write("---")


    # Priority Management
    st.header("🍅 Perishable Priority Order")

    priority_data = pd.DataFrame(
        st.session_state.priority_results
    )

    st.table(priority_data)


    st.write("---")


    # Final Decision
    st.header("🌱 KSHETRA Final Recommendation")

    best_crop = mandi_data.loc[
        mandi_data["Profit"].idxmax()
    ]


    st.success(
        f"""
        🌟 Highest Profit Crop: {best_crop['Crop']}

        🏪 Sell At: {best_crop['Best Mandi']}

        💰 Expected Profit: ₹ {best_crop['Profit']:,.2f}

        📌 Recommended Action:
        Transport this crop first to maximize farmer income.
        """
    )


    st.write("---")


    # New Analysis Button
    if st.button(
        "🔄 Start New KSHETRA Analysis",
        use_container_width=True
    ):

        st.session_state.farm_data = {}
        st.session_state.mandi_results = []
        st.session_state.transport_results = []
        st.session_state.weather_results = []
        st.session_state.priority_results = []

        st.session_state.page = "farm_details"

        st.rerun()
