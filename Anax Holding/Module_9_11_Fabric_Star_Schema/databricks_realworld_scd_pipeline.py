from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_date, lit, md5, concat_ws
from delta.tables import DeltaTable

# =======================================================================
# THE REAL WORLD ENTERPRISE SCENARIO (How Databricks actually does it)
# =======================================================================

spark = SparkSession.builder.appName("RealWorld_SCD_Pipeline").getOrCreate()

# --- Azure ADLS Gen2 Configuration ---
storage_account = "practice123456"
account_key = "<YOUR_AZURE_STORAGE_KEY>"
spark.conf.set(f"fs.azure.account.key.{storage_account}.dfs.core.windows.net", account_key)

# Setup paths
container_base = f"abfss://lakehouse@{storage_account}.dfs.core.windows.net"
filename = 'flat_enterprise_lakehouse_export.csv'

# ==========================================
# 1. BRONZE -> SILVER (Ingest & Cleanse)
# ==========================================
print("1. Extracting 500-row Flat Export from ADLS Base directory...")
# Pointing directly to your massive flat file at the root of the lakehouse container!
bronze_df = spark.read.format("csv").option("header", "true").load(f"{container_base}/{filename}")

# Cleanse Data (Silver Layer)
silver_df = bronze_df.select(
    col("client_id"),
    col("client_country").alias("country"), # SCD Type 1 Column
    col("kyc_status").alias("kyc_status")   # SCD Type 2 Column
).dropDuplicates(["client_id"]) # CRITICAL: Delta Merge crashes if your flat file has 5 trades from the same client on the same day!

# ==========================================
# 2. SILVER -> GOLD (SCD Type 1 & 2 Merge)
# ==========================================
gold_dim_path = f"{container_base}/gold/DimClients"

# A. Ensure the Target Gold Table Exists Schema-Wise
if not DeltaTable.isDeltaTable(spark, gold_dim_path):
    print("WARNING: Target Delta table does not exist. Creating empty schema structure...")
    # Create an extremely lightweight empty DataFrame with the exact schema needed
    from pyspark.sql.types import StructType, StructField, StringType, BooleanType, DateType
    schema = StructType([
        StructField("ClientKey", StringType(), True),
        StructField("client_id", StringType(), True),
        StructField("country", StringType(), True),
        StructField("kyc_status", StringType(), True),
        StructField("is_active", BooleanType(), True),
        StructField("start_date", DateType(), True),
        StructField("end_date", StringType(), True)
    ])
    empty_df = spark.createDataFrame([], schema)
    empty_df.write.format("delta").save(gold_dim_path)

print("2. Performing Enterprise PySpark Delta Merge...")

# B. Load the live Delta Table
dim_clients_table = DeltaTable.forPath(spark, gold_dim_path)

# ======================================================================
# C. THE "SIMPLE" TWO-STEP SCD CALCULATION
# Instead of doing a massively complex single-transaction staging union,
# we split the brain into two simple, highly-readable steps to explain.
# ======================================================================

print("Executing Step 1: Updating existing records...")

# STEP 1: Update the Target Table based on incoming data
dim_clients_table.alias("target").merge(
    source=silver_df.alias("source"),
    condition="target.client_id = source.client_id AND target.is_active = True"
).whenMatchedUpdate(
    # SCD TYPE 2 (KYC Changed): Retire the old row.
    condition="target.kyc_status <> source.kyc_status",
    set={
        "is_active": lit(False),
        "end_date": current_date()
    }
).whenMatchedUpdate(
    # SCD TYPE 1 (Country Changed): Just overwrite it!
    condition="target.country <> source.country",
    set={
        "country": "source.country"
    }
).whenNotMatchedInsert(
    # BRAND NEW CLIENT: Insert them immediately natively
    values={
        "ClientKey": md5(concat_ws("||", "source.client_id", "source.kyc_status")), 
        "client_id": "source.client_id",
        "country": "source.country",
        "kyc_status": "source.kyc_status",
        "is_active": lit(True),
        "start_date": current_date(),
        "end_date": lit("9999-12-31")
    }
).execute()

print("Executing Step 2: Injecting new historical rows...")

# STEP 2: Append the 'New' Active record for any client who got retired in Step 1
# We just look for clients who were just updated to is_active = False today!
new_scd2_rows = silver_df.join(
    spark.read.format("delta").load(gold_dim_path).filter(col("is_active") == False).filter(col("end_date") == current_date()),
    "client_id"
).select(
    md5(concat_ws("||", silver_df.client_id, silver_df.kyc_status)).alias("ClientKey"),
    silver_df.client_id,
    col("country"),
    silver_df.kyc_status,
    lit(True).alias("is_active"),
    current_date().alias("start_date"),
    lit("9999-12-31").alias("end_date")
).dropDuplicates(["client_id"])

# Push these freshly minted rows into the table
new_scd2_rows.write.format("delta").mode("append").save(gold_dim_path)

print("Simple SCD Process Complete! DimClients natively updated.")


# ==========================================
# 3. FABRIC ENABLEMENT (The Data Inflow)
# ==========================================
print("""
[MS FABRIC DIRECTLAKE DATA INFLOW PROCESS]
Now that Databricks has mathematically forced the exact SCD logic onto the physical Delta files inside ADLS Gen2, here is how Fabric connects to it without copying data:

1. Open Microsoft Fabric > Data Engineering interface.
2. In your Fabric 'Lakehouse', click [Get Data] -> [New Shortcut].
3. Point the shortcut directly to your Azure ADLS container path:
   `abfss://lakehouse@practice123456.dfs.core.windows.net/gold/DimClients`
4. Fabric natively parses the Delta transaction logs (the _delta_log folder) built by PySpark.

Result: When your Power BI Semantic Model refreshes via 'DirectLake', it parses the OneLake Shortcut. Power BI sees the exact `is_active=False` and `is_active=True` dimensions natively, filtering perfectly on your Star Schema without running a single SQL Query!
""")
