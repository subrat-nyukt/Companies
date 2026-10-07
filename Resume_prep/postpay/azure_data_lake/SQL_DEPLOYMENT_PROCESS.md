# How to Deploy Your SQL Logic in Databricks

Yes! You should absolutely use this SQL logic. In fact, this SQL script **IS** your "Feature Engineering Pipeline."

Here is the professional workflow to deploy it in Databricks.

## The Architecture: "The Medallion Architecture"
In Databricks, we don't just run a query once. We organize data into 3 layers:
1.  **Bronze (Raw)**: The CSV files you uploaded (`raw_orders`, `raw_plans`).
2.  **Silver (Cleaned)**: We join the tables and clean the dates.
3.  **Gold (Features)**: **THIS IS YOUR SQL QUERY.** It aggregates the data into "Risk Features" (e.g., 5 unpaid orders).

---

## Step-by-Step Deployment Process

### Step 1: Create the "Feature Store" Notebook
1.  Open Databricks -> **New Notebook**.
2.  Name it: `Job_Feature_Engineering_Daily`.
3.  Copy your **ENTIRE SQL QUERY** into a cell.
4.  **Important**: Add `CREATE OR REPLACE TABLE gold.customer_risk_profile AS` at the very top.
    *   This tells Databricks to **save the result** into a permanent table, not just show it on screen.

```sql
-- Cell 1 in Notebook
CREATE OR REPLACE TABLE gold.customer_risk_profile AS
SELECT 
    customer_id,
    -- ... paste your massive logic here ...
    sum(case when created > current_date - 30 ...) as Unpaid_1m
FROM bronze.instalment_plans
GROUP BY customer_id;
```

### Step 2: Schedule it as a Job ("Deployment")
You don't want to click "Run" manually every day at 3 AM. You automate it.
1.  Click **"Workflows"** (left sidebar) -> **"Create Job"**.
2.  Name it: `Daily_Risk_Scoring_Pipeline`.
3.  **Task 1**: Select your Notebook (`Job_Feature_Engineering_Daily`).
4.  **Schedule**: Set it to run **Every Day at 01:00 AM**.

### Step 3: Connect to the ML Model
Now that the job runs every night, you have a fresh table `gold.customer_risk_profile` that is always up to date.

*   **Training**: You point your ML Training script to read from `gold.customer_risk_profile`.
*   **Inference**: When a user applies for a loan, the API queries this table: *"Hey, give me the risk profile for User_123."*

### Summary
1.  **Write SQL** (You did this).
2.  **Wrap in Notebook** (Add `CREATE TABLE AS...`).
3.  **Schedule Job** (Workflows tab).
4.  **Model Consumes Table** (ML Training).

This is how companies like Uber and Airbnb deploy their features!
