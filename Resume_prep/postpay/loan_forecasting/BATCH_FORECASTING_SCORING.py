# LOAN FORECASTING: BATCH SCORING
# This script runs weekly to predict which customers are likely to return.

import mlflow
import pandas as pd
from pyspark.sql.functions import col, current_timestamp

# 1. Load the Latest Registered Model
model_name = "loan_repeater_model"
model_uri = f"models:/{model_name}/latest"
# In a real environment, you'd use: model = mlflow.pyfunc.load_model(model_uri)
# For this simulation, we'll assume the model is available via a mockup or previous run.

print(f"Loading model from {model_uri}...")

# 2. Get Live Features for all Customers
live_data = spark.table("default.model_forecasting_features")

# 3. Predict Probability
# Here we use the Spark UDF approach or convert to Pandas for small batches
pdf = live_data.toPandas()
features = pdf[['frequency', 'recency', 'monetary', 'tenure']]

# Mocking prediction for demonstration
# In production, use: pdf['repeat_probability'] = model.predict_proba(features)[:, 1]
import numpy as np
pdf['repeat_probability'] = np.random.uniform(0.1, 0.9, size=len(pdf))

# 4. Filter for high-probability returners
pdf['is_predicted_repeater'] = (pdf['repeat_probability'] > 0.6).astype(int)

# 5. Save Results back to Gold Layer
spark_results = spark.createDataFrame(pdf) \
    .withColumn("prediction_timestamp", current_timestamp())

spark_results.write.mode("overwrite").saveAsTable("default.forecast_active_predictions")

# 6. Aggregate for Executive View
total_forecasted = pdf['repeat_probability'].sum()
print(f"📊 FORECAST SUMMARY:")
print(f"Predicted total repeat loans in next 1 year: {int(total_forecasted)}")
print(f"Customer base coverage: {len(pdf)} users")
print(f"High-intent users (Prob > 60%): {len(pdf[pdf['is_predicted_repeater'] == 1])}")

print("\n✅ Batch scoring complete. Results saved to: default.forecast_active_predictions")
