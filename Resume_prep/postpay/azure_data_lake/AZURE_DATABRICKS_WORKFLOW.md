# End-to-End ML Workflow in Azure Databricks

This guide outlines the professional workflow for building a Credit Risk/Fraud Detection model using Azure Databricks and Azure Data Lake Storage (ADLS).

## Phase 1: Connection & Data Loading (The "Mount")
**Goal**: Make the files in your Data Lake accessible to Databricks.

1.  **Authentication**: Use a Service Principal to securely connect.
2.  **Mounting**: "Map" the Azure Storage container to a local path (e.g., `/mnt/data`).

```python
# 1. Define configuration (Secrets are stored in Azure Key Vault!)
configs = {
  "fs.azure.account.auth.type": "OAuth",
  "fs.azure.account.oauth.provider.type": "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
  "fs.azure.account.oauth2.client.id": dbutils.secrets.get(scope="key-vault", key="client-id"),
  "fs.azure.account.oauth2.client.secret": dbutils.secrets.get(scope="key-vault", key="client-secret"),
  "fs.azure.account.oauth2.client.endpoint": "https://login.microsoftonline.com/<tenant-id>/oauth2/token"
}

# 2. Mount the container (Run only once)
dbutils.fs.mount(
  source = "abfss://raw-data@<storage-account>.dfs.core.windows.net/",
  mount_point = "/mnt/postpay-data",
  extra_configs = configs
)
```

## Phase 2: Data Ingestion & SQL (Spark SQL)
**Goal**: Run your complex SQL query on the massive dataset in the Data Lake.

1.  **Load Raw Data**: Read the raw CSV/Parquet files.
2.  **Create Temp View**: This allows you to run standard SQL queries.

```python
# Read the raw parquet/delta files
df_raw = spark.read.format("delta").load("/mnt/postpay-data/instalment_plans")

# Create a temporary view so we can write SQL
df_raw.createOrReplaceTempView("instalment_plans")

# NOW run your massive SQL query directly!
risk_features_df = spark.sql("""
    SELECT 
        customer_id,
        sum(case when status='paid' then 1 else 0 end) as paid_count,
        ... (Your Logic Here) ...
    FROM instalment_plans
    GROUP BY customer_id
""")

# Save this "Feature Store" table for later use
risk_features_df.write.format("delta").saveAsTable("analytics.customer_risk_features")
```

## Phase 3: Exploratory Data Analysis (Databricks Notebooks)
**Goal**: Visualize the data distribution.

1.  **Built-in Data Profile**: specific Databricks feature.
    *   Click "Data Profile" tab next to the results. It automatically shows histograms, missing values, and correlations.
2.  **Visualizations**:
    *   Use `display(df)` to create interactive charts (Bar, Scatter, Line) without writing code.

```python
# Load the feature table we just created
df = spark.table("analytics.customer_risk_features")

# Native interactive grid
display(df) 
```

## Phase 4: Model Training (MLflow & Scikit-Learn)
**Goal**: Train the model and track experiments.
Databricks has **MLflow** built-in to track every run (parameters, accuracy, model file).

```python
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# Convert to Pandas for Scikit-Learn (if data fits in memory)
pdf = df.toPandas()
X = pdf.drop("is_default", axis=1)
y = pdf["is_default"]

# Start an MLflow experiment
with mlflow.start_run(run_name="RandomForest_v1"):
    
    # split
    X_train, X_test, y_train, y_test = train_test_split(X, y)
    
    # train
    rf = RandomForestClassifier(n_estimators=100)
    rf.fit(X_train, y_train)
    
    # log parameters and metrics automatically
    accuracy = rf.score(X_test, y_test)
    mlflow.log_metric("accuracy", accuracy)
    
    # log the model itself
    mlflow.sklearn.log_model(rf, "model")
    
    print(f"Model trained with accuracy: {accuracy}")
```

## Phase 5: Deployment (Model Registry)
**Goal**: Push the best model to production.

1.  Go to the **Models** tab in Databricks.
2.  Find your "RandomForest_v1" run.
3.  Click **"Register Model"** -> Name it `Postpay_Risk_Model`.
4.  Transition stage to **Staging** -> **Production**.

## Real-time Inference Code
When the backend app calls the model:

```python
import mlflow

# Load the Production model
model = mlflow.pyfunc.load_model("models:/Postpay_Risk_Model/Production")

# Predict
risk_score = model.predict(new_customer_data)
```
