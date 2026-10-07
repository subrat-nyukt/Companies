import pandas as pd
import numpy as np
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.linear_model import LinearRegression

# 1. Create a simulated dataset
np.random.seed(42)
n_samples = 15

# Create base features
data = {
    'Age': np.random.randint(22, 60, n_samples),
    'Income': np.random.randint(30000, 120000, n_samples),
}
df = pd.DataFrame(data)

# Simulate Credit Score based heavily on Income and slightly on Age
df['Credit_Score'] = 400 + (df['Age'] * 1.5) + (df['Income'] * 0.003) + np.random.normal(0, 15, n_samples)
df['Credit_Score'] = df['Credit_Score'].clip(300, 850).round()

# 2. Introduce MAR (Missing At Random) missingness.
# Rule: If Income is less than 70,000, there is a high chance the Credit Score is missing.
# The missingness depends entirely on the OBSERVED 'Income' variable, which makes it MAR.
df_missing = df.copy()
missing_mask = (df_missing['Income'] < 70000) & (np.random.rand(n_samples) < 0.8)
df_missing.loc[missing_mask, 'Credit_Score'] = np.nan

print("--- 1. Original Dataset (With MAR Missing Values) ---")
print(df_missing)
print("\nTotal Missing Credit Scores:", df_missing['Credit_Score'].isna().sum())

# 3. Apply MICE (IterativeImputer)
print("\n--- 2. Running MICE Imputation ---")
# MICE uses a regression model (LinearRegression here) to predict missing values based on other columns
mice_imputer = IterativeImputer(estimator=LinearRegression(), random_state=42, max_iter=10)

# Fit and transform the data
imputed_data = mice_imputer.fit_transform(df_missing)

# Convert back to DataFrame for readability
df_imputed = pd.DataFrame(imputed_data, columns=df_missing.columns)
df_imputed['Credit_Score'] = df_imputed['Credit_Score'].round()

print("\n--- 3. Dataset After MICE Imputation ---")
print(df_imputed)

print("\n--- 4. Let's see how well MICE did! ---")
# Compare the True hidden values vs the MICE imputed values
missing_indices = df_missing[df_missing['Credit_Score'].isna()].index
comparison = pd.DataFrame({
    'Income': df.loc[missing_indices, 'Income'],
    'True_Credit_Score (Hidden)': df.loc[missing_indices, 'Credit_Score'],
    'MICE_Imputed_Score': df_imputed.loc[missing_indices, 'Credit_Score']
})
print(comparison)
