import pandas as pd
import os

dir_path = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(dir_path, "flat_enterprise_lakehouse_export.csv")

print("==========================================================")
print("[START] Building MS Fabric Star Schema with SCD Type 2...")
print("==========================================================\n")

df_flat = pd.read_csv(input_path)

# ==========================================
# 1. BUILD DIMENSIONS (Lookup tables)
# ==========================================
print("-> Synthesizing DimClients (Injecting SCD 2 Columns)...")
# Get unique clients
dim_clients = df_flat[['client_id', 'client_country', 'kyc_status']].drop_duplicates().reset_index(drop=True)

# Generate Surrogate Key
dim_clients.insert(0, 'ClientKey', range(1, len(dim_clients) + 1))

# Append the absolute required SCD Type 2 Tracking Columns!
dim_clients['is_active'] = True
dim_clients['start_date'] = "2026-04-01"
dim_clients['end_date'] = "9999-12-31"

# !! INJECT A MOCK HISTORICAL ROW TO TEST IN POWER BI !!
print("-> Generating Mock Historical Data for Client ANX-120...")
mock_history = pd.DataFrame([{
    'ClientKey': len(dim_clients) + 1,
    'client_id': "ANX-120", 
    'client_country': "UAE",
    'kyc_status': "REJECTED", # Their OLD historical status
    'is_active': False,       # It is no longer active
    'start_date': "2025-01-01",
    'end_date': "2026-04-01"  
}])
dim_clients = pd.concat([dim_clients, mock_history], ignore_index=True)


print("-> Synthesizing DimInstruments...")
dim_instruments = df_flat[['instrument_symbol', 'instrument_type']].drop_duplicates().reset_index(drop=True)
dim_instruments.insert(0, 'InstrumentKey', range(1, len(dim_instruments) + 1))


print("-> Synthesizing DimDates (For Power BI Time Intelligence)...")
unique_dates = pd.to_datetime(df_flat['execution_date']).drop_duplicates().sort_values()
dim_dates = pd.DataFrame({
    'DateKey': unique_dates.dt.strftime('%Y%m%d').astype(int), 
    'FullDate': unique_dates,
    'Year': unique_dates.dt.year,
    'Month': unique_dates.dt.month,
    'DayOfWeek': unique_dates.dt.day_name()
}).reset_index(drop=True)


# ==========================================
# 2. BUILD THE FACT TABLE (The Measures)
# ==========================================
print("-> Synthesizing FactTrades (Tying the Foreign Keys together)...")

# Merge our new SCD Surrogate keys onto the flat table
fact_trades = df_flat.merge(dim_clients, on=['client_id', 'client_country', 'kyc_status'], how='left')
fact_trades = fact_trades.merge(dim_instruments, on=['instrument_symbol', 'instrument_type'], how='left')
fact_trades['DateKey'] = pd.to_datetime(fact_trades['execution_date']).dt.strftime('%Y%m%d').astype(int)

# Strip all text out of the fact table, leaving ONLY numbers and foreign keys!
fact_trades = fact_trades[[
    'trade_id', 
    'DateKey', 
    'ClientKey', 
    'InstrumentKey', 
    'trade_volume', 
    'trade_profit', 
    'broker_commission'
]]

# ==========================================
# 3. EXPORT STAR SCHEMA
# ==========================================
output_dir = os.path.join(dir_path, "Star_Schema_Output")
os.makedirs(output_dir, exist_ok=True)

dim_clients.to_csv(os.path.join(output_dir, "DimClients.csv"), index=False)
dim_instruments.to_csv(os.path.join(output_dir, "DimInstruments.csv"), index=False)
dim_dates.to_csv(os.path.join(output_dir, "DimDates.csv"), index=False)
fact_trades.to_csv(os.path.join(output_dir, "FactTrades.csv"), index=False)

print("\n[SUCCESS] SCD Dimensions explicitly added to CSV datasets!")
print("Load 'Star_Schema_Output/DimClients.csv' into Power BI, and you will see the active/inactive tracking rows!")
