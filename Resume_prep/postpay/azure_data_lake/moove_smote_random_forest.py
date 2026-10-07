import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
from sklearn.ensemble import RandomForestClassifier
from imblearn.over_sampling import SMOTE
import warnings
warnings.filterwarnings('ignore')

# 1. Load the generated dataset
df = pd.read_csv("moove_synthetic_driver_data.csv")

# 2. Imbalance injection (5% risky drivers)
risky = df[df['Is_Risky'] == 1]
non_risky = df[df['Is_Risky'] == 0]
n_risky_samples = int(len(df) * 0.05)
risky_sampled = risky.sample(n=n_risky_samples, random_state=42)
df_imbalanced = pd.concat([non_risky, risky_sampled]).sample(frac=1, random_state=42).reset_index(drop=True)

# 3. Data Preprocessing
X = df_imbalanced.drop('Is_Risky', axis=1)
y = df_imbalanced['Is_Risky']

categorical_cols = X.select_dtypes(include=['object']).columns
for col in categorical_cols:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col])

# Train-test split FIRST (Crucial: SMOTE only goes on training data)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"Original Training Class Distribution:\n{y_train.value_counts()}")

# Scale Numeric Features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 4. Apply SMOTE to Training Data ONLY
print("\nApplying SMOTE...")
smote = SMOTE(random_state=42)
X_train_smote, y_train_smote = smote.fit_resample(X_train_scaled, y_train)
print(f"SMOTE Training Class Distribution:\n{y_train_smote.value_counts()}")

# 5. Train Random Forest on SMOTE data
print("\nTraining Random Forest Classifier on SMOTE data...")
rf_model_smote = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,            
    min_samples_leaf=5,      
    random_state=42,
    n_jobs=-1                
)

rf_model_smote.fit(X_train_smote, y_train_smote)

# 6. Evaluation (on the pure, untouched test set)
print("\n--- Model Evaluation (SMOTE) ---")
y_pred = rf_model_smote.predict(X_test_scaled)
y_prob = rf_model_smote.predict_proba(X_test_scaled)[:, 1]

print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(f"ROC-AUC Score: {roc_auc_score(y_test, y_prob):.4f}\n")
print("Classification Report:")
print(classification_report(y_test, y_pred))
