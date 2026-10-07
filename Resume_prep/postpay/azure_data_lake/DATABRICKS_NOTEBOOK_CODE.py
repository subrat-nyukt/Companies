# SQL for Databricks (Spark SQL)
# Upload the 3 CSVs to DBFS /mnt/postpay-data/ 
# Then run this code cell in a Databricks Notebook

# 1. READ RAW FILES
df_plans = spark.read.csv("/mnt/postpay-data/raw_instalment_plans.csv", header=True, inferSchema=True)
df_orders = spark.read.csv("/mnt/postpay-data/raw_orders.csv", header=True, inferSchema=True)
df_customers = spark.read.csv("/mnt/postpay-data/raw_customers.csv", header=True, inferSchema=True)

# 2. CREATE TEMP VIEWS (So we can write SQL)
df_plans.createOrReplaceTempView("instalment_plans")
df_orders.createOrReplaceTempView("orders")
df_customers.createOrReplaceTempView("customers")

# 3. RUN THE FEATURE LOGIC
# This is a simplified version of your massive SQL script adapted for Spark SQL
# It calculates: 
#   - Total Orders (Lifetime)
#   - Unpaid Count
#   - Device Type (from last order)
#   - Total Spend

risk_features = spark.sql("""
    SELECT 
        p.customer_id,
        
        -- VELOCITY: Count of orders
        count(distinct p.order_id) as total_orders,
        
        -- RISK: Unpaid Count
        sum(case when p.instalment_plan_status = 'unpaid' then 1 else 0 end) as unpaid_count,
        
        -- SPEND: Total amount
        sum(p.total_amount) as total_spend,
        
        -- DEVICE: (Taking the most recent device used)
        first(o.user_agent) as device_type,
        
        -- PAYMENT: (Taking the most recent payment method)
        first(o.payment_method_type) as payment_type

    FROM instalment_plans p
    JOIN orders o ON p.order_id = o.order_id
    GROUP BY p.customer_id
""")

# 4. VIEW RESULTS
display(risk_features)

# 5. SAVE TO FEATURE STORE
risk_features.write.saveAsTable("default.customer_risk_features")
