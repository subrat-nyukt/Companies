# LAKEHOUSE MONITORING SETUP (Drift Detection)
# -------------------------------------------------------------------------
# This script enables automatic Databricks Monitoring on your output table.
# Run this ONCE to configure the monitor.
# -------------------------------------------------------------------------

from databricks import lakehouse
from databricks.lakehouse import monitoring

# 1. Configuration
monitor_table_name = "default.daily_risk_scores"
assets_dir = "/Users/your_email/postpay_monitoring" # Where to save the dashboard assets

print(f"--- Configuring Drift Monitor for: {monitor_table_name} ---")

# 2. Define the Monitor
# We tell Databricks: "Watch this table. If the stats change too much, tell me."
try:
    info = monitoring.create_monitor(
        table_name=monitor_table_name,
        profile_type=monitoring.MonitorProfileType.INFERENCE_LOG,
        
        # How often to check for drift?
        analysis_schedule=monitoring.MonitorSchedule(
            quartz_cron_expression="0 0 12 * * ?", # Run daily at noon
            timezone_id="UTC"
        ),
        
        # What columns represent the prediction?
        inference_log_info=monitoring.InferenceLogInfo(
            model_id_col="model_version",
            prediction_col="risk_prediction",
            timestamp_col="scoring_timestamp",
            problem_type=monitoring.MonitorProblemType.CLASSIFICATION
        ),
        
        # Where to store the dashboard definition (optional but good practice)
        output_schema_name="default", # Stores metric tables here
        assets_dir=assets_dir
    )
    print("✅ Monitor Created Successfully!")
    print(f"Go to 'Catalog' -> Tables -> '{monitor_table_name}' -> 'Quality' tab to see the dashboard.")

except Exception as e:
    print(f"⚠️ Monitor might already exist or table is empty. Error: {e}")
    # Simple update if it exists
    # monitoring.update_monitor(...)
