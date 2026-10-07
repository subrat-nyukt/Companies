-- ==========================================================
-- DATABRICKS FEATURE ENGINEERING QUERY (For ML Model)
-- Run this in a Databricks Notebook cell.
-- ==========================================================

CREATE OR REPLACE TABLE default.gold_customer_risk_profile AS

WITH num_ins as (
    -- 1. INSTALLMENT BEHAVIOR (Payment History)
    SELECT 
        customer_id,
        -- Count of plans in last 30 days
        sum(case when created >= current_timestamp() - INTERVAL 30 DAYS 
             and instalment_plan_status in ('paid','unpaid','due') 
             and status='captured' then 1 else 0 end) as No_of_instalment_plan_1m,
        
        -- Count of plans in last 90 days
        sum(case when created >= current_timestamp() - INTERVAL 90 DAYS 
             and instalment_plan_status in ('paid','unpaid','due') 
             and status='captured' then 1 else 0 end) as No_of_instalment_plan_3m,
             
        -- Lifetime Total Plans
        count(*) as No_of_instalment_plan_tot

    FROM default.raw_instalment_plans
    WHERE num_instalments=3 
    GROUP BY customer_id
),

unpaid_history as (
    -- 2. RISK SIGNALS (Defaults)
    SELECT 
        customer_id,
        -- Unpaid orders in last 30 days (CRITICAL RISK)
        sum(case when created >= current_timestamp() - INTERVAL 30 DAYS 
             and instalment_plan_status = 'unpaid' 
             and status='captured' then 1 else 0 end) as No_of_unpaid_orders_1m,
             
        -- Unpaid orders lifetime
        sum(case when instalment_plan_status = 'unpaid' 
             and status='captured' then 1 else 0 end) as No_of_unpaid_orders_tot,
             
        -- Average Amount Unpaid (Severity)
        coalesce(avg(case when instalment_plan_status = 'unpaid' 
             then total_amount_unpaid else null end), 0) as Avg_unpaid_amt

    FROM default.raw_instalment_plans
    GROUP BY customer_id
),

order_stats as (
    -- 3. SPENDING HABITS
    SELECT 
        customer_id,
        -- Total Spend Lifetime
        sum(total_amount) as total_lifetime_spend,
        
        -- Max Spend in one go
        max(total_amount) as max_order_value,
        
        -- Device Type (Most frequent or recursive logic - here simplified to MAX)
        max(user_agent) as device_type,
        
        -- Days since last order (Recency)
        datediff(current_date(), max(created)) as days_since_last_order

    FROM default.raw_orders
    WHERE status='captured'
    GROUP BY customer_id
),

payment_methods as (
    -- 4. WALLET & CARDS
    SELECT 
        customer_id,
        -- Has used Apple Pay? (1=Yes, 0=No)
        max(case when is_apple_pay = 'true' then 1 else 0 end) as has_used_apple_pay,
        
        -- Count distinct cards used
        count(distinct card_first_six_digits || card_last_four_digits) as distinct_cards_used

    FROM default.raw_orders
    WHERE status='captured'
    GROUP BY customer_id
),

demographics as (
    -- 5. CUSTOMER PROFILE
    SELECT 
        customer_id,
        id_number,
        -- Age of Account (Days since registration)
        datediff(current_date(), created) as account_age_days
    FROM default.raw_customers
)

-- FINAL SELECT: Joining everything into a single Customer 360 View
SELECT 
    d.customer_id,
    
    -- Demographics
    d.account_age_days,
    
    -- Velocity (Plans)
    coalesce(n.No_of_instalment_plan_1m, 0) as plans_1m,
    coalesce(n.No_of_instalment_plan_3m, 0) as plans_3m,
    coalesce(n.No_of_instalment_plan_tot, 0) as plans_total,
    
    -- Risk (Unpaid)
    coalesce(u.No_of_unpaid_orders_1m, 0) as unpaid_1m,
    coalesce(u.No_of_unpaid_orders_tot, 0) as unpaid_total,
    coalesce(u.Avg_unpaid_amt, 0) as avg_unpaid_amount,
    
    -- Spend & Device
    coalesce(o.total_lifetime_spend, 0) as lifetime_spend,
    o.device_type,
    coalesce(o.days_since_last_order, 999) as recency_days,
    
    -- Payment
    coalesce(p.has_used_apple_pay, 0) as uses_apple_pay,
    coalesce(p.distinct_cards_used, 0) as distinct_cards,
    
    -- TARGET VARIABLE (For labeling if they are 'High Risk' right now)
    case when coalesce(u.No_of_unpaid_orders_tot, 0) > 0 then 1 else 0 end as is_defaulter

FROM demographics d
LEFT JOIN num_ins n ON d.customer_id = n.customer_id
LEFT JOIN unpaid_history u ON d.customer_id = u.customer_id
LEFT JOIN order_stats o ON d.customer_id = o.customer_id
LEFT JOIN payment_methods p ON d.customer_id = p.customer_id;
