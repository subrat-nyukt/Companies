# NIGHTLY BATCH SCORING JOB
# -------------------------------------------------------------------------
# This script loads the "Production" model and scores ALL customers.
# Schedule this to run every night (e.g., 02:00 AM) using Databricks Workflows.
# -------------------------------------------------------------------------

import mlflow
from pyspark.sql.functions import struct, col, current_timestamp, lit

# 1. Configuration
model_name = "Postpay_Risk_Engine"
stage = "Production"
input_table = "default.gold_customer_risk_profile"
output_table = "default.daily_risk_scores"

print(f"--- Starting Batch Scoring using Model: {model_name} ({stage}) ---")

# 2. Load the Model as a Spark UDF (User Defined Function)
# This allows us to distribute the prediction across the cluster (Fast!)
predict_function = mlflow.pyfunc.spark_udf(spark, f"models:/{model_name}/{stage}")

# 3. Load the Latest Data
df = spark.table(input_table)

# 4. Prepare Features
# We need to pass the exact columns the model expects.
# Note: If you used 'device_type' mapping in training, ensure your pipeline handles it here too.
# For simplicity, assuming the gold table matches training requirements or model handles it.
# We'll select all columns except IDs/Labels for prediction
feature_cols = [c for c in df.columns if c not in ['customer_id', 'is_defaulter']]

# 5. Run Predictions (Distributed)
# "struct(*feature_cols)" packs all columns into the format the model expects
df_scored = df.withColumn("risk_prediction", predict_function(struct(*feature_cols))) \
              .withColumn("scoring_timestamp", current_timestamp()) \
              .withColumn("model_version", lit(stage))

# 6. Save Logic (Append or Overwrite)
# We append so we keep a history of scores for Monitoring later
df_scored.select("customer_id", "scoring_timestamp", "model_version", "risk_prediction", *feature_cols) \
         .write.mode("append").saveAsTable(output_table)

print(f"✅ Successfully scored {df_scored.count()} customers.")
print(f"Results saved to: {output_table}")
