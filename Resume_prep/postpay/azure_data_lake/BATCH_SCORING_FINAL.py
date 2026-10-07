# NIGHTLY BATCH SCORING JOB
# -------------------------------------------------------------------------
# This script scores ALL customers using the "Champion" model.
# Schedule this to run every night (e.g., 02:00 AM).
# -------------------------------------------------------------------------

import mlflow
from pyspark.sql.functions import struct, col, current_timestamp, lit

# 1. Configuration
# IMPORTANT: Use the FULL 3-level name: 'catalog.schema.model_name'
model_name = "workspace.default.Postpay_Risk_Engine" 
alias = "Champion"
input_table = "default.gold_customer_risk_profile"
output_table = "default.daily_risk_scores"

print(f"--- Starting Batch Scoring using Model: {model_name} (@{alias}) ---")

# 2. Load the Model as a Spark UDF
# Using the Unity Catalog '@Alias' syntax
predict_function = mlflow.pyfunc.spark_udf(spark, f"models:/{model_name}@{alias}")

# 3. Load the Latest Data
df = spark.table(input_table)

# 4. Prepare Features
# Remove ID and Label columns, keep only Features
feature_cols = [c for c in df.columns if c not in ['customer_id', 'is_defaulter']]

# 5. Run Predictions (Distributed)
# "struct(*feature_cols)" packs all columns into the format the model expects
df_scored = df.withColumn("risk_prediction", predict_function(struct(*feature_cols))) \
              .withColumn("scoring_timestamp", current_timestamp()) \
              .withColumn("model_version", lit(alias))

# 6. Save Logic (Append)
# We append so we keep a history of scores for Monitoring later
final_cols = ["customer_id", "scoring_timestamp", "model_version", "risk_prediction"] + feature_cols

df_scored.select(*final_cols) \
         .write.format("delta").mode("append").saveAsTable(output_table)

print(f"✅ Successfully scored {df_scored.count()} customers.")
print(f"Results saved to: {output_table}")
