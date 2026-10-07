from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, to_date, year, month, date_format, dayofweek,
    concat_ws, md5, current_timestamp, lit, expr, when
)
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, BooleanType
import datetime

# ---------------------------------------------------------
# SETUP: Initialize Spark
# ---------------------------------------------------------
spark = SparkSession.builder.appName("Ecobank_Silver_to_Gold_StarSchema").getOrCreate()

# =========================================================
# STEP 1: READ SILVER DATA (Simulating reading from ADLS)
# =========================================================
print("Loading Silver Data...")
df_corps = spark.read.csv("corporate_merchants.csv", header=True, inferSchema=True)
df_branches = spark.read.csv("merchant_branches.csv", header=True, inferSchema=True)
df_terminals = spark.read.csv("payment_terminals.csv", header=True, inferSchema=True)
df_txns = spark.read.csv("advanced_transactions.csv", header=True, inferSchema=True)

# Add a mock email to branches just so we can practice SCD1
df_branches = df_branches \
    .withColumnRenamed("city", "location") \
    .withColumn("email_id", concat_ws("@", col("branch_id"), lit("ecobank.com")))


# =========================================================
# STEP 2: CREATE DIM_BRANCH (With initial SCD properties)
# =========================================================
print("\nCreating Dim_Branch (Day 0 Load)...")
# We use expr("uuid()") instead of md5 because in the future, 
# SCD2 will create multiple rows for the same branch_id.
dim_branch = df_branches.withColumn("branch_sk", expr("uuid()")) \
    .withColumn("valid_from", lit("2024-01-01 00:00:00")) \
    .withColumn("valid_to", lit("9999-12-31 23:59:59")) \
    .withColumn("is_active", lit(True)) \
    .select(
        col("branch_sk"),
        col("branch_id"),
        col("branch_name"),
        col("location"),         # SCD2 attribute
        col("email_id"),         # SCD1 attribute
        col("valid_from"),
        col("valid_to"),
        col("is_active")
    )


# =========================================================
# STEP 3: CREATE DIM_MERCHANT (Terminal details)
# =========================================================
print("Creating Dim_Merchant...")
# We use md5(terminal_id) here. This is safe because terminal_id is a static 
# piece of hardware (SCD0) and won't have multiple historical versions.
dim_merchant_raw = df_terminals.join(df_corps, on="corporate_id", how="left")

dim_merchant = dim_merchant_raw.withColumn("terminal_sk", md5(col("terminal_id"))) \
    .select(
        col("terminal_sk"),
        col("terminal_id"),
        col("branch_id"),        # <-- KEPT this so Fact can link to dim_branch
        col("qr_code_id"),
        col("merchant_wallet_number"),
        col("legal_name").alias("corporate_name"),
        col("category").alias("merchant_category"),
        col("corporate_fee_rate")
    )


# =========================================================
# STEP 4: CREATE DIM_DATE
# =========================================================
print("Creating Dim_Date...")
dim_date = df_txns.withColumn("full_date", to_date(col("timestamp"))) \
                  .select("full_date").distinct()

dim_date = dim_date.withColumn("date_sk", date_format(col("full_date"), "yyyyMMdd").cast("int")) \
    .withColumn("year", year(col("full_date"))) \
    .withColumn("month_num", month(col("full_date"))) \
    .withColumn("month_name", date_format(col("full_date"), "MMMM")) \
    .withColumn("day_of_week", date_format(col("full_date"), "EEEE")) \
    .select("date_sk", "full_date", "year", "month_num", "month_name", "day_of_week")


# =========================================================
# STEP 5: CREATE FACT_TRANSACTIONS
# =========================================================
print("Creating Fact_Transactions...")

fact_raw = df_txns.withColumn("full_date", to_date(col("timestamp")))

# 1. Join to Dim_Merchant to get terminal_sk and branch_id
fact_raw = fact_raw.join(dim_merchant, on="terminal_id", how="inner")

# 2. Join to Dim_Date to get Date SK
fact_raw = fact_raw.join(dim_date, on="full_date", how="inner")

# 3. Join to Dim_Branch (Active only) to get branch_sk
# This ensures new transactions get the CURRENT surrogate key!
dim_branch_active = dim_branch.filter(col("is_active") == True).select("branch_id", "branch_sk")
fact_raw = fact_raw.join(dim_branch_active, on="branch_id", how="inner")

