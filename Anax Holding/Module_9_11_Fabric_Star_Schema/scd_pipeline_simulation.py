import pandas as pd

print("==================================================")
print("REAL-WORLD SIMULATION: SLOWLY CHANGING DIMENSIONS (SCD)")
print("==================================================\n")

# 1. Existing DimClients Table (Yesterday's Data)
# -----------------------------------------------------
# Notice the SCD tracking columns: 'is_active', 'start_date', 'end_date'
existing_dim_data = [
    {"ClientKey": 1, "client_id": "ANX-100", "client_country": "UAE", "kyc_status": "PENDING", 
     "is_active": True, "start_date": "2026-04-01", "end_date": "9999-12-31"},
    {"ClientKey": 2, "client_id": "ANX-101", "client_country": "UK",  "kyc_status": "VERIFIED", 
     "is_active": True, "start_date": "2026-04-01", "end_date": "9999-12-31"}
]
dim_clients = pd.DataFrame(existing_dim_data)

print("--- YESTERDAY'S EXISTING DIM_CLIENTS DATABASE ---")
print(dim_clients.to_string(index=False))


# 2. Today's Incoming Data Updates 
# -----------------------------------------------------
# Scenario A: ANX-100's KYC got approved! (SCD Type 2 -> We must preserve the old PENDING history)
# Scenario B: ANX-101 moved from UK to USA. (SCD Type 1 -> We just overwrite, we don't care about their old address).
incoming_updates = [
    {"client_id": "ANX-100", "incoming_country": "UAE", "incoming_kyc": "VERIFIED"},
    {"client_id": "ANX-101", "incoming_country": "USA", "incoming_kyc": "VERIFIED"}
]
df_updates = pd.DataFrame(incoming_updates)


# 3. Apply the SCD Data Engineering Logic
# -----------------------------------------------------
today_str = "2026-04-12"

for idx, update in df_updates.iterrows():
    bus_key = update['client_id']
    
    # Isolate the current 'active' row in our dimension table
    idx_db = dim_clients[(dim_clients['client_id'] == bus_key) & (dim_clients['is_active'] == True)].index[0]
    db_record = dim_clients.loc[idx_db]
    
    # == SCD TYPE 1 CHECK (Country) ==
    if update['incoming_country'] != db_record['client_country']:
        # Action: Literally overwrite the cell in the dataframe. No history saved.
        dim_clients.at[idx_db, 'client_country'] = update['incoming_country']
        print(f"\n[SCD TYPE 1 DETECTED] Simply overwriting country for {bus_key} without tracking history.")
        
    # == SCD TYPE 2 CHECK (KYC Status) ==
    if update['incoming_kyc'] != db_record['kyc_status']:
        print(f"\n[SCD TYPE 2 DETECTED] Retaining history. Closing old record and inserting new line for {bus_key}.")
        # Action A: Retire the old record by changing dates and 'is_active'
        dim_clients.at[idx_db, 'is_active'] = False
        dim_clients.at[idx_db, 'end_date'] = today_str
        
        # Action B: Generate a completely new row with a new ClientKey (Surrogate Key)
        new_row = {
            "ClientKey": dim_clients['ClientKey'].max() + 1, 
            "client_id": bus_key,
            "client_country": dim_clients.at[idx_db, 'client_country'], 
            "kyc_status": update['incoming_kyc'],
            "is_active": True,
            "start_date": today_str,
            "end_date": "9999-12-31" # 9999 means it is the current version
        }
        # In a real Databricks environment, this is achieved natively via `DeltaTable.merge()`
        dim_clients = pd.concat([dim_clients, pd.DataFrame([new_row])], ignore_index=True)


print("\n\n--- TODAY'S UPDATED DIM_CLIENTS (AFTER SCD PROCESSING) ---")
print(dim_clients.sort_values(by=['client_id', 'start_date']).to_string(index=False))

print("\n[ARCHITECTURAL NOTE]")
print("Notice how ANX-101 only has ONE row because Country changes just overwrite data (SCD 1).")
print("But ANX-100 now has TWO rows! If an executive asks for their trading volume when they were 'PENDING', we can perfectly recall it by linking the FactTable to ClientKey 1!")
