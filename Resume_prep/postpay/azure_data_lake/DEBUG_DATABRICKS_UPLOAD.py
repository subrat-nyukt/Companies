# COPY THIS INTO A DATABRICKS NOTEBOOK CELL
# Run it to fix the "Combined File" issue

# 1. Check what files exist in the upload folder
print("--- Checking File System ---")
try:
    files = dbutils.fs.ls("dbfs:/FileStore/tables/")
    found_files = []
    for f in files:
        print(f"Found: {f.name}")
        if "raw_" in f.name:
            found_files.append(f.name)
            
    if len(found_files) == 0:
        print("\nWARNING: No 'raw_' files found. Did you upload them to the default location?")
    else:
        print(f"\nSuccess! Found {len(found_files)} potential raw files.")

except Exception as e:
    print(f"Error checking files: {e}")

# 2. Force-create 3 Separate Tables (Correcting the merge issue)
# This explicitly tells Spark which file belongs to which table

print("\n--- Creating Separate Tables ---")

# Table 1: Customers
try:
    spark.sql("DROP TABLE IF EXISTS raw_customers")
    # Note: We use * wildcard to handle if Databricks renamed it to raw_customers-1.csv
    df_c = spark.read.csv("dbfs:/FileStore/tables/raw_customers*.csv", header=True, inferSchema=True)
    df_c.write.mode("overwrite").saveAsTable("raw_customers")
    print("✅ Table 'raw_customers' created successfully.")
except Exception as e:
    print(f"❌ Failed to create raw_customers: {e}")

# Table 2: Orders
try:
    spark.sql("DROP TABLE IF EXISTS raw_orders")
    df_o = spark.read.csv("dbfs:/FileStore/tables/raw_orders*.csv", header=True, inferSchema=True)
    df_o.write.mode("overwrite").saveAsTable("raw_orders")
    print("✅ Table 'raw_orders' created successfully.")
except Exception as e:
    print(f"❌ Failed to create raw_orders: {e}")

# Table 3: Instalment Plans
try:
    spark.sql("DROP TABLE IF EXISTS raw_instalment_plans")
    df_p = spark.read.csv("dbfs:/FileStore/tables/raw_instalment_plans*.csv", header=True, inferSchema=True)
    df_p.write.mode("overwrite").saveAsTable("raw_instalment_plans")
    print("✅ Table 'raw_instalment_plans' created successfully.")
except Exception as e:
    print(f"❌ Failed to create raw_instalment_plans: {e}")

print("\nDone. You should now see 3 separate tables in the Data tab.")
