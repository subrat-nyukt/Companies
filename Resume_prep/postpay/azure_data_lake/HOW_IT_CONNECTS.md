# How Batch Scoring Connects to Your Registered Model

The "Connector" is literally just one line of code in the script:
`mlflow.pyfunc.load_model("models:/Postpay_Risk_Engine/Production")`

Here is the step-by-step flow (Visualized in `BATCH_SCORING_FLOW.mermaid`):

1.  **3:00 AM Trigger**: The Scheduled Job (`Production_Daily_Scoring`) wakes up.
2.  **Fetch the Brain (Step 1)**:
    *   The script asks the **Model Registry**: "Hey, give me the *current* `Production` version of `Postpay_Risk_Engine`."
    *   It doesn't ask for Version 1 or Version 5 specifically. It asks for the "Production" tag. This means if you promote V5 to Production tomorrow, the job picks up V5 automatically *without code changes*.
3.  **Fetch the Data (Step 2)**:
    *   The script reads the entire `gold_customer_risk_profile` table (10M rows).
4.  **Run Predictions (Step 3)**:
    *   It feeds the 10M rows into the loaded model (Brain).
    *   The model outputs 10M scores (0 or 1).
5.  **Save Results (Step 4)**:
    *   It writes these scores to `daily_risk_scores`.

So the connection is dynamic via the **Model Registry URL** (`models:/...`).
