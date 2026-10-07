import pandas as pd
from datetime import datetime
import os

# Set paths to the current directory
script_dir = os.path.dirname(os.path.abspath(__file__))
crm_path = os.path.join(script_dir, 'crm_wallets.json')
mt5_path = os.path.join(script_dir, 'mt5_balances.csv')

def perform_eod_reconciliation():
    # 1. Load data
    print("Loading CRM and MT5 data...")
    crm_df = pd.read_json(crm_path)
    mt5_df = pd.read_csv(mt5_path)

    # 2. Merge DataFrames on user_id to compare side-by-side
    # We use an 'outer' join so we don't miss users that exist in only one system
    recon_df = pd.merge(crm_df, mt5_df, on='user_id', how='outer', suffixes=('_crm', '_mt5'))

    alerts = []

    # 3. Identify discrepancies
    for index, row in recon_df.iterrows():
        user_id = int(row['user_id'])
        
        # Scenario A: Exists in MT5 but missing in CRM Wallet
        if pd.isna(row['wallet_id']):
            alerts.append({
                "severity": "HIGH",
                "type": "MISSING_IN_CRM",
                "user_id": user_id,
                "message": f"User {user_id} found in MT5 but missing a CRM wallet record. (Unmapped deposit?)"
            })
            
        # Scenario B: Exists in CRM but missing in MT5 Trading Account
        elif pd.isna(row['mt5_account_id']):
            alerts.append({
                "severity": "HIGH",
                "type": "MISSING_IN_MT5",
                "user_id": user_id,
                "message": f"User {user_id} has CRM balance but is missing from MT5 database."
            })
            
        # Scenario C: Both exist, but Balances do not match
        elif row['balance'] != row['mt5_balance']:
            diff = abs(row['balance'] - row['mt5_balance'])
            alerts.append({
                "severity": "CRITICAL",
                "type": "BALANCE_MISMATCH",
                "user_id": user_id,
                "message": f"Discrepancy of {diff:.2f} {row['currency_crm']} for User {user_id}. (CRM: {row['balance']}, MT5: {row['mt5_balance']})"
            })

    # 4. Trigger Alerts
    trigger_slack_alert_simulation(alerts)

def trigger_slack_alert_simulation(alerts):
    """
    Simulates sending a formatted alert payload to a Slack or Microsoft Teams webhook.
    """
    print("\n" + "="*70)
    print("[ALERT] EOD RECONCILIATION ALERTS (Simulated Slack/Teams Output) [ALERT]")
    print("="*70)
    
    if not alerts:
        print("✅ No discrepancies found. CRM and MT5 data are 100% matched.")
        print("="*70)
        return
        
    for alert in alerts:
        # Visual cues based on severity
        icon = "[CRITICAL]" if alert['severity'] == "CRITICAL" else "[WARNING]"
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {icon} [{alert['type']}]")
        print(f"    > {alert['message']}")
        print("-" * 70)
        
    print(f"Total Anomalies Flagged: {len(alerts)}")
    print("Action Required: Please investigate anomalies before market open tomorrow.")
    print("="*70 + "\n")

if __name__ == "__main__":
    perform_eod_reconciliation()
