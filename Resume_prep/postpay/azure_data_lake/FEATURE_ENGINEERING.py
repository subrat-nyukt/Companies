# PHASE 2: FEATURE ENGINEERING (Spark SQL)
# Run this in a new Databricks Notebook cell AFTER uploading all 3 files.

# 1. Create the Feature Store Table
# We are converting raw transactions into "Risk Drivers" per customer.

risk_features = spark.sql("""
    SELECT 
        c.customer_id,
        
        -- 1. VELOCITY (How active are they?)
        count(distinct o.order_id) as total_lifetime_orders,
        max(o.created) as last_order_date,
        
        -- 2. RISK SIGNALS (Unpaid History)
        -- Counting how many plans were ever 'unpaid'
        sum(case when p.instalment_plan_status = 'unpaid' then 1 else 0 end) as count_unpaid,
        
        -- Ratio of Unpaid Amount / Total Spent (Debt-to-Value)
        round(
            sum(p.total_amount_unpaid) / nullif(sum(p.total_amount),0)
        , 4) as debt_ratio,
        
        -- 3. DEVICE FINGERPRINT (Most recent device)
        -- We want to know if they use iPhone or Android
        first(o.user_agent) as device_type,
        
        -- 4. SPEND POWER
        round(avg(o.total_amount), 2) as avg_order_value,
        
        -- 5. TARGET VARIABLE (Outcome for Training)
        -- In a real scenario, we might predict if they default on the *next* order.
        -- For this demo, let's flag them as 'High Risk' if they have ANY unpaid plans.
        case when sum(case when p.instalment_plan_status = 'unpaid' then 1 else 0 end) > 0 
             then 1 else 0 end as is_high_risk

    FROM raw_customers c
    -- Left join to keep customers even if they have no orders
    LEFT JOIN raw_orders o ON c.customer_id = o.customer_id
    LEFT JOIN raw_instalment_plans p ON o.order_id = p.order_id
    
    GROUP BY c.customer_id
""")

# 2. View the Result
display(risk_features)

# 3. Save as a Clean Table for ML
# This table is now ready for the Data Science team!
risk_features.write.mode("overwrite").saveAsTable("default.customer_risk_features")
print("✅ Feature Table created: default.customer_risk_features")
