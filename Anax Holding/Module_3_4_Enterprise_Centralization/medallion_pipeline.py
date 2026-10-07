import pandas as pd
import sqlite3
import os

# Define local paths
script_dir = os.path.dirname(os.path.abspath(__file__))
crm_path = os.path.join(script_dir, "crm_users.json")
mt5_path = os.path.join(script_dir, "mt5_deals.csv")
db_path = os.path.join(script_dir, "marketing_spend.db")

print("==================================================")
print("--- [BRONZE LAYER] INGEST RAW DATA ---")
print("==================================================")

# 1. Extract JSON (Mocking a CRM API or NoSQL export)
bronze_crm = pd.read_json(crm_path)
print(f"[OK] Loaded {len(bronze_crm)} user records from CRM JSON.")

# 2. Extract CSV (Mocking a raw MT5 Server export)
bronze_mt5 = pd.read_csv(mt5_path)
print(f"[OK] Loaded {len(bronze_mt5)} trading deals from MT5 CSV.")

# 3. Extract SQLite DB (Mocking a direct Azure SQL / PostgreSQL connection)
conn = sqlite3.connect(db_path)
bronze_marketing = pd.read_sql_query("SELECT * FROM marketing_campaigns", conn)
conn.close()
print(f"[OK] Loaded {len(bronze_marketing)} campaigns from Marketing SQL DB.")


print("\n==================================================")
print("--- [SILVER LAYER] CLEANSING & AGGREGATION ---")
print("==================================================")

# A. Clean CRM Data (Select only necessary columns for the profile)
silver_crm = bronze_crm[['user_id', 'kyc_status', 'campaign_id']].copy()
silver_crm['user_id'] = silver_crm['user_id'].astype(int)
print("[CLEAN] Cleaned CRM data. Selected KYC and Campaign ID.")

# B. Aggregate MT5 Deals (We need TOTAL profit per user, not individual deals)
silver_mt5 = bronze_mt5.groupby('user_id', as_index=False).agg(
    total_trading_profit=('profit', 'sum'),
    total_trade_volume=('volume', 'sum')
)
print("[AGGREGATE] Aggregated MT5 deals to calculate Total Trading Profit per User.")


print("\n==================================================")
print("--- [GOLD LAYER] 'THE GOLDEN RECORD' MULTI-JOIN ---")
print("==================================================")

# STEP 1: Join CRM Users with their MT5 Trading Activity 
gold_df = pd.merge(silver_crm, silver_mt5, on='user_id', how='left')

# STEP 2: Join the resulting profile with the Marketing Database to find Acquisition Cost
gold_df = pd.merge(gold_df, bronze_marketing, on='campaign_id', how='left')

# Fill missing numerical values with 0 (e.g., users who registered but haven't traded yet)
gold_df['total_trading_profit'] = gold_df['total_trading_profit'].fillna(0)
gold_df['ad_click_cost'] = gold_df['ad_click_cost'].fillna(0)

# Analytics: Calculate Client Net Value (How much they made us vs How much we spent to get them)
gold_df['client_net_value'] = gold_df['total_trading_profit'] - gold_df['ad_click_cost']

# Final Selection & Ordering
golden_client_profile = gold_df[
    ['user_id', 'kyc_status', 'platform', 'ad_click_cost', 'total_trading_profit', 'client_net_value']
].sort_values(by='client_net_value', ascending=False)

print("\n[GOLD] FINAL MEDALLION ARCHITECTURE OUTPUT: GOLDEN CLIENT PROFILES [GOLD]")
print(golden_client_profile.to_string(index=False))

# Dump Golden Record to disk
gold_path = os.path.join(script_dir, "golden_client_profile.csv")
golden_client_profile.to_csv(gold_path, index=False)
print(f"\n[SAVED] Saved Golden Table locally to: {gold_path}")
print("This table is now ready to be securely pushed into Azure Synapse & Power BI!")
