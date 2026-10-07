from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit, abs as spark_abs, coalesce

# -----------------------------------------------------------------------------
# 1. Configuration & Storage Setup
# -----------------------------------------------------------------------------
spark = SparkSession.builder.appName("Bank_Wallet_Reconciliation").getOrCreate()

storage_account = "practice123456"
account_key = "<YOUR_AZURE_STORAGE_KEY>"
spark.conf.set(f"fs.azure.account.key.{storage_account}.dfs.core.windows.net", account_key)

container_base = f"abfss://lakehouse@{storage_account}.dfs.core.windows.net"

# -----------------------------------------------------------------------------
# 2. Extract (Connect to Google Drive & ADLS)
# -----------------------------------------------------------------------------
print("Extracting Bank Data (Simulating Google Drive ingestion)...")
# In production, Databricks would use an HTTP REST API or gdown library to fetch this.
# Assuming it lands in a staging folder in our lakehouse:
bank_path = f"{container_base}/staging/bank_statements.csv"
# df_bank = spark.read.csv(bank_path, header=True, inferSchema=True)

# For testing locally without Databricks, we load the local mock:
df_bank = spark.read.csv("bank_statements.csv", header=True, inferSchema=True)

print("Extracting Wallet Data (from ADLS Gen2)...")
wallet_path = f"{container_base}/raw/adls_wallet_data.csv"
# df_wallet = spark.read.csv(wallet_path, header=True, inferSchema=True)
df_wallet = spark.read.csv("adls_wallet_data.csv", header=True, inferSchema=True)

# -----------------------------------------------------------------------------
# 3. Transform: The Full Outer Join & Compliance Logic
# -----------------------------------------------------------------------------
# Join on both Transaction ID and User ID to ensure strict matching
recon_df = df_bank.join(df_wallet, on=[ ], how="outer")

# Apply Data Governance Rules to flag anomalies into a clean, BI-ready format
recon_report = recon_df \
    .withColumn(
        "Reconciliation_Status",
        when(col("bank_deposit_amount").isNull(), lit("CRITICAL: Missing in Bank"))
        .when(col("wallet_credited_amount").isNull(), lit("WARNING: Missing in CRM Wallet"))
        .when(col("bank_deposit_amount") != col("wallet_credited_amount"), lit("CRITICAL: Amount Mismatch"))
        .otherwise(lit("CLEAN: Perfect Match"))
    ) \
    .withColumn(
        "Discrepancy_Amount",
        spark_abs(coalesce(col("bank_deposit_amount"), lit(0.0)) - coalesce(col("wallet_credited_amount"), lit(0.0)))
    )

print("\n--- GENERATED RECONCILIATION REPORT ---")
recon_report.show(truncate=False)

# -----------------------------------------------------------------------------
# 4. Load: Expose pure Gold Data to Power BI!
# -----------------------------------------------------------------------------
# We write the resulting report as a Gold Delta Table into ADLS.
report_path = f"{container_base}/gold/bank_reconciliation_report"
print(f"Saving Reconciliation Report to ADLS for Power BI: {report_path}")

# In Databricks, you uncomment this to physically write the files:
# recon_report.write.format("delta").mode("overwrite").save(report_path)

print("Pipeline complete. Ready for Synapse & Power BI!")
