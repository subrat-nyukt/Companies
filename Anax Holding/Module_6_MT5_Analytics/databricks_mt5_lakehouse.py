from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum, when, round as spark_round
import os

# --- 1. SPARK INIT & ADLS STORAGE SETUP ---
spark = SparkSession.builder.appName("MT5_Analytics").getOrCreate()

storage_account = "practice123456"
account_key = "<YOUR_AZURE_STORAGE_KEY>"
spark.conf.set(f"fs.azure.account.key.{storage_account}.dfs.core.windows.net", account_key)

container_base = f"abfss://lakehouse@{storage_account}.dfs.core.windows.net"

# Simulating Databricks reading the Bronze CSV file from ADLS
script_dir = os.path.dirname(os.path.abspath(__file__))
raw_csv_path = os.path.join(script_dir, "raw_mt5_deals.csv")

print("\n[BRONZE] Extracting 10,000 trades from MT5 SQL Database Dump...")
df_bronze = spark.read.csv(raw_csv_path, header=True, inferSchema=True)

# --- 2. SILVER LAYER (B-Book Financial Engine) ---
# GOAL: Broker's Gross Revenue = Commission + Spread + B-Book Revenue
# B-Book Mechanics: The broker is the market maker. 
# If a B-Book Client LOSES $100 -> The Broker GAINS $100.
# If a B-Book Client GAINS $50 -> The Broker LOSES $50.
df_silver = df_bronze.withColumn(
    "broker_b_book_revenue",
    when(col("is_b_book") == True, col("client_profit") * -1).otherwise(0.0)
).withColumn(
    "total_broker_revenue",
    col("commission") + col("spread_revenue") + col("broker_b_book_revenue")
)

print("[SILVER] Applied Quantitative B-Book PnL Math.")

# --- 3. GOLD LAYER (Aggregating for Power BI) ---
# We want to know exactly which Financial Instruments generate the most revenue for Anax Capital.
df_gold_symbol = df_silver.groupBy("symbol").agg(
    spark_round(spark_sum("volume"), 2).alias("total_lots_traded"),
    spark_round(spark_sum("total_broker_revenue"), 2).alias("gross_broker_revenue")
).orderBy(col("gross_broker_revenue").desc())

print("\n[GOLD] FINAL AGGREGATED PROFITABILITY BY TRADING SYMBOL:")
df_gold_symbol.show()

# --- 4. EXPORT TO ADLS & SYNAPSE FOR POWER BI ---
gold_path = f"{container_base}/gold/mt5_symbol_profitability"
print(f"\n[DATABRICKS] Writing Golden Table to Data Lake: {gold_path}")

# In a live cluster, this natively pushes the Delta table into Azure Storage:
# df_gold_symbol.write.format('delta').mode('overwrite').save(gold_path)

print("-----------------------------------------------------------------------------------------")
print("PIPELINE COMPLETE. Next Steps for Power BI:")
print("1) Open Synapse Serverless SQL.")
print("2) Run: CREATE VIEW vw_mt5_revenue AS SELECT * FROM OPENROWSET(BULK '...', FORMAT='DELTA')")
print("3) Open Power BI, connect to the view, and build a Bar Chart of Gross Revenue by Symbol.")
print("-----------------------------------------------------------------------------------------")

# Optional: creating local CSV so you can view it directly on your PC
df_gold_symbol.toPandas().tocsv_path = os.path.join(script_dir, "gold_mt5_symbol_report.csv")
df_gold_symbol.toPandas().to_csv(tocsv_path, index=False)
