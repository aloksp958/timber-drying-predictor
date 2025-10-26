import pandas as pd
import numpy as np
import random

# --- Component 1: Species Knowledge Base (Indian Woods Focus) ---
# Approximate specific gravity values based on research
SPECIES_GRAVITY_MAP = {
    "Teak (Sagwan)": 0.66,
    "Sal": 0.85,
    "Sheesham (Indian Rosewood)": 0.78,
    "Mango": 0.60, # Average value
    "Deodar (Himalayan Cedar)": 0.50,
    "Chir Pine": 0.53,
    "Neem": 0.68,
    "Babul": 0.80,
    "Sissoo": 0.75,
    "Haldu": 0.65,
    "Indian Laurel (Asna)": 0.75,
    "Marandi (Red Meranti type)": 0.55 # Commonly imported/used
}

# --- Component 2: The "Physics Engine" (Simulator) ---
def calculate_drying_time(thickness, specific_gravity, initial_mc, target_mc, temp_c, humidity_rh):
    """
    Calculates the theoretical drying time in hours based on a simplified
    empirical model, adjusted for potentially higher humidity.
    """
    # 1. Normalize inputs
    humidity_frac = humidity_rh / 100.0
    mc_initial_frac = initial_mc / 100.0
    mc_target_frac = target_mc / 100.0

    # 2. Calculate key factors
    moisture_to_remove = mc_initial_frac - mc_target_frac

    # --- Robust Zero Time Check ---
    # If moisture to remove is negligible or negative, return 0
    if moisture_to_remove < 0.001: # Use a small tolerance
        return 0.0
    # --- Check End ---

    # Wood Resistance Factor (denser, thicker wood is harder to dry)
    wood_resistance = specific_gravity * (thickness**1.5)

    # Drying Power Factor (hot, dry air dries faster)
    # Higher humidity significantly reduces drying power
    drying_power = (temp_c / 10.0) * (1.0 - humidity_frac) + 0.05 # Reduced base slightly for high humidity

    # 3. Calculate Final Time
    calibration_constant = 70 # Slightly increased constant for higher avg humidity
    time_hours = (wood_resistance * moisture_to_remove / drying_power) * calibration_constant

    # NO random noise for consistency in training
    return max(0.1, time_hours) # Ensure time is at least slightly positive if drying needed

# --- Component 3: The Generator ---
print("Starting synthetic data generation (Indian Context)...")
data = []
N_ROWS = 10000 # Keep 10,000 data points

species_list = list(SPECIES_GRAVITY_MAP.keys())

for i in range(N_ROWS):
    # 1. Select Species and get Specific Gravity
    species = random.choice(species_list)
    specific_gravity = SPECIES_GRAVITY_MAP[species]

    # 2. Randomize other inputs (Indian Climate Ranges)
    thickness_cm = round(np.random.uniform(1.5, 12.0), 1) # Slightly wider thickness range
    initial_mc = round(np.random.uniform(35.0, 120.0), 1) # Initial MC can be high
    target_mc = round(np.random.uniform(8.0, 15.0), 1) # Target MC range
    temp_c = round(np.random.uniform(25.0, 45.0), 1) # Adjusted Temp Range
    humidity_rh = round(np.random.uniform(40.0, 95.0), 1) # Adjusted Humidity Range (Higher Max)

    # --- NAYA: Ensure some cases have Initial MC <= Target MC ---
    # Force about 1% of cases to be already dry for the model to learn
    if i < N_ROWS * 0.01:
         initial_mc = target_mc - round(np.random.uniform(0.1, 5.0), 1) # Make it slightly lower or equal
         initial_mc = max(5.0, initial_mc) # Ensure initial MC isn't unrealistically low


    # 3. Calculate the drying time
    drying_time_hours = calculate_drying_time(
        thickness_cm,
        specific_gravity,
        initial_mc,
        target_mc,
        temp_c,
        humidity_rh
    )

    # 4. Store the data
    data.append({
        "Species": species,
        "Thickness_cm": thickness_cm,
        "Specific_Gravity": specific_gravity,
        "Initial_Moisture": initial_mc,
        "Target_Moisture": target_mc,
        "Temperature_C": temp_c,
        "Humidity_RH": humidity_rh,
        "Drying_Time_Hours": round(drying_time_hours, 2)
    })

# 5. Save to CSV
df = pd.DataFrame(data)
# Ensure Target Moisture column exists before saving (was missing header in app.py fix)
if 'Target_Moisture' not in df.columns:
     print("Error: Target_Moisture column missing!")
else:
     df.to_csv("synthetic_wood_drying_data.csv", index=False)
     print(f"Successfully generated {N_ROWS} rows of data.")
     print(df.head())
     # Print stats for zero drying time
     zero_time_count = len(df[df['Drying_Time_Hours'] == 0.0])
     print(f"Number of rows with 0 drying time: {zero_time_count} (approx {zero_time_count/N_ROWS*100:.1f}%)")
