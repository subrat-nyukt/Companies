# Phase 4 & 5: Deployment & Monitoring Guide

You have a trained model. Now you need to put it to work (Deploy) and make sure it keeps working (Monitor).

## Step 1: Register the Model (The "Gold Standard")
In `TRAIN_FINAL_MODEL.py`, we used `mlflow.sklearn.log_model`.
1.  Go to the **"Experiments"** tab in Databricks (left sidebar).
2.  Find your run.
3.  Click the **"Register Model"** button.
4.  Name it: `Postpay_Risk_Engine`.
5.  Transition the version from **None** -> **Staging** (for testing) -> **Production**.

## Step 2: Deployment (How to use it)
There are two ways to use the model:

### A. Real-Time (Online Serving)
*   **Use Case**: A user is clicking "Checkout" *right now*.
*   **Action**: Go to **"Models"** -> Click your Model -> Click **"Use Model for Inference"** -> **"Real-time"**.
*   **Result**: Databricks gives you a **REST API URL**. Your backend engineers send a JSON request, and get back "Reject" or "Approve" in 100ms.

### B. Batch Inference (Nightly Scoring)
*   **Use Case**: Update risk scores for *all* returning customers every night.
*   **Action**: Create a scheduled Job (Notebook).
*   **Code**:
    ```python
    import mlflow
    
    # 1. Load Production Model
    model = mlflow.pyfunc.load_model("models:/Postpay_Risk_Engine/Production")
    
    # 2. Load Latest Data
    df_new = spark.table("default.gold_customer_risk_profile").toPandas()
    
    # 3. Predict Risk
    df_new['risk_score'] = model.predict(df_new)
    
    # 4. Save to Database
    spark.createDataFrame(df_new).write.saveAsTable("default.daily_risk_scores")
    ```

## Step 3: Monitoring (Drift Detection)
Models decay. A model trained in 2023 might fail in 2024 because spending habits change.

**What to Monitor:**
1.  **Data Drift**: Is the input changing?
    *   *Example*: Suddenly 90% of users are on "Windows" instead of "iPhone". (Something is wrong with the data pipeline).
2.  **Concept Drift**: Is the output changing?
    *   *Example*: The model used to reject 5% of users. Now it rejects 50%. (The model needs retraining).

**How to do it in Databricks:**
*   Enable **Databricks Lakehouse Monitoring**. It automatically compares your "Training Data" stats vs. "Live Inference Data" stats and alerts you if they diverge.
