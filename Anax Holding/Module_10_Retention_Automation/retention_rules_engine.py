import pandas as pd
from datetime import datetime
import json
import os

# --- RETENTION ENGINE CONFIGURATION ---
FREE_MARGIN_THRESHOLD = 0.20  # 20%
INACTIVITY_DAYS_THRESHOLD = 14 # 14 Days

# Mock API Endpoint (Using a free public testing webhook)
# In production, this would be the Anax Capital CRM API (e.g., Salesforce / HubSpot / SendGrid)
CRM_WEBHOOK_URL = "https://httpbin.org/post"

def evaluate_retention_rules(csv_path):
    print("1. Loading Live Trading Accounts...")
    df = pd.read_csv(csv_path)
    
    # --- RULE 1: Financial Calculations (Free Margin) ---
    # Free Margin = Equity - Used Margin
    # Free Margin % = Free Margin / Equity
    df['free_margin'] = df['equity'] - df['used_margin']
    df['free_margin_pct'] = df['free_margin'] / df['equity']
    
    # --- RULE 2: Time Calculations (Inactivity) ---
    current_date = datetime.now()
    df['last_trade_date'] = pd.to_datetime(df['last_trade_date'])
    df['days_since_last_trade'] = (current_date - df['last_trade_date']).dt.days
    
    print("2. Firing Retention Engine Rules...")
    # Flag 1: Margin Call Warning (Free Margin < 20%)
    margin_users = df[df['free_margin_pct'] < FREE_MARGIN_THRESHOLD]
    
    # Flag 2: Inactive Warning (Not traded in > 14 days)
    inactive_users = df[df['days_since_last_trade'] > INACTIVITY_DAYS_THRESHOLD]
    
    hit_list = pd.concat([margin_users, inactive_users]).drop_duplicates(subset=['client_id'])
    
    print(f"Discovered {len(hit_list)} clients at risk of Churning!")
    return hit_list

def trigger_crm_automation(hit_list):
    """
    Simulates sending payloads to a CRM API to trigger retention emails or sales calls.
    """
    print("\n3. Triggering CRM Automations via REST API...")
    import requests # Standard library for API calls
    
    success_count = 0
    
    for index, client in hit_list.iterrows():
        # Determine the reason for the trigger to customize the email copy!
        reason = []
        if client['free_margin_pct'] < FREE_MARGIN_THRESHOLD:
            reason.append("MARGIN_WARNING")
        if client['days_since_last_trade'] > INACTIVITY_DAYS_THRESHOLD:
            reason.append("INACTIVE_CHURN_RISK")
            
        payload = {
            "client_id": client['client_id'],
            "equity": client['equity'],
            "free_margin_pct": round(client['free_margin_pct'], 4),
            "days_inactive": client['days_since_last_trade'],
            "automation_triggers": reason,
            "action": "SEND_RETENTION_BONUS_EMAIL"
        }
        
        try:
            # Pushing to the CRM API
            response = requests.post(CRM_WEBHOOK_URL, json=payload, timeout=5)
            if response.status_code == 200:
                success_count += 1
                # We print out the raw JSON payload to prove our backend works!
                print(f"Automated API Triggered for {client['client_id']} -> Reason: {reason}")
        except Exception as e:
            print(f"Failed to trigger API for {client['client_id']}: {e}")

    print(f"\nExecution Complete. Successfully triggered {success_count} CRM workflows.")

if __name__ == "__main__":
    file_path = "Data/live_trading_accounts.csv"
    if not os.path.exists(file_path):
        print(f"Error: Run generate_trading_accounts.py first! Could not find {file_path}")
    else:
        churn_risk_clients = evaluate_retention_rules(file_path)
        trigger_crm_automation(churn_risk_clients)
