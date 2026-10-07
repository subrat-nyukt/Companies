import pandas as pd
import os
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def generate_settlement_report():
    print("Starting automated settlement reporting process...")
    
    try:
        # 1. Load Data (Extract)
        transactions = pd.read_csv('transactions.csv')
        merchants = pd.read_csv('merchants.csv')
        print(f"Loaded {len(transactions)} transactions and {len(merchants)} merchants.")
    except FileNotFoundError:
        print("Error: Data files not found. Please run 01_generate_mock_data.py first.")
        return

    # 2. Clean and Filter Data
    # Operations only cares about successful transactions for settlement
    successful_txns = transactions[transactions['status'] == 'SUCCESS'].copy()
    
    # Optional: Filter by specific date range (e.g., yesterday for daily settlement)
    # Using all data for this simulation
    
    # 3. Join Data (Transactions + Merchant Data to get feed rates)
    merged_data = pd.merge(successful_txns, merchants, on='merchant_id', how='left')
    
    # 4. Apply Business Logic (Transform)
    # Calculate Ecobank's processing fee
    merged_data['processing_fee'] = merged_data['amount'] * merged_data['fee_rate']
    
    # Calculate the final amount to settle to the merchant
    merged_data['settlement_amount'] = merged_data['amount'] - merged_data['processing_fee']

    # 5. Aggregate by Merchant
    settlement_summary = merged_data.groupby(['merchant_id', 'category']).agg(
        total_transactions=('transaction_id', 'count'),
        total_volume=('amount', 'sum'),
        total_fees_collected=('processing_fee', 'sum'),
        net_settlement=('settlement_amount', 'sum')
    ).reset_index()
    
    # Format currency columns for readability (optional, but good for operations)
    currency_cols = ['total_volume', 'total_fees_collected', 'net_settlement']
    for col in currency_cols:
         settlement_summary[col] = settlement_summary[col].round(2)

    # 6. Output (Load)
    output_filename = f'daily_settlement_report_{datetime.now().strftime("%Y%m%d")}.csv'
    settlement_summary.to_csv(output_filename, index=False)
    
    print("\n--- Summary Statistics ---")
    print(f"Total processing fees collected: {settlement_summary['total_fees_collected'].sum():.2f}")
    print(f"Total volume processed: {settlement_summary['total_volume'].sum():.2f}")
    print(f"\nReport generated successfully: {output_filename}")
    
    # Quick preview for the terminal
    print("\nPreview of top 5 settlements:")
    print(settlement_summary.sort_values(by='net_settlement', ascending=False).head().to_string())


if __name__ == "__main__":
     generate_settlement_report()