fact_transactions = fact_raw \
    .withColumn("processing_fee_amount", col("amount") * col("corporate_fee_rate")) \
    .withColumn("net_settlement_amount", col("amount") - col("processing_fee_amount")) \
    .select(
        col("transaction_id"),
        col("terminal_sk"),
        col("branch_sk"),    # <-- NOW WE HAVE IT
        col("date_sk"),
        col("provider"),     
        col("status"),       
        col("amount").alias("gross_amount"),
        col("processing_fee_amount"),
        col("net_settlement_amount")
    )


# #########################################################################
# SCD SIMULATION & REPORTING SECTION (Next Day Data)
# What happens when a branch moves? 
# Let's simulate BR_0001 changing location and BR_0002 changing email.
# #########################################################################
print("\n========== NEXT DAY SIMULATION: SCD UPDATES ==========")

now_str    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
far_future = "9999-12-31 23:59:59"

incoming_updates_data = [
    ("BR_0001", "New Lagos Downtown", "BR_0001@ecobank.com"),    # Location changed (SCD2)
    ("BR_0002", "Dakar",              "new.BR_0002@ecobank.com") # Email changed (SCD1)
]
incoming_updates = spark.createDataFrame(incoming_updates_data, ["branch_id", "location", "email_id"])

# --- SCD TYPE 1: Update Email in place
scd1_updates = incoming_updates.alias("src").join(
    dim_branch.filter(col("is_active") == True).alias("tgt"), on="branch_id", how="inner"
).filter(
    (col("src.email_id") != col("tgt.email_id")) & 
    (col("src.location") == col("tgt.location"))
).select(col("src.branch_id"), col("src.email_id").alias("new_email"))

dim_branch = dim_branch.join(scd1_updates, on="branch_id", how="left") \
    .withColumn("email_id", when(col("new_email").isNotNull() & col("is_active"), col("new_email")).otherwise(col("email_id"))) \
    .drop("new_email")

# --- SCD TYPE 2: Expire old location, insert new location
scd2_changes = incoming_updates.alias("src").join(
    dim_branch.filter(col("is_active") == True).alias("tgt"), on="branch_id", how="inner"
).filter(col("src.location") != col("tgt.location")) \
 .select(col("src.branch_id"), col("src.location").alias("new_location"), col("src.email_id").alias("new_email"), col("tgt.branch_name"))

branches_to_expire = scd2_changes.select("branch_id")

dim_branch = (
    dim_branch.join(branches_to_expire, on="branch_id", how="left_anti")
    .union(
        dim_branch.join(branches_to_expire, on="branch_id", how="inner").filter(col("is_active") == True)
                  .withColumn("is_active", lit(False)).withColumn("valid_to", lit(now_str))
    )
    .union(
        dim_branch.join(branches_to_expire, on="branch_id", how="inner").filter(col("is_active") == False)
    )
)

new_scd2_rows = scd2_changes \
    .withColumn("branch_sk",  expr("uuid()")) \
    .withColumn("valid_from", lit(now_str)) \
    .withColumn("valid_to",   lit(far_future)) \
    .withColumn("is_active",  lit(True)) \
    .select(
        col("branch_sk"), col("branch_id"), col("branch_name"),
        col("new_location").alias("location"), col("new_email").alias("email_id"),
        col("valid_from"), col("valid_to"), col("is_active")
    )

dim_branch = dim_branch.union(new_scd2_rows)

print("\n--- Final Dim_Branch (With time travel history) ---")
dim_branch.filter(col("branch_id").isin("BR_0001", "BR_0002")).orderBy("branch_id", "valid_from").show(truncate=False)

print("\n--- Final Reporting: fact_transactions correctly mapped to OLD active branch version ---")
report = fact_transactions.join(dim_branch, on="branch_sk", how="left") \
    .filter(col("branch_id") == "BR_0001") \
    .select("transaction_id", "branch_sk", "location", "is_active", "gross_amount")

report.show(truncate=False)
print("Notice how the transaction still points to the old 'Lagos' location and is_active is False.")
print("This proves our surrogate key successfully preserved the state of the branch AT TIME OF TRANSACTION!")
