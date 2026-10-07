# How to "Read" Your Risk Table in Databricks

Now that you have created `default.gold_customer_risk_profile`, here are 3 ways to view and understand the data.

## Option 1: The "Glance" (See the raw data)
Run this SQL command in a notebook cell to see the first 20 rows.
```sql
%sql
SELECT * FROM default.gold_customer_risk_profile LIMIT 20;
```
*   **What to look for**: Do you see `null` values? Do the numbers look realistic (e.g., `lifetime_spend` isn't negative)?

## Option 2: The "Fraud Check" (Compare Good vs. Bad)
This is the most important query. It shows you the **average behavior** of a defaulter vs. a good customer.
```sql
%sql
SELECT 
    is_defaulter,                -- 0 = Good, 1 = Bad
    count(*) as total_users,     -- How many users in each group
    avg(lifetime_spend) as avg_spend,    -- Do bad users spend more or less?
    avg(plans_1m) as avg_velocity_1m,    -- Do bad users rush to buy?
    avg(distinct_cards) as avg_cards     -- Do bad users shuffle cards?
FROM default.gold_customer_risk_profile
GROUP BY is_defaulter;
```
*   **Insight**: If `avg_velocity_1m` is **higher** for `is_defaulter = 1`, it confirms that fraudsters act quickly!

## Option 3: The "Data Profile" (Automatic Charts)
Databricks has a built-in UI tool.
1.  Run `SELECT * FROM default.gold_customer_risk_profile`
2.  Look at the results area. Next to "Table", click **"Data Profile"**.
3.  It will automatically show you:
    *   **Histograms**: How many users have 0 orders vs 100 orders?
    *   **Missing Values**: Are we missing device types?

## Option 4: Python (For Data Scientists)
If you prefer Python/Pandas styling:
```python
# Load table into a Spark DataFrame
df = spark.table("default.gold_customer_risk_profile")

# View summary statistics (Count, Mean, StdDev)
display(df.describe())
```
