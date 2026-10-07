from pyspark.sql import SparkSession
from pyspark.sql.functions import col, datediff, mean, count, sum as spark_sum, current_timestamp, current_date, when, round

# Configuration
storage_account = "practice123456"
account_key = "<YOUR_AZURE_STORAGE_KEY>"

# -----------------------------------------------------------------------------
# 1. Initialize Spark Session & Configure ADLS Access
# -----------------------------------------------------------------------------
spark = SparkSession.builder.appName("AnaxCapital_KPI_Processing").getOrCreate()
spark.conf.set(f"fs.azure.account.key.{storage_account}.dfs.core.windows.net", account_key)

# Setup paths
container_base = f"abfss://lakehouse@{storage_account}.dfs.core.windows.net"
filename = 'crm_conversion_data'

# -----------------------------------------------------------------------------
# 2. Extract: Read Raw "Scattered" Data from ADLS Gen2 (Bronze Layer)
# -----------------------------------------------------------------------------
df_raw = spark.read.csv(f'{container_base}/{filename}.csv', header=True, inferSchema=True)
bronze_data = df_raw

try:
    display(bronze_data)
except NameError:
    bronze_data.show()

# -----------------------------------------------------------------------------
# 3. Transform: Clean and Process Data (Silver Layer)
# -----------------------------------------------------------------------------
# Convert string dates to un-nullable dates where applicable
df_silver = df_raw \
    .withColumn("lead_date", col("lead_date").cast("date")) \
    .withColumn("first_deposit_date", col("first_deposit_date").cast("date")) \
    .withColumn("first_trade_date", col("first_trade_date").cast("date"))

# Calculate Time to Conversion
df_silver = df_silver \
    .withColumn("Days_to_Deposit", datediff(col("first_deposit_date"), col("lead_date"))) \
    .withColumn("Days_to_Trade", datediff(col("first_trade_date"), col("first_deposit_date"))) \
    .withColumn("Day1_retention", when(col("Days_to_Trade") <= 1, 1).otherwise(0))

# Save to Silver Layer (Optional but recommended for Medallion Architecture)
silver_delta_path = f"{container_base}/silver/crm_conversion_cleaned"
# df_silver.write.format("delta").mode("overwrite").save(silver_delta_path)

# -----------------------------------------------------------------------------
# 4. Transform: Aggregate Data for KPI Dashboard (Gold Layer)
# -----------------------------------------------------------------------------
# Consolidating Gold transformations into a simpler, highly readable SQL query
df_silver.createOrReplaceTempView("silver")

df_gold_kpi = spark.sql("""
    SELECT 
        marketing_campaign,
        COUNT(user_id) AS total_leads,
        COUNT(first_deposit_date) AS total_depositors,
        ROUND((COUNT(first_deposit_date) / COUNT(user_id)) * 100, 2) AS lead_to_dep_conversion_pct,
        ROUND(AVG(Days_to_Deposit), 2) AS avg_days_to_deposit,
        COUNT(first_trade_date) AS total_traders,
        ROUND(AVG(Days_to_Trade), 2) AS avg_days_deposit_to_trade,
        ROUND((SUM(Day1_retention) / COUNT(first_deposit_date)) * 100, 2) AS day_1_trade_activation_pct,
        ROUND(SUM(total_volume_traded_30_days), 2) AS total_volume
    FROM silver
    GROUP BY marketing_campaign
""")

df_gold_kpi.show()

# -----------------------------------------------------------------------------
# 5. Load: Write Processed KPI Data to ADLS Gen2 (Gold Layer) for Synapse
# -----------------------------------------------------------------------------
# We write this as a Delta table or Parquet file in the Gold container.
# Synapse Serverless SQL can read this directly to serve Power BI!
gold_delta_path = f"{container_base}/gold/kpi_campaign_performance"
print(f"Writing Gold Data to ADLS Gen2 for Synapse Consumption: {gold_delta_path}")

# Writing as Delta format (Best practice for Lakehouse)
df_gold_kpi.write.format("delta").mode("overwrite").save(gold_delta_path)

# Alternatively, write as Parquet if strictly using Synapse without Delta support:
# df_gold_kpi.write.format("parquet").mode("overwrite").save(f"{container_base}/gold/parquet_kpis")

print("Pipeline executed successfully. Data is ready for Synapse & Power BI.")
