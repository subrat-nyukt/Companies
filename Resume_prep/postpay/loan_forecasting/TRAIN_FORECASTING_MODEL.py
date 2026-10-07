# LOAN FORECASTING: MODEL TRAINING
import mlflow
import mlflow.sklearn
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score, precision_recall_curve

# 1. Load Data
print("Loading Forecasting Features...")
df = spark.table("default.model_forecasting_features").toPandas()

# 2. Prepare Features & Target
X = df[['frequency', 'recency', 'monetary', 'tenure']]
y = df['will_repeat_next_year']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Train with MLflow Tracking
with mlflow.start_run(run_name="Loan_Repeat_Forecast"):
    
    print("Training Forecast Model (Repeat Probability)...")
    clf = RandomForestClassifier(n_estimators=150, max_depth=7, random_state=42)
    clf.fit(X_train, y_train)
    
    # 4. Evaluate
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    
    # Calculate ROC-AUC and PR-AUC
    roc_auc = roc_auc_score(y_test, y_prob)
    pr_auc = average_precision_score(y_test, y_prob)
    
    print(f"✅ Model ROC-AUC: {roc_auc:.4f}")
    print(f"✅ Model PR-AUC: {pr_auc:.4f}")
    
    # Classification Report to see Recall and Precision
    print("\nClassification Report:\n", classification_report(y_test, y_pred))
    
    # --- Plotting the Precision-Recall Curve ---
    precision, recall, _ = precision_recall_curve(y_test, y_prob)
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, color='blue', lw=2, label=f'PR Curve (AUC = {pr_auc:.4f})')
    plt.xlabel('Recall (True Positive Rate)')
    plt.ylabel('Precision (Positive Predictive Value)')
    plt.title('Precision-Recall Curve (Imbalanced Data)')
    plt.legend(loc='lower left')
    plt.grid(True)
    
    # Save the plot and log it to MLflow
    pr_curve_path = "pr_curve.png"
    plt.savefig(pr_curve_path)
    mlflow.log_artifact(pr_curve_path)
    print(f"✅ Saved Precision-Recall curve to {pr_curve_path}")
    plt.close()
    
    # Log Metrics & Model
    mlflow.log_metric("roc_auc", roc_auc)
    mlflow.log_metric("pr_auc", pr_auc)
    mlflow.sklearn.log_model(clf, "loan_repeater_model")
    
    # Log parameters
    mlflow.log_param("n_estimators", 150)
    mlflow.log_param("max_depth", 7)

    print("\nModel Training Complete. Registered as 'loan_repeater_model' in MLflow.")
