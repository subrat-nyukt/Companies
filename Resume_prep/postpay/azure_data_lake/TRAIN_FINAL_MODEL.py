# DATABRICKS MODEL TRAINING CODE
# Run this in a NEW Python Notebook in Databricks.

import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

print("--- STEP 1: LOADING DATA ---")
# Read the Gold Table we just created
df_spark = spark.table("default.gold_customer_risk_profile")
df = df_spark.toPandas()

print(f"Loaded {len(df)} customer profiles.")
print("Columns:", list(df.columns))

# --- STEP 2: PREPROCESSING ---
# Separate Features (X) and Target (y)
target = "is_defaulter"

# Drop non-numeric columns that imply identity, not behavior
# We drop 'customer_id' because it's just a label
X = df.drop(["customer_id", target], axis=1)
y = df[target]

# handle 'device_type' (Convert "iPhone"/"Android" text to numbers)
# This is called One-Hot Encoding
X = pd.get_dummies(X, columns=["device_type"], drop_first=True)

# Fill any remaining missing values with 0
X = X.fillna(0)

# Split into Training (80%) and Testing (20%)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- STEP 3: TRAINING ---
print("\n--- STEP 3: TRAINING MODEL ---")
with mlflow.start_run(run_name="Postpay_Risk_Model"):
    
    # Initialize the Random Forest
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    
    # Train it
    rf.fit(X_train, y_train)
    
    # Predict on the Test Set
    y_pred = rf.predict(X_test)
    
    # --- STEP 4: EVALUATION ---
    acc = accuracy_score(y_test, y_pred)
    
    print(f"\n✅ Model Accuracy: {acc:.2%}")
    print("\nDetailed Report:")
    print(classification_report(y_test, y_pred))
    
    print("\nConfusion Matrix (True Negatives | False Positives)")
    print("(False Negatives | True Positives)")
    print(confusion_matrix(y_test, y_pred))
    
    # Log to MLflow
    mlflow.log_metric("accuracy", acc)
    mlflow.sklearn.log_model(rf, "model")
    print("\n🎉 Model Saved to MLflow Registry!")
