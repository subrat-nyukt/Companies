# DATABRICKS NOTEBOOK CODE
# Use this to process files one by one after uploading them individually.

# ==========================================
# STEP 1: Upload 'raw_customers.csv'
# ==========================================
# 1. Go to "Catalog" > "Create Table" > "Upload"
# 2. Drag & Drop ONLY 'raw_customers.csv'
# 3. Note the path it gives you (e.g., /FileStore/tables/raw_customers.csv)
# 4. Run this cell:

print("--- Processing Customers ---")
# Adjust the path below if Databricks gave you a different one!
df_cust = spark.read.csv("/FileStore/tables/raw_customers.csv", header=True, inferSchema=True)
df_cust.write.mode("overwrite").saveAsTable("raw_customers")
display(df_cust)
print("✅ Table 'raw_customers' created.")


# ==========================================
# STEP 2: Upload 'raw_orders.csv'
# ==========================================
# 1. Repeat the upload process for 'raw_orders.csv'
# 2. Run this cell:

print("\n--- Processing Orders ---")
df_ord = spark.read.csv("/FileStore/tables/raw_orders.csv", header=True, inferSchema=True)
df_ord.write.mode("overwrite").saveAsTable("raw_orders")
display(df_ord)
print("✅ Table 'raw_orders' created.")


# ==========================================
# STEP 3: Upload 'raw_instalment_plans.csv'
# ==========================================
# 1. Repeat the upload process for 'raw_instalment_plans.csv'
# 2. Run this cell:

print("\n--- Processing Instalment Plans ---")
df_plans = spark.read.csv("/FileStore/tables/raw_instalment_plans.csv", header=True, inferSchema=True)
df_plans.write.mode("overwrite").saveAsTable("raw_instalment_plans")
display(df_plans)
print("✅ Table 'raw_instalment_plans' created.")
