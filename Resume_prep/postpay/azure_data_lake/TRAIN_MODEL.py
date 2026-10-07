# PHASE 3: MODEL TRAINING (MLflow)
# Run this in a NEW cell in your Databricks Notebook.

import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score

# 1. Load the Feature Table we just created
print("Loading Feature Table...")
risk_df = spark.table("default.customer_risk_features").toPandas()

# 2. Prepare Data for Training
# Target: is_high_risk (1 = Bad, 0 = Good)
# Features: total_lifetime_orders, count_unpaid, debt_ratio, avg_order_value
# Note: We drop ID and date columns as they are not predictive features
X = risk_df[['total_lifetime_orders', 'count_unpaid', 'debt_ratio', 'avg_order_value']].fillna(0)
y = risk_df['is_high_risk']

# Split into Training (80%) and Testing (20%) sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Start MLflow Run (Tracks experiments)
with mlflow.start_run(run_name="Risk_Model_v1"):
    
    # A. Train the Model
    print("Training Random Forest Model...")
    # n_estimators = number of trees
    rf = RandomForestClassifier(n_estimators=100, max_depth=5)
    rf.fit(X_train, y_train)
    
    # B. Test the Model
    predictions = rf.predict(X_test)
    
    # C. Calculate Metrics
    acc = accuracy_score(y_test, predictions)
    prec = precision_score(y_test, predictions, zero_division=0)
    rec = recall_score(y_test, predictions, zero_division=0)
    
    print(f"✅ Model Accuracy: {acc:.2f}")
    print(f"⚠️ Precision (Caught Fraud correctly): {prec:.2f}")
    print(f"🔎 Recall (Did we miss any fraud?): {rec:.2f}")
    
    # D. Log everything to MLflow
    mlflow.log_metric("accuracy", acc)
    mlflow.log_metric("precision", prec)
    mlflow.log_metric("recall", rec)
    mlflow.sklearn.log_model(rf, "risk_model")
    
    print("\nModel saved to MLflow! Ready for deployment.")
