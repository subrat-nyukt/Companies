"""
Production Pipeline: Auto Train/Val/OOT Split + Score Logging
=============================================================
Simulates what runs as a SCHEDULED JOB on Azure Databricks each month.

What it does:
  - Reads loan applications from Delta Lake (simulated here as a DataFrame)
  - Auto-detects date cutoffs based on latest data (no hardcoding dates)
  - Trains model on train set
  - Scores all 3 sets and writes results to a scores table
  - Logs AUC metrics to MLflow (model registry)

In real Databricks: replace pd.DataFrame with spark.read.format("delta").load(...)
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline

# ── Simulate MLflow (in Databricks you'd use: import mlflow) ────────────────
class FakeMLflow:
    """Mimics mlflow.log_metric() so you can run this without Databricks."""
    def log_param(self, k, v):  print(f"  [MLflow] param  | {k}: {v}")
    def log_metric(self, k, v): print(f"  [MLflow] metric | {k}: {v:.4f}")

mlflow = FakeMLflow()

# ── STEP 1: Load data from Delta Lake ───────────────────────────────────────
# In Databricks:
#   df = spark.read.format("delta").load("/mnt/postpay/loan_applications").toPandas()
# Here we simulate it:
np.random.seed(42)
n = 500
df = pd.DataFrame({
    "driver_id": [f"D-{i:04d}" for i in np.random.randint(1, 150, n)],
    "app_date":  pd.date_range("2025-01-01", "2025-12-31", periods=n),
    "avg_spend_90d":  np.random.randint(1000, 6000, n),
    "txn_count_90d":  np.random.randint(1, 25, n),
    "loan_amount":    np.random.randint(5000, 50000, n),
    "label":          np.random.choice([0, 1], n, p=[0.80, 0.20])
}).sort_values("app_date").reset_index(drop=True)

print(f"Loaded {len(df)} rows | date range: {df['app_date'].min().date()} → {df['app_date'].max().date()}")

# ── STEP 2: Auto-detect cutoff dates (no hardcoding!) ───────────────────────
# Always based on the LATEST app_date in the table.
# This means when new data arrives next month, cutoffs shift automatically.

latest_date = df["app_date"].max()

oot_cutoff = latest_date - timedelta(days=60)   # last 2 months = OOT
val_cutoff = latest_date - timedelta(days=120)  # 2 months before OOT = Val
# everything before val_cutoff = Train

print(f"\nAuto-detected cutoffs (based on latest date: {latest_date.date()}):")
print(f"  Train : app_date <= {val_cutoff.date()}")
print(f"  Val   : {val_cutoff.date()} < app_date <= {oot_cutoff.date()}")
print(f"  OOT   : app_date > {oot_cutoff.date()}")

# ── STEP 3: Split ────────────────────────────────────────────────────────────
train = df[df["app_date"] <= val_cutoff]
val   = df[(df["app_date"] > val_cutoff) & (df["app_date"] <= oot_cutoff)]
oot   = df[df["app_date"] > oot_cutoff]

print(f"\n  Train : {len(train)} rows | default rate: {train['label'].mean():.1%}")
print(f"  Val   : {len(val)}  rows | default rate: {val['label'].mean():.1%}")
print(f"  OOT   : {len(oot)}  rows | default rate: {oot['label'].mean():.1%}")

# ── STEP 4: Train model ──────────────────────────────────────────────────────
features = ["avg_spend_90d", "txn_count_90d", "loan_amount"]

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("model",  LogisticRegression(max_iter=1000, class_weight="balanced"))
])
pipe.fit(train[features], train["label"])

# ── STEP 5: Score all 3 sets & compute AUC ──────────────────────────────────
def score_set(pipe, X, y, split_name):
    proba = pipe.predict_proba(X)[:, 1]
    auc   = roc_auc_score(y, proba) if y.nunique() > 1 else None
    return proba, auc

train_proba, train_auc = score_set(pipe, train[features], train["label"], "train")
val_proba,   val_auc   = score_set(pipe, val[features],   val["label"],   "val")
oot_proba,   oot_auc   = score_set(pipe, oot[features],   oot["label"],   "oot")

print(f"\n  AUC — Train: {train_auc:.4f} | Val: {val_auc:.4f} | OOT: {oot_auc:.4f}")

# ── STEP 6: Log to MLflow (model registry in Databricks) ────────────────────
print("\n[MLflow logging — in Databricks this writes to the experiment UI]")
mlflow.log_param("train_cutoff",    str(val_cutoff.date()))
mlflow.log_param("oot_cutoff",      str(oot_cutoff.date()))
mlflow.log_param("features",        str(features))
mlflow.log_metric("auc_train",      train_auc)
mlflow.log_metric("auc_val",        val_auc)
mlflow.log_metric("auc_oot",        oot_auc)
mlflow.log_metric("auc_degradation", train_auc - oot_auc)  # model decay signal

# ── STEP 7: Write scores back to Delta table ─────────────────────────────────
# In Databricks:
#   scores_spark_df.write.format("delta").mode("append").save("/mnt/postpay/model_scores")
# Here we simulate the output table:

train["score"] = train_proba; train["split"] = "train"
val["score"]   = val_proba;   val["split"]   = "val"
oot["score"]   = oot_proba;   oot["split"]   = "oot"

model_scores_table = pd.concat([train, val, oot])[
    ["driver_id", "app_date", "split", "score", "label"]
].reset_index(drop=True)

print("\n[model_scores] Delta table — sample of what gets written back to DB:")
print(model_scores_table.groupby("split").head(2).to_string(index=False))

# ── STEP 8: Drift alert — flag if OOT AUC drops more than 5% vs Val ─────────
print("\n── Model Health Check ──────────────────────────────────────────────")
degradation = val_auc - oot_auc
if degradation > 0.05:
    print(f"  🚨 ALERT: AUC dropped {degradation:.2%} from Val to OOT — retrain needed!")
else:
    print(f"  ✅ Model stable: Val→OOT degradation = {degradation:.2%}")

print("""
─────────────────────────────────────────────────────────────
How this runs in production (Azure Databricks):
  1. Databricks Workflow (Cron: 1st of every month, 2am)
  2. Reads new loan applications from Delta Lake automatically
  3. Cutoff dates shift forward by 1 month each run (no manual changes)
  4. Scores written to model_scores Delta table → Power BI picks them up
  5. MLflow tracks every run — you can compare Jan model vs Feb model
─────────────────────────────────────────────────────────────
""")
