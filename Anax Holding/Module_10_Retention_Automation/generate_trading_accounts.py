import pandas as pd
import random
from datetime import datetime, timedelta
import os

def generate_mock_accounts(num_records=500):
    """
    Generates a mock dataset reflecting the live state of trading accounts.
    Includes edge cases for margin calls and inactive clients.
    """
    print(f"Generating {num_records} mock trading accounts...")
    
    data = []
    current_date = datetime.now()
    
    for i in range(1, num_records + 1):
        client_id = f"ANX-{1000 + i}"
        
        # 1. Financial Mocking (Equity & Margin)
        # Random equity between $100 and $1,000,000
        equity = round(random.uniform(100, 1000000), 2)
        
        # Decide if this user is struggling (low free margin) or healthy
        status_category = random.choices(['healthy', 'margin_call', 'inactive'], weights=[0.7, 0.15, 0.15])[0]
        
        if status_category == 'margin_call':
            # Used margin is very high, leaving less than 20% free margin
            used_margin = equity * random.uniform(0.85, 0.99)
            last_trade_date = current_date - timedelta(days=random.randint(0, 5))
        elif status_category == 'inactive':
            # Healthy margin, but hasn't traded in a long time
            used_margin = equity * random.uniform(0.10, 0.40)
            last_trade_date = current_date - timedelta(days=random.randint(15, 60))
        else: # healthy
            # Healthy margin and recent trading
            used_margin = equity * random.uniform(0.10, 0.50)
            last_trade_date = current_date - timedelta(days=random.randint(0, 5))
            
        used_margin = round(used_margin, 2)
        
        data.append({
            "client_id": client_id,
            "equity": equity,
            "used_margin": used_margin,
            "last_trade_date": last_trade_date.strftime("%Y-%m-%d")
        })

    df = pd.DataFrame(data)
    
    # Save the file
    output_dir = "Data"
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "live_trading_accounts.csv")
    df.to_csv(file_path, index=False)
    
    print(f"Successfully created: {file_path}")
    print(df.head(10))

if __name__ == "__main__":
    generate_mock_accounts()
