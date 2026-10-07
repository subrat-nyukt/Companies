# Execution Guide: Creating the Feature Store in Databricks

You have the SQL file (`DATABRICKS_FULL_QUERY.sql`). Now, let's run it in Databricks to create your persistent Feature Store.

## Step 1: Create a New Notebook
1.  Log into your **Azure Databricks Workspace**.
2.  Click **"New"** (Top Left) -> **"Notebook"**.
3.  **Name**: `02_Feature_Engineering_Gold`
4.  **Default Language**: Select **SQL**. (This is important! It makes running the query easier).
5.  **Cluster**: Select your running cluster.

## Step 2: Paste and Run the SQL
1.  Open `DATABRICKS_FULL_QUERY.sql` on your computer and copy **ALL** the text.
2.  Go back to your Databricks Notebook.
3.  Paste the code into **Cell 1**.
4.  Press **Shift + Enter** to run the cell.

**What happens now?**
*   Spark will read the 3 raw tables (`raw_customers`, `raw_orders`, `raw_instalment_plans`).
*   It will execute all the joins and aggregations.
*   It will **create a new permanent table** named `default.gold_customer_risk_profile`.

## Step 3: Verify the Table Exists
Once the cell finishes running (you see a green "Command took X seconds"), verifying it is crucial.

1.  Create a **New Cell** (click the `+` button below the first cell).
2.  Run this quick check:
    ```sql
    SELECT * FROM default.gold_customer_risk_profile LIMIT 10;
    ```
3.  If you see rows of data with columns like `plans_1m`, `unpaid_total`, `device_type` — **CONGRATULATIONS!** 
    
    You have successfully built your Feature Store.

## Step 4: (Optional) Check the Schema
To understand what data types you have (e.g., Integer vs String), run:
```sql
DESCRIBE default.gold_customer_risk_profile;
```

---
**Next Stage**: Now that the table exists, we are ready for **Machine Learning**. We will create a *new* notebook for Model Training that reads from this table.
