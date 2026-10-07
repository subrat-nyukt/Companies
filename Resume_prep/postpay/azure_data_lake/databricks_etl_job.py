import pandas as pd
import os
import glob
from datetime import datetime

# Simulating Databricks Notebook Environment
BRONZE_PATH = "azure_data_lake/bronze"
SILVER_PATH = "azure_data_lake/silver"
GOLD_PATH = "azure_data_lake/gold"

# --- HELPER FUNCTIONS ---
def display_table(df, name):
    print(f"\n[Databricks] Displaying {name} ({len(df)} rows):")
    print(df.head(5))

# --- STEP 1: READ FROM DATA LAKE (Bronze) ---
print("[Databricks] --- Step 1: Reading Raw Data (Bronze) ---")

# In real Databricks: spark.read.format("csv").load(f"/mnt/datalake/bronze/{table}/*.csv")
# Simulation: glob for latest CSV
def get_latest_file(path_pattern):
    list_of_files = glob.glob(path_pattern)
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)

kna1_file = get_latest_file(f"{BRONZE_PATH}/KNA1_*.csv")
vbak_file = get_latest_file(f"{BRONZE_PATH}/VBAK_*.csv")

if not kna1_file or not vbak_file:
    print("[Databricks] Error: No raw data found in Data Lake Bronze.")
    exit(1)

df_kna1_bronze = pd.read_csv(kna1_file)
df_vbak_bronze = pd.read_csv(vbak_file)
display_table(df_kna1_bronze, "df_kna1_bronze")

# --- STEP 2: TRANSFORM TO SILVER (Clean & Standardize) ---
print("\n[Databricks] --- Step 2: Transforming -> Silver ---")

# 2a. Clean Customers (KNA1)
# Remove rows with null names
df_kna1_silver = df_kna1_bronze.dropna(subset=['NAME1']).copy()
# Standardize Country codes
df_kna1_silver['LAND1'] = df_kna1_silver['LAND1'].str.upper()

# 2b. Clean Sales (VBAK)
# Remove duplicates
df_vbak_silver = df_vbak_bronze.drop_duplicates().copy()
# Convert Date
df_vbak_silver['AUDAT'] = pd.to_datetime(df_vbak_silver['AUDAT'])
df_vbak_silver['NETWR'] = pd.to_numeric(df_vbak_silver['NETWR'])

# Save to Silver (Simulating Delta Lake write)
os.makedirs(SILVER_PATH, exist_ok=True)
df_kna1_silver.to_parquet(f"{SILVER_PATH}/clean_customers.parquet")
df_vbak_silver.to_parquet(f"{SILVER_PATH}/clean_sales.parquet")
print(f"[Databricks] Write Success: Saved clean tables to {SILVER_PATH} (Parquet format)")

# --- STEP 3: AGGREGATE TO GOLD (Business Logic) ---
print("\n[Databricks] --- Step 3: Aggregating -> Gold ---")

# Join Sales & Customers
# SQL Equivalent:
# SELECT c.NAME1, c.LAND1, SUM(s.NETWR)
# FROM clean_sales s
# JOIN clean_customers c ON s.KUNNR = c.KUNNR
# GROUP BY c.NAME1, c.LAND1

df_gold = pd.merge(df_vbak_silver, df_kna1_silver, on='KUNNR', how='inner')

# Calculate KPI: Total Sales per Country
df_gold_agg = df_gold.groupby(['LAND1', 'REGIO']).agg(
    Total_Sales=('NETWR', 'sum'),
    Order_Count=('VBELN', 'count')
).reset_index()

display_table(df_gold_agg, "df_gold_agg")

# Save to Gold
os.makedirs(GOLD_PATH, exist_ok=True)
gold_file = f"{GOLD_PATH}/country_sales_summary.csv"
df_gold_agg.to_csv(gold_file, index=False)

print(f"\n[Databricks] JOB COMPLETE. Final Gold Table available at: {gold_file}")
print("[Databricks] Power BI can now connect to this Gold table.")
