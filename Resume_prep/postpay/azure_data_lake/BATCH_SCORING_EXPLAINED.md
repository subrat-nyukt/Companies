# Explanation of BATCH_SCORING.py

| Code Line | What it Does (Plain English) |
| :--- | :--- |
| `model_name = "Risk_Engine"` | **The Brain**: Defines WHICH brain we want to use (you renamed it). |
| `input_table = "default.gold..."` | **The Exam**: Defines WHERE the customer data lives. |
| `predict_function = mlflow.pyfunc.spark_udf(...)` | **The Magic**: Downloads the model from the Registry and converts it into a "Spark Function" so 50 computers can run it at once. |
| `df = spark.table(input_table)` | **Read**: Loads the customer data into memory. |
| `feature_cols = [...]` | **Filter**: Removes the 'Answer Key' (is_defaulter) and 'Names' (customer_id) so the model only sees the Features (Unpaid Count, Spend). |
| `df.withColumn("risk_prediction", ...)` | **Predict**: Runs the model on every row. Adds a new column `risk_prediction` (0 or 1). |
| `.withColumn("scoring_timestamp", ...)` | **Stamp**: Adds "Today's Date" so we know WHEN this score was calculated. |
| `.write.mode("append").saveAsTable(...)` | **Save**: Writes the results to the database. Uses "Append" so we keep history (Yesterday's scores + Today's scores). |
