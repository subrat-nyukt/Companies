import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Constraints & Settings
NUM_USERS = 5000
CAMPAIGNS = ['Google_Ads', 'Meta_Ads', 'Affiliate_Network', 'Organic']
CAMPAIGN_WEIGHTS = [0.4, 0.3, 0.2, 0.1]

# Set a seed
np.random.seed(42)

def generate_mock_data():
    print("Generating mock CRM and Trading data for Anax Capital...")
    
    # Generate User IDs
    user_ids = [f"USR{10000 + i}" for i in range(NUM_USERS)]
    
    # Generate Campaigns
    campaigns = np.random.choice(CAMPAIGNS, NUM_USERS, p=CAMPAIGN_WEIGHTS)
    
    # Generate Lead Dates (spread across the last 6 months)
    base_date = datetime.now() - timedelta(days=180)
    lead_dates = [base_date + timedelta(days=np.random.randint(0, 150)) for _ in range(NUM_USERS)]
    
    # Generate Deposit Dates
    # Not all leads will deposit (assume 30% conversion to deposit)
    has_deposited = np.random.choice([True, False], NUM_USERS, p=[0.3, 0.7])
    
    first_deposit_dates = []
    first_trade_dates = []
    total_volumes = []
    
    for i in range(NUM_USERS):
        if has_deposited[i]:
            # Deposit happens 1 to 14 days after lead
            deposit_delay = np.random.randint(1, 15)
            deposit_date = lead_dates[i] + timedelta(days=deposit_delay)
            first_deposit_dates.append(deposit_date)
            
            # 80% of depositors will trade
            if np.random.rand() < 0.8:
                # Trade happens 0 to 5 days after deposit
                trade_delay = np.random.randint(0, 6)
                trade_date = deposit_date + timedelta(days=trade_delay)
                first_trade_dates.append(trade_date)
                
                # Trading volume heavily skewed (few whales, many small traders)
                volume = np.round(np.random.lognormal(mean=2, sigma=1.5) * 10, 2)
                total_volumes.append(volume)
            else:
                first_trade_dates.append(pd.NaT)
                total_volumes.append(0.0)
                
        else:
            first_deposit_dates.append(pd.NaT)
            first_trade_dates.append(pd.NaT)
            total_volumes.append(0.0)

    # Create DataFrame
    df = pd.DataFrame({
        'user_id': user_ids,
        'marketing_campaign': campaigns,
        'lead_date': lead_dates,
        'first_deposit_date': first_deposit_dates,
        'first_trade_date': first_trade_dates,
        'total_volume_traded_30_days': total_volumes
    })
    
    # Format dates for CSV output
    df['lead_date'] = pd.to_datetime(df['lead_date']).dt.strftime('%Y-%m-%d')
    df['first_deposit_date'] = pd.to_datetime(df['first_deposit_date']).dt.strftime('%Y-%m-%d')
    df['first_trade_date'] = pd.to_datetime(df['first_trade_date']).dt.strftime('%Y-%m-%d')
    
    # Save to CSV
    output_path = "crm_conversion_data.csv"
    df.to_csv(output_path, index=False)
    print(f"Data generated successfully! File saved to {output_path}")

if __name__ == "__main__":
    generate_mock_data()
