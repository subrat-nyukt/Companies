import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

# Ensure we're working in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def generate_merchants(num_merchants=50):
    merchant_ids = [f"MERCH_{str(i).zfill(4)}" for i in range(1, num_merchants + 1)]
    categories = ['Retail', 'Digital Goods', 'Utilities', 'Travel']
    
    merchants = pd.DataFrame({
        'merchant_id': merchant_ids,
        'category': [random.choice(categories) for _ in range(num_merchants)],
        'fee_rate': [random.uniform(0.01, 0.03) for _ in range(num_merchants)] # 1-3% fee
    })
    
    merchants.to_csv('merchants.csv', index=False)
    print(f"Generated {num_merchants} merchants in merchants.csv")
    return merchants

def generate_transactions(merchants_df, num_transactions=2000):
    providers = ['MTN_MOMO', 'AIRTEL_MONEY', 'ORANGE_MONEY', 'MPESA']
    statuses = ['SUCCESS'] * 90 + ['FAILED'] * 8 + ['PENDING'] * 2 # 90% success rate
    
    transactions = []
    
    start_date = datetime.now() - timedelta(days=30)
    
    for i in range(num_transactions):
        txn_id = f"TXN_{str(random.randint(100000, 999999))}"
        merchant_id = random.choice(merchants_df['merchant_id'].tolist())
        amount = round(random.uniform(10.0, 5000.0), 2)
        provider = random.choice(providers)
        status = random.choice(statuses)
        
        # Random time in the last 30 days
        random_seconds = random.randint(0, 30 * 24 * 60 * 60)
        timestamp = start_date + timedelta(seconds=random_seconds)
        
        transactions.append({
            'transaction_id': txn_id,
            'merchant_id': merchant_id,
            'amount': amount,
            'currency': 'XOF', # CFA Franc, common in Ecobank regions
            'provider': provider,
            'status': status,
            'timestamp': timestamp.isoformat()
        })
        
    df = pd.DataFrame(transactions)
    df.to_csv('transactions.csv', index=False)
    print(f"Generated {num_transactions} transactions in transactions.csv")

if __name__ == "__main__":
    print("Generating simulated data for Ecobank project...")
    merchants = generate_merchants()
    generate_transactions(merchants)
    print("Data generation complete.")
