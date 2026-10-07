import pandas as pd
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def run_advanced_reporting():
    print("Loading data...")
    try:
        txns = pd.read_csv('advanced_transactions.csv')
        branches = pd.read_csv('merchant_branches.csv')
        corps = pd.read_csv('corporate_merchants.csv')
    except FileNotFoundError:
        print("Please run 04_generate_advanced_data.py first.")
        return

    # Filter only successful transactions for settlement
    success_txns = txns[txns['status'] == 'SUCCESS'].copy()
    
    # --- The Database Join Simulation ---
    # 1. Join transactions to branches
    merged = pd.merge(success_txns, branches, on=['branch_id', 'corporate_id'], how='left')
    # 2. Join that result to the corporate details to get the fee rate
    merged = pd.merge(merged, corps, on='corporate_id', how='left')
    
    # Calculate processing fee and net settlement
    merged['fee_deducted'] = merged['amount'] * merged['corporate_fee_rate']
    merged['net_settlement'] = merged['amount'] - merged['fee_deducted']
    
    
    # --- REPORT 1: For the Branch Managers (Operational View) ---
    # They care about how much volume their specific store did.
    branch_report = merged.groupby(['branch_id', 'branch_name', 'city']).agg(
        total_transactions=('transaction_id', 'count'),
        gross_volume=('amount', 'sum')
    ).reset_index()
    
    branch_report['gross_volume'] = branch_report['gross_volume'].round(2)
    branch_report.to_csv('report_1_branch_performance.csv', index=False)
    
    
    # --- REPORT 2: For Ecobank Finance (Settlement View) ---
    # They care about the total payout they need to send to the Corporate bank account.
    corp_report = merged.groupby(['corporate_id', 'legal_name']).agg(
        active_branches=('branch_id', 'nunique'),
        total_transactions=('transaction_id', 'count'),
        gross_volume=('amount', 'sum'),
        total_fees_collected=('fee_deducted', 'sum'),
        final_payout_to_merchant=('net_settlement', 'sum')
    ).reset_index()
    
    # Format currency
    for col in ['gross_volume', 'total_fees_collected', 'final_payout_to_merchant']:
        corp_report[col] = corp_report[col].round(2)
        
    corp_report.to_csv('report_2_corporate_settlement.csv', index=False)
    
    print("\nReports Generated Successfully!")
    print("\n--- Preview: Top 3 Corporate Payouts ---")
    print(corp_report.sort_values(by='final_payout_to_merchant', ascending=False).head(3).to_string())

if __name__ == "__main__":
    run_advanced_reporting()
