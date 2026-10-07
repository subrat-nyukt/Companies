# Project Roadmap: Credit Risk Prediction

## Objective: 
**Prevent Financial Loss** by automatically rejecting customers who are likely to default (not pay back their loan).

---

## Step 1: Data Ingestion (The Foundation)
**Action**: Uploading `raw_customers.csv`, `raw_orders.csv`, and `raw_instalment_plans.csv` to Databricks.

*   **Why are we doing this?** 
    *   Machine Learning requires **History**. We cannot predict if a *new* customer is risky unless we study the behavior of *past* customers.
    *   These 3 files contain the "Ground Truth": who paid on time, who paid late, and who never paid at all.
*   **Alignment to Objective**: 
    *   Without this data, we are guessing. This step gives us the **evidence** needed to train the system.

---

## Step 2: Feature Engineering (The Logic)
**Action**: Running the Spark SQL query to create `customer_risk_features` (calculating `unpaid_count`, `debt_ratio`, `avg_order_value`).

*   **Why are we doing this?** 
    *   Raw data (e.g., "Order ID: 10592") is useleless to a model. It doesn't tell a story.
    *   We need to transform *transactions* into *behaviors*. 
    *   **Example**: 
        *   *Raw*: "User A bought a shoe." (Neutral)
        *   *Feature*: "User A has **3 unpaid loans** in the last month." (RISKY!)
*   **Alignment to Objective**: 
    *   This step identifies the **Warning Signs**. We are defining *what* makes a customer risky (e.g., High Debt Ratio). If we get this wrong, the model will be blind to fraud.

---

## Step 3: Model Training (The Brain)
**Action**: Using `RandomForestClassifier` to learn patterns from the `customer_risk_features` table.

*   **Why are we doing this?** 
    *   We can't manually review every single transaction; it's too slow.
    *   The Model acts as an **Automated Gatekeeper**. It looks at thousands of past examples and "learns" a rule-set.
    *   *Rule Learned*: "IF `unpaid_count > 0` AND `device_type = 'Android'`, THEN `Probability of Default = 85%`."
*   **Alignment to Objective**: 
    *   This is the **Decision Maker**. In production, this model will run in < 100ms during checkout. 
    *   If the model predicts "High Risk", we **Block the Transaction** -> **Saving the Money**.

---

## Step 4: Monitoring (The Safety Net) - *Upcoming*
**Action**: Tracking `Accuracy`, `Precision`, and `Recall` in MLflow.

*   **Why are we doing this?** 
    *   Models can rot. A model trained in 2020 might not work in 2023 (e.g., COVID changed spending habits).
    *   We need to know when the model starts making mistakes.
*   **Alignment to Objective**: 
    *   Ensures the system **continues** to stop fraud over time. If accuracy drops, we stop saving money.
