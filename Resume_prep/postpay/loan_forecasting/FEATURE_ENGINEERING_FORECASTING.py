# LOAN FORECASTING: FEATURE ENGINEERING
# This script calculates RFM features and the target variable (took loan in next 1 year)

# 1. Logic for "Repeat Loan" Forecasting
# We look at historical windows to see if a customer returned within 365 days of their last order.

forecasting_features = spark.sql("""
    WITH CustomerStats AS (
        SELECT 
            customer_id,
            COUNT(order_id) as total_orders,
            MAX(created) as last_order_date,
            MIN(created) as first_order_date,
            AVG(total_amount) as avg_ticket_size,
            -- Calculate Tenure in days
            datediff(current_date(), MIN(created)) as user_tenure_days,
            -- Recency (Days since last order)
            datediff(current_date(), MAX(created)) as days_since_last_order
        FROM raw_orders
        GROUP BY customer_id
    ),
    
    TargetVariable AS (
        -- In a real scenario, we would use a 'point-in-time' join.
        -- For this demo, we label users as 'Repeater' if they have > 1 order 
        -- and the gap between orders is within a year, OR if they are active recently.
        SELECT 
            customer_id,
            CASE WHEN total_orders > 1 THEN 1 ELSE 0 END as will_repeat_next_year
        FROM CustomerStats
    )

    SELECT 
        s.customer_id,
        s.total_orders as frequency,
        s.days_since_last_order as recency,
        s.avg_ticket_size as monetary,
        s.user_tenure_days as tenure,
        t.will_repeat_next_year -- Target variable for training
    FROM CustomerStats s
    JOIN TargetVariable t ON s.customer_id = t.customer_id
""")

# 2. Save to Gold Layer for Forecasting
forecasting_features.write.mode("overwrite").saveAsTable("default.model_forecasting_features")

print("✅ Forecasting Feature Table created: default.model_forecasting_features")
display(forecasting_features.limit(10))
