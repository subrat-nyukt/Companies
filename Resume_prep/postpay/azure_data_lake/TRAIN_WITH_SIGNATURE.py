# FIXED MODEL TRAINING CODE (With Signature)
# Run this in a NEW Python Notebook cell.

import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature  # --- THIS IS NEW ---
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

print("--- RE-TRAINING WITH SIGNATURE ---")

# 1. Load Data
df_spark = spark.table("default.gold_customer_risk_profile")
df = df_spark.toPandas()

# 2. Preprocess
X = df.drop(["customer_id", "is_defaulter"], axis=1)
y = df["is_defaulter"]
X = pd.get_dummies(X, columns=["device_type"], drop_first=True)
X = X.fillna(0)

# 3. Train
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

# --- THE FIX: Create Model Signature ---
# This tells Databricks exactly what the input looks like (e.g., "plans_1m is a double")
signature = infer_signature(X_train, rf.predict(X_train))

# 4. Log to MLflow WITH Signature
with mlflow.start_run(run_name="Risk_Model_With_Signature"):
    
    # Log the usual metrics
    acc = accuracy_score(y_test, rf.predict(X_test))
    mlflow.log_metric("accuracy", acc)
    
    # Log model WITH SIGNATURE (Crucial for Unity Catalog)
    mlflow.sklearn.log_model(
        rf, 
        "model",
        signature=signature,  # <--- PASS IT HERE
        input_example=X_train.head() # Helpful for UI testing
    )
    
    print("✅ Model re-trained and saved WITH signature!")
