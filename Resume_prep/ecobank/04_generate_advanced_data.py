import pandas as pd
import random
from datetime import datetime, timedelta
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def generate_corporate_merchants():
    """Generates the Parent/Headquarters details"""
    print("Generating Corporate Merchants...")
    corp_ids = [f"CORP_{str(i).zfill(3)}" for i in range(1, 21)] # 20 corporate parents
    categories = ['Supermarket Chain', 'Gas Stations', 'Fast Food Franchise', 'Pharmacy']
    
    corps = pd.DataFrame({
        'corporate_id': corp_ids,
        'legal_name': [f"Company {i} LLC" for i in range(1, 21)],
        'category': [random.choice(categories) for _ in range(20)],
        'corporate_fee_rate': [random.uniform(0.015, 0.025) for _ in range(20)] # 1.5% to 2.5% fee
    })
    corps.to_csv('corporate_merchants.csv', index=False)
    return corps

def generate_merchant_branches(corps_df):
    """Generates 1 to 5 branches for each Corporate Merchant"""
    print("Generating Merchant Branches...")
    branches = []
    branch_counter = 1
    
    for _, corp in corps_df.iterrows():
        num_branches = random.randint(1, 5)
        for b in range(num_branches):
            branches.append({
                'branch_id': f"BR_{str(branch_counter).zfill(4)}",
                'corporate_id': corp['corporate_id'],
                'branch_name': f"{corp['legal_name']} - Location {b+1}",
                'city': random.choice(['Lagos', 'Abuja', 'Accra', 'Nairobi', 'Dakar'])
            })
            branch_counter += 1
            
    df = pd.DataFrame(branches)
    df.to_csv('merchant_branches.csv', index=False)
    return df

def generate_adv_transactions(branches_df):
    """Generates transactions mapped to specific branches"""
    print("Generating Advanced Transactions...")
    providers = ['MTN_MOMO', 'AIRTEL_MONEY', 'ORANGE_MONEY']
    statuses = ['SUCCESS'] * 90 + ['FAILED'] * 8 + ['PENDING'] * 2
    
    transactions = []
    start_date = datetime.now() - timedelta(days=7) # Transactions over the last 7 days
    
    for i in range(5000): # 5000 total transactions
        branch = branches_df.sample(1).iloc[0]
        
        transactions.append({
            'transaction_id': f"TXN_{str(random.randint(1000000, 9999999))}",
            'branch_id': branch['branch_id'],
            'corporate_id': branch['corporate_id'], # We include corporate_id here to make database joins easier
            'amount': round(random.uniform(10.0, 2000.0), 2),
            'provider': random.choice(providers),
            'status': random.choice(statuses),
            'timestamp': (start_date + timedelta(minutes=random.randint(0, 10000))).isoformat()
        })
        
    df = pd.DataFrame(transactions)
    df.to_csv('advanced_transactions.csv', index=False)
    return df

if __name__ == "__main__":
    print("--- Starting Advanced Data Generation ---")
    corps = generate_corporate_merchants()
    branches = generate_merchant_branches(corps)
    generate_adv_transactions(branches)
    print("--- Data Generation Complete! ---")
    print("You now have 3 new CSV files: corporate_merchants.csv, merchant_branches.csv, and advanced_transactions.csv")
