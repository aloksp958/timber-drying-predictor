import joblib
import pandas as pd
import sys
import numpy as np
import json # Graph data ke liye

# --- EXPERT Species Specific Drying Tips (v2.0) ---
SPECIES_TIPS = {
    # Hardwoods - Prone to checking/cracking if dried too fast
    "Oak, Red": "[TIP] High risk of checking & honeycombing. Requires slow initial drying (low temp <45°C, high humidity >70%) especially above FSP (~30% MC). Use end coating. Increase temp slowly only after MC drops below 25%.",
    "Oak, White": "[TIP] Very slow drying, similar risks to Red Oak but slightly more prone to surface checks. Use mild schedule (low temp, high humidity). Good airflow is crucial. Use end coating.",
    "Maple, Sugar (Hard)": "[TIP] Prone to discoloration (sticker stain, chemical stain) if humidity is high for too long. Needs moderate temp (~50-60°C) and good airflow. Can check if dried too fast.",
    "Maple, Red (Soft)": "[TIP] Dries faster than Hard Maple but also prone to sticker stain. Keep humidity moderate (~60-65%) and ensure good airflow. Avoid high initial temps.",
    "Ash, White": "[TIP] Relatively easy to dry but can develop brown stain if humidity is too high initially. Use moderate schedule. Good airflow prevents staining.",
    "Birch, Yellow": "[TIP] Moderate drying speed. Prone to surface checking and end splitting if temp increases too rapidly. Careful control needed.",
    "Walnut, Black": "[TIP] Best color achieved with slower drying, especially air-drying first. Kiln drying needs moderate temps (<50°C initially) to prevent darkening or graying. Low risk of checking.",

    # Softwoods - Generally dry faster, risk of warping/stain
    "Pine, Southern": "[TIP] Dries fast but high risk of warping, twisting, and checking around knots. Needs good stacking, weights on top, and moderate temps. Watch for blue stain.",
    "Pine, White": "[TIP] Dries very easily and quickly with low degrade risk. Main concern is blue stain if kept wet for too long or if humidity is too high. Low temps (<45°C) recommended.",
    "Pine, Ponderosa": "[INFO] Ponderosa Pine dries easily but can be prone to brown stain (enzymatic) especially in thicker stock. Requires prompt handling after cutting and good airflow. Can warp.",
    "Douglas Fir": "[TIP] Dries well, relatively fast. Thicker dimensions (>5cm) have high risk of internal checking (honeycombing) if dried too aggressively. Use milder schedule for thick stock.",
    "Spruce": "[TIP] Spruce dries quickly but is prone to knots loosening or splitting, especially if over-dried. Watch for checking around knots.",
    "Cedar, Western Red": "[INFO] Very stable, dries easily with minimal shrinkage or degrade. Low temps are sufficient. Can collapse if temps are too high when wet.",

    # Tropical/Other
    "Teak": "[INFO] Teak is naturally oily and very stable. Dries relatively slowly but with very low risk of defects. Moderate schedule is fine.",
    "Mahogany": "[INFO] Mahogany generally dries well with low shrinkage and minimal defects. Can be prone to internal stresses (casehardening) if dried too fast.",

    # Default
    "Default": "[INFO] General best practices apply: ensure good airflow between boards using properly spaced stickers, use weights on top of the stack to minimize warping, and seal end grain if possible to prevent rapid moisture loss and end checks. Monitor moisture content regularly."
}
# --- Species Tips END ---


# --- 1. Load the trained model and categories ---
try:
    model = joblib.load("drying_model.pkl")
    known_species = joblib.load("species_categories.pkl")
except FileNotFoundError:
    print("ERROR: Model or category files not found.")
    print("Please run 'train_model.py' first!")
    sys.exit(1)

# --- 2. Get inputs from the command line ---
try:
    species_input = sys.argv[1]
    thickness_cm = float(sys.argv[2])
    initial_mc = float(sys.argv[3])
    target_mc = float(sys.argv[4])
    temp_c = float(sys.argv[5])
    humidity_rh = float(sys.argv[6])
except IndexError:
    print("Error: Missing inputs.")
    print("Usage: python predict.py \"Species Name\" Thickness Initial_MC Target_MC Temp Humidity")
    sys.exit(1)
except ValueError:
    print("Error: Invalid number format for inputs.")
    sys.exit(1)

# --- 3. Validate and process the inputs ---
if species_input not in known_species:
    print(f"Error: Unknown species '{species_input}'.")
    print("Known species are:", known_species)
    sys.exit(1)

SPECIES_GRAVITY_MAP = {
    "Pine, Southern": 0.55, "Pine, White": 0.36, "Pine, Ponderosa": 0.43,
    "Oak, White": 0.73, "Oak, Red": 0.67, "Maple, Sugar (Hard)": 0.67,
    "Maple, Red (Soft)": 0.58, "Douglas Fir": 0.50, "Cedar, Western Red": 0.36,
    "Ash, White": 0.65, "Birch, Yellow": 0.67, "Walnut, Black": 0.59,
    "Teak": 0.66, "Mahogany": 0.59, "Spruce": 0.43
}
specific_gravity = SPECIES_GRAVITY_MAP.get(species_input, 0.5)


