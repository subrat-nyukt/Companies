# How to Set Up Lakehouse Monitoring (UI Method)

You can set up drift detection entirely through the Databricks UI without writing Python code.

## Prerequisites
1.  **Table Exists**: You must have run `BATCH_SCORING.py` at least once so the table `default.daily_risk_scores` exists.
2.  **Unity Catalog**: Your table needs to be in Unity Catalog (e.g., `workspace.default.daily_risk_scores`).

## Step-by-Step Setup

1.  **Go to Catalog Explorer**:
    *   Click **"Catalog"** in the left sidebar.
    *   Navigate to your table: `default` -> `daily_risk_scores`.

2.  **Enable Monitoring**:
    *   Look for a tab named **"Quality"** (sometimes called "Monitoring" or "Insights") next to "Sample Data".
    *   Click the big blue button **"Monitor"** or **"Create Monitor"**.

3.  **Configure the Monitor**:
    *   **Profile Type**: Select **"Inference"** (since this is model output).
    *   **Prediction Column**: Select `risk_prediction`.
    *   **Label Column**: Leave blank (unless you have ground truth already).
    *   **Timestamp Column**: Select `scoring_timestamp`.
    *   **Model ID Column**: Select `model_version`.
    *   **Problem Type**: Select **"Classification"**.

4.  **Schedule It**:
    *   **Frequency**: "Daily".
    *   **Output Schema**: Select `default` (This is where it saves the metric tables).

5.  **Click "Create"**:
    *   Databricks will now run a job to analyze your table.
    *   It creates a **Dashboard** automatically.

## Viewing the Dashboard
Once the job finishes (wait 5-10 mins):
1.  Go back to the **"Quality"** tab of your table.
2.  Click **"View Dashboard"**.
3.  You will see charts for:
    *   **Data Drift**: Distances between yesterday's data and today's.
    *   **Model Performance**: Number of High Risk vs Low Risk predictions over time.
