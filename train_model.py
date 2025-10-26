import pandas as pd
import xgboost as xgb
import joblib 
from sklearn.model_selection import train_test_split

print("Starting model training (v2.2 Fix)...")

# 1. Load the dataset
try:
    df = pd.read_csv("synthetic_wood_drying_data.csv")
except FileNotFoundError:
    print("ERROR: 'synthetic_wood_drying_data.csv' not found.")
    print("Please run 'generate_data.py' first!")
    exit()

print(f"Loaded {len(df)} rows of synthetic data.")

# --- NEW (v2.2): Tell pandas this is a category ---
df['Species'] = df['Species'].astype('category')
# Save the categories for the prediction script
species_categories = list(df['Species'].cat.categories) 

# 2. Define Features (X) and Target (y)
target_variable = "Drying_Time_Hours"
features = [
    "Species", 
    "Thickness_cm", 
    "Specific_Gravity",
    "Initial_Moisture", 
    "Target_Moisture", 
    "Temperature_C", 
    "Humidity_RH"
]

X = df[features]
y = df[target_variable]

# 3. Handle Categorical Data
# --- REMOVED (v2.2): No OrdinalEncoder needed ---
print("Data pre-processing complete (using native categories).")

# 4. Split Data (80% for training, 20% for testing)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 5. Create and Train the XGBoost Model
print("Training the XGBoost model... (This may take a minute)")

model = xgb.XGBRegressor(
    objective='reg:squarederror',
    n_estimators=1000,
    learning_rate=0.05,
    max_depth=5,
    early_stopping_rounds=50,
    random_state=42,
    enable_categorical=True  # --- NEW (v2.2): Tell XGBoost to handle categories ---
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)], 
    verbose=False
)

print("Model training complete!")

# 6. Save the Model and the Categories
model_filename = "drying_model.pkl"
joblib.dump(model, model_filename)

# --- NEW (v2.2): Save the list of categories ---
category_filename = "species_categories.pkl"
joblib.dump(species_categories, category_filename)

print(f"Model saved as '{model_filename}'")
print(f"Categories saved as '{category_filename}'") # <-- NEW
print("\n--- Build complete! You have your trained AI. ---")