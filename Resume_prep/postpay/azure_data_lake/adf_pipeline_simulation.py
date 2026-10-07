import os
import shutil
import time

# Simulate Azure Data Factory (ADF) Behavior
def simulate_adf_pipeline(source_path, destination_path, table_name):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # 1. Pipeline Start
    print(f"[ADF] Status: Pipeline copy_{table_name}_to_adls STARTED at {timestamp}")

    # 2. Check Source (Self-Hosted IR)
    full_source_path = os.path.join(source_path, f"{table_name}.csv")
    if not os.path.exists(full_source_path):
        print(f"[ADF ERROR] Source table {table_name} not found!")
        return

    # 3. Create ADLS Bronze Container (if not exists)
    os.makedirs(destination_path, exist_ok=True)
    
    # 4. Copy Activity (Ingestion)
    dest_filename = f"{table_name}_{timestamp}.csv"
    full_dest_path = os.path.join(destination_path, dest_filename)
    
    shutil.copyfile(full_source_path, full_dest_path)
    print(f"[ADF] Activity: Copy Data 1 -> Succeeded. Copied {os.path.getsize(full_dest_path)} bytes.")
    
    # 5. Pipeline Finish
    end_time = time.strftime("%Y%m%d_%H%M%S")
    print(f"[ADF] Status: Pipeline copy_{table_name}_to_adls SUCCEEDED at {end_time}\n")

if __name__ == "__main__":
    SOURCE_SYSTEM = "sap_system_source"
    DATA_LAKE_BRONZE = "azure_data_lake/bronze" # The landing zone
    
    # Run pipelines for both tables
    simulate_adf_pipeline(SOURCE_SYSTEM, DATA_LAKE_BRONZE, "KNA1")
    simulate_adf_pipeline(SOURCE_SYSTEM, DATA_LAKE_BRONZE, "VBAK")
