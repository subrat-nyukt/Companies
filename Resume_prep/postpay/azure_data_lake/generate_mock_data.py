import pandas as pd
import numpy as np
import random

def generate_mock_data(n_customers=1000):
    np.random.seed(42)
    
    data = []
    
    for i in range(n_customers):
        cust_id = f"CUST_{i:04d}"
        
        # 1. Velocity Features (Buying pattern)
        # Randomly assign if they are a heavy user or light user
        user_type = np.random.choice(['light', 'heavy', 'new'], p=[0.5, 0.3, 0.2])
        
        if user_type == 'heavy':
            orders_1m = np.random.randint(1, 10)
            avg_amt = np.random.normal(500, 100)
        elif user_type == 'light':
            orders_1m = np.random.randint(0, 3)
            avg_amt = np.random.normal(200, 50)
        else:
            orders_1m = 0
            avg_amt = 0
            
        # 2. Risk Signals (The SQL logic calculates these)
        # unpaid orders in history
        unpaid_history = np.random.choice([0, 1, 2], p=[0.8, 0.15, 0.05])
        
        # 3. Device & Cards
        device = np.random.choice(['iPhone', 'Android', 'Windows', 'Unknown'], p=[0.5, 0.4, 0.05, 0.05])
        card_type = np.random.choice(['Debit', 'Credit', 'Amex'], p=[0.7, 0.25, 0.05])
        
        # 4. Target Variable (Did they default on the NEXT order?)
        # Logic: High unpaid history + Android + Debit = Higher Risk (Hypothetically)
        risk_score = 0
        if unpaid_history > 0: risk_score += 0.4
        if device == 'Android': risk_score += 0.1
        if card_type == 'Debit': risk_score += 0.1
        if orders_1m > 5: risk_score += 0.2 # Velocity risk
        
        noise = np.random.normal(0, 0.2)
        final_prob = 0.1 + risk_score + noise
        final_prob = max(0, min(1, final_prob))
        
        is_default = 1 if np.random.random() < final_prob else 0
        
        # Row corresponding to the SQL output
        row = {
            'customer_id': cust_id,
            'No_of_instalment_plan_1m': orders_1m,
            'No_of_instalment_plan_3m': orders_1m * np.random.randint(1, 4),
            'Avg_ins_amt_1m': round(avg_amt, 2),
            'No_of_unpaid_orders_hist': unpaid_history,
            'device_type': device,
            'card_type': card_type,
            'No_of_approvals_12m': np.random.randint(0, 20),
            'is_default': is_default # TARGET VARIABLE
        }
        data.append(row)
        
    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    print("Generating mock dataset based on SQL schema...")
    df = generate_mock_data(1000)
    df.to_csv('customer_risk_features.csv', index=False)
    print(f"Saved {len(df)} rows to customer_risk_features.csv")
    print("\nSample Data:")
    print(df.head().to_markdown(index=False, numalign="left", stralign="left"))
