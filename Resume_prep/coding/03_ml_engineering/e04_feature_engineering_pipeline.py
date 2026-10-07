"""
=============================================================
E04 — Feature Engineering Pipeline
=============================================================
What This Tests:
  Can you build a clean, reusable feature engineering pipeline?
  - Point-in-time correct feature computation
  - Rolling window features (RFM-style)
  - Handling categoricals, missing values, and outliers
  - Pipeline that works identically in training and serving

Postpay Context:
  "We had 111 raw columns across 8 domains. This pipeline
   transforms them into model-ready features with proper
   temporal guards to prevent future-data leakage."

Run: python e04_feature_engineering_pipeline.py
Requires: pip install pandas scikit-learn
=============================================================
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ──────────────────────────────────────────────────────────────
# STEP 1: Generate synthetic transaction log
# ──────────────────────────────────────────────────────────────
def generate_transaction_log(n_drivers=200, n_months=12, seed=42):
    """
    Simulate a monthly transaction log for drivers.
    Each row = one month of a driver's activity.
    """
    rng = np.random.default_rng(seed)
    rows = []
    base = pd.Timestamp("2024-01-01")

    for driver_id in range(1, n_drivers + 1):
        risk = rng.normal(0, 1)  # latent risk factor
        for month in range(n_months):
            dt = base + pd.DateOffset(months=month)
            rows.append({
                "driver_id":    f"DRV_{driver_id:04d}",
                "month_date":   dt,
                "earnings":     max(0, rng.normal(1200 - 150 * risk, 300)),
                "trips":        max(0, int(rng.normal(90 - 10 * risk, 20))),
                "cancellations": max(0, int(rng.poisson(2 + 2 * max(risk, 0)))),
                "hard_brakes":  max(0, int(rng.poisson(5 + 3 * max(risk, 0)))),
                "complaints":   max(0, int(rng.poisson(0.5 + max(risk, 0)))),
                "bureau_score": int(np.clip(rng.normal(650 - 50 * risk, 60), 300, 850)),
                "bank_balance": max(0, rng.normal(3000 - 500 * risk, 800)),
            })

    df = pd.DataFrame(rows)
    # Inject some missing values (realistic)
    mask = rng.random(len(df)) < 0.05
    df.loc[mask, "bureau_score"] = np.nan
    mask2 = rng.random(len(df)) < 0.03
    df.loc[mask2, "bank_balance"] = np.nan
    return df


# ──────────────────────────────────────────────────────────────
# STEP 2: Rolling Window Feature Builder (Point-in-Time Safe)
# ──────────────────────────────────────────────────────────────
class RollingFeatureBuilder(BaseEstimator, TransformerMixin):
    """
    Compute rolling features per driver using only PAST data.
    
    For each driver-month row, computes:
      - avg, sum, std of a metric over the last N months
      - trend (last month vs avg of prior months)
    
    This is POINT-IN-TIME SAFE: no future data leaks in.
    """

    def __init__(self, columns, windows=(3, 6)):
        self.columns = columns
        self.windows = windows

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        df = X.copy()
        df = df.sort_values(["driver_id", "month_date"])

        for col in self.columns:
            for w in self.windows:
                # Rolling mean — shift(1) ensures we only use PAST months
                df[f"{col}_avg_{w}m"] = (
                    df.groupby("driver_id")[col]
                    .transform(lambda s: s.shift(1).rolling(w, min_periods=1).mean())
                )
                # Rolling sum
                df[f"{col}_sum_{w}m"] = (
                    df.groupby("driver_id")[col]
                    .transform(lambda s: s.shift(1).rolling(w, min_periods=1).sum())
                )

            # Trend: current month vs 3-month avg (positive = improving)
            df[f"{col}_trend"] = df[col] - df[f"{col}_avg_3m"]

        return df


# ──────────────────────────────────────────────────────────────
# STEP 3: Ratio and Derived Feature Builder
# ──────────────────────────────────────────────────────────────
class DerivedFeatureBuilder(BaseEstimator, TransformerMixin):
    """
    Compute derived features that capture business logic.
    - cancel_rate = cancellations / trips
    - earnings_per_trip = earnings / trips
    - risk_ratio = hard_brakes / trips
    """

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        df = X.copy()
        # Avoid division by zero
        safe_trips = df["trips"].replace(0, 1)
        df["cancel_rate"]       = df["cancellations"] / safe_trips
        df["earnings_per_trip"] = df["earnings"] / safe_trips
        df["brake_rate"]        = df["hard_brakes"] / safe_trips
        df["complaint_rate"]    = df["complaints"] / safe_trips
        return df


# ──────────────────────────────────────────────────────────────
# STEP 4: Missing Value Handler (Credit Risk Specific)
# ──────────────────────────────────────────────────────────────
class CreditMissingHandler(BaseEstimator, TransformerMixin):
    """
    Handle missing values with credit-risk-specific logic:
    - bureau_score missing → flag it (missingness IS informative)
    - Numeric NaNs → median imputation
    """

    def __init__(self, flag_columns=("bureau_score",)):
        self.flag_columns = flag_columns
        self.medians_ = {}

    def fit(self, X, y=None):
        df = X.copy()
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            self.medians_[col] = df[col].median()
        return self

    def transform(self, X):
        df = X.copy()
        # Create missingness flags
        for col in self.flag_columns:
            if col in df.columns:
                df[f"{col}_is_missing"] = df[col].isna().astype(int)

        # Median imputation for all numerics
        for col, median_val in self.medians_.items():
            if col in df.columns:
                df[col] = df[col].fillna(median_val)
        return df


# ──────────────────────────────────────────────────────────────
# STEP 5: Outlier Capper (Winsorization)
# ──────────────────────────────────────────────────────────────
class OutlierCapper(BaseEstimator, TransformerMixin):
    """
    Cap extreme outliers at the 1st and 99th percentiles.
    Prevents a single extreme record from distorting the model.
    """

    def __init__(self, columns, lower=0.01, upper=0.99):
        self.columns = columns
        self.lower = lower
        self.upper = upper
        self.bounds_ = {}

    def fit(self, X, y=None):
        df = X.copy()
        for col in self.columns:
            if col in df.columns:
                lo = df[col].quantile(self.lower)
                hi = df[col].quantile(self.upper)
                self.bounds_[col] = (lo, hi)
        return self

    def transform(self, X):
        df = X.copy()
        for col, (lo, hi) in self.bounds_.items():
            if col in df.columns:
                df[col] = df[col].clip(lo, hi)
        return df


# ──────────────────────────────────────────────────────────────
# STEP 6: Full Pipeline Assembly
# ──────────────────────────────────────────────────────────────
def build_feature_pipeline():
    """
    Assemble the full feature engineering pipeline.
    This pipeline is REUSABLE: fit on training data, transform on serving data.
    """
    rolling_cols  = ["earnings", "trips", "cancellations", "hard_brakes"]
    cap_cols      = ["earnings", "bank_balance", "bureau_score"]

    pipeline = Pipeline([
        ("derived",  DerivedFeatureBuilder()),
        ("rolling",  RollingFeatureBuilder(columns=rolling_cols, windows=(3, 6))),
        ("missing",  CreditMissingHandler(flag_columns=("bureau_score",))),
        ("capping",  OutlierCapper(columns=cap_cols)),
    ])
    return pipeline


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  E04 — Feature Engineering Pipeline")
    print("=" * 60)

    # 1. Generate data
    print("\n[1] Generating transaction log...")
    txn = generate_transaction_log(n_drivers=100, n_months=12)
    print(f"  Shape: {txn.shape}  |  Drivers: {txn['driver_id'].nunique()}")
    print(f"  Missing bureau_score: {txn['bureau_score'].isna().sum()}")
    print(f"  Missing bank_balance: {txn['bank_balance'].isna().sum()}")

    # 2. Build and run pipeline
    print("\n[2] Building feature pipeline...")
    pipeline = build_feature_pipeline()

    # Temporal split: fit on first 8 months, transform on last 2
    train_mask = txn["month_date"] <= "2024-08-31"
    oot_mask   = txn["month_date"] >= "2024-11-01"

    train_raw = txn[train_mask].copy()
    oot_raw   = txn[oot_mask].copy()

    print(f"  Train rows: {len(train_raw)}  |  OOT rows: {len(oot_raw)}")

    # Fit on training, transform both
    train_feat = pipeline.fit_transform(train_raw)
    oot_feat   = pipeline.transform(oot_raw)

    # 3. Show results
    print("\n[3] Feature columns created:")
    new_cols = [c for c in train_feat.columns if c not in txn.columns]
    for c in sorted(new_cols):
        print(f"  + {c}")

    print(f"\n  Total features: {len(train_feat.columns)} (was {len(txn.columns)})")

    # 4. Verify no NaNs remain
    nan_count = train_feat.select_dtypes(include=[np.number]).isna().sum().sum()
    print(f"\n[4] Remaining NaNs after pipeline: {nan_count}")
    if nan_count == 0:
        print("  [OK] All missing values handled")
    else:
        print("  [!] Some NaNs remain (from rolling windows on first months)")

    # 5. Sample output
    print("\n[5] Sample row (driver DRV_0001, last month):")
    sample = train_feat[train_feat["driver_id"] == "DRV_0001"].iloc[-1]
    for col in sorted(new_cols):
        val = sample.get(col, "N/A")
        if isinstance(val, float):
            print(f"  {col:35s} = {val:.4f}")
        else:
            print(f"  {col:35s} = {val}")

    print("\n" + "=" * 60)
    print("  Interview Talking Points:")
    print("  1. Pipeline is sklearn-compatible => fit(train), transform(serve)")
    print("  2. Rolling features use shift(1) => NO future data leakage")
    print("  3. Missing flags: bureau_score_is_missing is itself a risk signal")
    print("  4. Outlier capping prevents extreme values from distorting trees")
    print("  5. Same pipeline runs in training AND production => no skew")
    print("=" * 60)
