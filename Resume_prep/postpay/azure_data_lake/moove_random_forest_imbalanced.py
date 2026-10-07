import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
from sklearn.ensemble import RandomForestClassifier
import warnings
warnings.filterwarnings('ignore')

# 1. Load the generated dataset
df = pd.read_csv("moove_synthetic_driver_data.csv")

# 2. Imbalance injection (for demonstration purposes)
# Let's say we purposely make 'Is_Risky' = 1 only 5% of the data
# We'll undersample the Risky instances to artificially create this imbalance
risky = df[df['Is_Risky'] == 1]
non_risky = df[df['Is_Risky'] == 0]

# Sample only 5% of the total size for the risky class
n_risky_samples = int(len(df) * 0.05)
risky_sampled = risky.sample(n=n_risky_samples, random_state=42)

# Combine back and shuffle
df_imbalanced = pd.concat([non_risky, risky_sampled]).sample(frac=1, random_state=42).reset_index(drop=True)
print(f"Imbalanced Dataset created: {df_imbalanced.shape[0]} rows.")
print("Class Distribution:")
print(df_imbalanced['Is_Risky'].value_counts(normalize=True) * 100)

# 3. Data Preprocessing
X = df_imbalanced.drop('Is_Risky', axis=1)
y = df_imbalanced['Is_Risky']

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


# 4. Train Random Forest (Handling Imbalance)
print("\nTraining Random Forest Classifier (with class_weight='balanced')...")

# The magic parameter for Random Forest is class_weight="balanced"
# This automatically adjusts weights inversely proportional to class frequencies.
rf_model = RandomForestClassifier(
    n_estimators=100,
    class_weight='balanced', # Crucial for handling imbalanced datasets (e.g., 95% / 5%)
    max_depth=10,            # Limiting depth helps prevent overfitting on the minority class
    min_samples_leaf=5,      # Requiring more samples per leaf avoids isolating outliers
    random_state=42,
    n_jobs=-1                # Use all CPU cores
)

rf_model.fit(X_train_scaled, y_train)

# 5. Evaluation
print("\n--- Model Evaluation ---")
y_pred = rf_model.predict(X_test_scaled)
y_prob = rf_model.predict_proba(X_test_scaled)[:, 1]

print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(f"ROC-AUC Score: {roc_auc_score(y_test, y_prob):.4f}\n")
print("Classification Report:")
print(classification_report(y_test, y_pred))