# --- 4. Create the input DataFrame for the model ---
input_data_dict = {
    "Species": species_input,
    "Thickness_cm": thickness_cm,
    "Specific_Gravity": specific_gravity,
    "Initial_Moisture": initial_mc,
    "Target_Moisture": target_mc,
    "Temperature_C": temp_c,
    "Humidity_RH": humidity_rh
}

def create_input_df(data_dict):
    df = pd.DataFrame([data_dict])
    df['Species'] = pd.Categorical(df['Species'], categories=known_species)
    training_features = [
        "Species", "Thickness_cm", "Specific_Gravity",
        "Initial_Moisture", "Target_Moisture", "Temperature_C", "Humidity_RH"
    ]
    return df[training_features]

baseline_input_df = create_input_df(input_data_dict)

# --- 5. Make the BASELINE prediction ---
try:
    baseline_time = model.predict(baseline_input_df)[0]
    baseline_time = max(0.1, float(baseline_time)) # Ensure it's a standard float
except Exception as e:
     print(f"Error during prediction: {e}")
     baseline_time = 0

# --- 6. Show the Baseline Result ---
print(f"\n--- Prediction Result ---")
print(f"Input Species: {species_input}")
print(f"Input Thickness: {thickness_cm} cm")
print(f"Conditions: {temp_c}°C, {humidity_rh}% Humidity")
print(f"Moisture Range: {initial_mc}% -> {target_mc}%")
print("---------------------------------")
if baseline_time > 0:
    print(f"PREDICTED DRYING TIME: {baseline_time:.2f} hours")
    print(f"(Approximately {baseline_time/24:.1f} days)")
else:
    print("Could not calculate prediction.")


# --- 7. Dynamic "What-If" Recommendations ---
if baseline_time > 0:
    print("\n--- Smart Recommendations (What-If Analysis) ---")
    recommendations = []
    try:
        # Scenario 1: Increase temp
        if temp_c < 55:
            temp_up_dict = input_data_dict.copy()
            temp_up_dict['Temperature_C'] = temp_c + 5
            new_time_temp = max(0.1, float(model.predict(create_input_df(temp_up_dict))[0]))
            temp_savings = baseline_time - new_time_temp
            if temp_savings > 1:
                recommendations.append(
                    (temp_savings, f"[TIP] Increasing temp by 5°C could save approx. {temp_savings:.1f} hours.")
                )

        # Scenario 2: Decrease humidity
        if humidity_rh > 30:
            hum_down_dict = input_data_dict.copy()
            hum_down_dict['Humidity_RH'] = humidity_rh - 10
            new_time_hum = max(0.1, float(model.predict(create_input_df(hum_down_dict))[0]))
            hum_savings = baseline_time - new_time_hum
            if hum_savings > 1:
                recommendations.append(
                    (hum_savings, f"[TIP] Decreasing humidity by 10% could save approx. {hum_savings:.1f} hours.")
                )

        recommendations.sort(key=lambda x: x[0], reverse=True)

        if not recommendations:
            print("[OK] Conditions are near optimal, or changes have minimal effect.")
        else:
            for saving, rec in recommendations:
                print(rec)

    except Exception as e:
        print(f"Could not calculate recommendations: {e}")

    # Add thickness info
    if thickness_cm > 5:
        print("[INFO] This is a thick board; drying will always take significant time.")

    # --- Print Species Specific Tip ---
    print("\n--- Species Specific Advice ---")
    tip = SPECIES_TIPS.get(species_input, SPECIES_TIPS["Default"])
    print(tip)
    # --- NAYA: Add Disclaimer ---
    print("\n[Disclaimer] These tips are general guidelines. Actual results depend on specific kiln conditions, wood quality, and operator expertise.")
    # --- Disclaimer END ---


    # --- Generate and Print Graph Data ---
    print("\n--- Predicted Drying Curve Data ---")
    try:
        if baseline_time <= 0:
             raise ValueError("Baseline time must be positive to generate graph.")

        time_points = np.linspace(0, baseline_time, num=10)
        time_ratio = time_points / baseline_time if baseline_time > 0 else np.zeros_like(time_points)
        moisture_points = initial_mc - (initial_mc - target_mc) * np.sqrt(np.maximum(0, time_ratio))
        moisture_points[0] = initial_mc
        moisture_points[-1] = target_mc

        # Convert NumPy floats to standard Python floats using float()
        graph_data = {
            "time_labels": [round(float(t), 1) for t in time_points],
            "moisture_values": [round(float(m), 1) for m in moisture_points]
        }

        print("GRAPH_DATA_START")
        print(json.dumps(graph_data)) # Ab yeh fail nahi hoga
        print("GRAPH_DATA_END")

    except Exception as e:
        print(f"Could not generate graph data: {e}")
    # --- Graph Data END ---

