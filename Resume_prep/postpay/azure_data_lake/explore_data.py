import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def perform_eda():
    # Load dataset (Generated from your SQL logic)
    df = pd.read_csv('customer_risk_features.csv')
    
    print("--- 1. Dataset Overview ---")
    print(f"Total Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print("\n--- 2. Target Distribution (Class Balance) ---")
    print(df['is_default'].value_counts(normalize=True))
    
    print("\n--- 3. Correlation with Target ---")
    # Simple correlation with numeric columns
    numeric_cols = df.select_dtypes(include=['number']).columns
    corr = df[numeric_cols].corr()['is_default'].sort_values()
    print(corr)
    
    print("\n--- 4. Risk by Device Type ---")
    print(df.groupby('device_type')['is_default'].mean().sort_values(ascending=False))

if __name__ == "__main__":
    perform_eda()
