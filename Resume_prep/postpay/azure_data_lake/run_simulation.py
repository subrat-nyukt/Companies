import subprocess
import time
import sys

def run_step(step_name, filename):
    print(f"\n{'='*50}")
    print(f"       STEP {step_name}: {filename}")
    print(f"{'='*50}\n")
    try:
        subprocess.check_call([sys.executable, filename])
        time.sleep(1) # Add delay for realistic feel
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Step {step_name} Failed!")
        exit(1)

def main():
    print("DEMO: SAP S/4HANA -> Azure Data Factory -> Databricks ETL")
    
    # 1. Start Virtual SAP
    run_step("1 (Source System)", "virtual_s4_hana.py")

    # 2. Trigger ADF Ingestion
    run_step("2 (Ingestion Pipeline)", "adf_pipeline_simulation.py")
    
    # 3. Simulate Data Lake view
    print(f"\n[Storage Check] Verifying RAW files in Data Lake Bronze...")
    # List files in bronze
    # Windows command simulation
    subprocess.call("dir azure_data_lake\\bronze", shell=True)
    
    # 4. Run Databricks Transformation
    run_step("3 (Processing Job)", "databricks_etl_job.py")
    
    print("\n[SUCCESS] End-to-End Pipeline Completed Successfully!")
    print("Your Gold (Business) Data is ready for Power BI consumption.")

if __name__ == "__main__":
    main()
