import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# 1. Generate Synthetic Dataset
print("Generating synthetic dataset...")
np.random.seed(42)
n_samples = 5000

data = {
    # Customer Details
    'Age_of_driver': np.random.randint(21, 65, n_samples),
    'Years_of_driving_experience': np.random.randint(1, 40, n_samples),
    'Gender': np.random.choice([0, 1], n_samples), # 0: Female, 1: Male
    'Marital_status': np.random.choice(['Single', 'Married', 'Divorced'], n_samples),
    
    # Platform Earnings
    'Avg_weekly_earnings_3m': np.random.normal(300, 80, n_samples),
    'Acceptance_rate_1m': np.random.uniform(0.6, 1.0, n_samples),
    'Cancellation_rate_1m': np.random.uniform(0.0, 0.3, n_samples),
    'Passenger_rating': np.random.uniform(3.5, 5.0, n_samples),
    'Total_hours_online_1m': np.random.normal(200, 50, n_samples),
    
    # Telematics Behavior
    'Hard_braking_events_1m': np.random.poisson(2, n_samples),
    'Speeding_violations_1m': np.random.poisson(1, n_samples),
    'Late_night_driving_hours_1m': np.random.normal(20, 10, n_samples),
    
    # Financial History
    'Bureau_credit_score': np.random.normal(650, 100, n_samples),
    'Past_loan_defaults_count': np.random.poisson(0.5, n_samples),
    'Mobile_money_tx_volume_3m': np.random.normal(1500, 500, n_samples),
    
    # Loan Origination
    'Requested_loan_principal': np.random.uniform(5000, 25000, n_samples),
    'Downpayment_percentage': np.random.uniform(0.1, 0.3, n_samples),
    
    # Target Variable: Is_Risky (1 = Default/Risky, 0 = Good Standing)
    # Creating a synthetic relationship
}

df = pd.DataFrame(data)

# Calculate risk probability based on features (synthetic logic)
risk_prob = (
    (df['Past_loan_defaults_count'] * 0.3) +
    (df['Cancellation_rate_1m'] * 0.2) +
    (df['Speeding_violations_1m'] * 0.1) +
    (df['Hard_braking_events_1m'] * 0.1) -
    (df['Bureau_credit_score'] / 1000 * 0.2) -
    (df['Acceptance_rate_1m'] * 0.1) -
    (df['Passenger_rating'] / 5 * 0.1)
)

# Add some noise to make it realistic
risk_prob += np.random.normal(0, 0.1, n_samples)
df['Is_Risky'] = (risk_prob > df['Is_Risky'].median() if 'Is_Risky' in df else (risk_prob > np.median(risk_prob))).astype(int)

# Ensure strictly non-negative values for certain columns
df['Avg_weekly_earnings_3m'] = df['Avg_weekly_earnings_3m'].clip(lower=0)
df['Total_hours_online_1m'] = df['Total_hours_online_1m'].clip(lower=0)
df['Late_night_driving_hours_1m'] = df['Late_night_driving_hours_1m'].clip(lower=0)

print(f"Dataset generated with {df.shape[0]} rows and {df.shape[1]} columns.")
df.to_csv("moove_synthetic_driver_data.csv", index=False)
print("Saved to 'moove_synthetic_driver_data.csv'.\n")

# 2. Data Preprocessing
print("Preprocessing data...")
X = df.drop('Is_Risky', axis=1)
y = df['Is_Risky']

# Encode Categorical
categorical_cols = X.select_dtypes(include=['object']).columns
for col in categorical_cols:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col])

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Scale Numeric Features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

features = X.columns

# 3. Train XGBoost Model
print("Training XGBoost Classifier...")
# Handle potential class imbalance
scale_pos_weight = (len(y_train) - sum(y_train)) / sum(y_train)

xgb_model = xgb.XGBClassifier(
    objective='binary:logistic',
    n_estimators=100,
    learning_rate=0.1,
    max_depth=4,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    use_label_encoder=False,
    eval_metric='logloss'
)

xgb_model.fit(X_train_scaled, y_train)

# 4. Evaluation
print("\n--- Model Evaluation ---")
y_pred = xgb_model.predict(X_test_scaled)
y_prob = xgb_model.predict_proba(X_test_scaled)[:, 1]

print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(f"ROC-AUC Score: {roc_auc_score(y_test, y_prob):.4f}\n")
print("Classification Report:")
print(classification_report(y_test, y_pred))

# 5. Feature Importance
print("\n--- Top Feature Importances ---")
importances = xgb_model.feature_importances_
feature_importance_df = pd.DataFrame({
    'Feature': features,
    'Importance': importances
}).sort_values(by='Importance', ascending=False)

print(feature_importance_df.head(10).to_markdown(index=False))

feature_importance_df.to_csv("moove_xgboost_feature_importance.csv", index=False)
print("\nFeature importances saved to 'moove_xgboost_feature_importance.csv'.")
