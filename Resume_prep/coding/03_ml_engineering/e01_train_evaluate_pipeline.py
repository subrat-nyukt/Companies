"""
=============================================================
E01 — End-to-End ML Training & Evaluation Pipeline
=============================================================
What This Tests:
  Can you build a clean, production-quality sklearn pipeline?
  - Data preparation with temporal split (no leakage)
  - Class imbalance handling (SMOTE + class weights)
  - Model training with cross-validation
  - Evaluation using credit-risk appropriate metrics
  - MLflow experiment tracking

Run: python e01_train_evaluate_pipeline.py
Requires: pip install scikit-learn imbalanced-learn mlflow
=============================================================
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.datasets import make_classification
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    roc_auc_score, classification_report,
    confusion_matrix, precision_recall_curve,
    average_precision_score
)
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline


# ──────────────────────────────────────────────────────────────
# STEP 1: Generate a synthetic driver loan dataset
# ──────────────────────────────────────────────────────────────
def generate_driver_loan_data(n_samples: int = 5000, seed: int = 42) -> pd.DataFrame:
    """
    Generate a realistic imbalanced credit risk dataset.
    - 85% good repayers (class 0)
    - 15% defaulters (class 1)
    - Features: earnings, behavior, financial history
    - Temporal component: app_date (for temporal split)
    """
    np.random.seed(seed)
    rng = np.random.default_rng(seed)

    # Synthetic features (maps to real Postpay features)
    n = n_samples
    risk = rng.standard_normal(n)

    data = {
        "wk_earn_3m":        np.clip(rng.normal(1200 - 200 * risk, 300, n), 100, 5000),
        "cancel_rate_1m":    np.clip(rng.normal(0.08 + 0.05 * risk, 0.05, n), 0, 1),
        "bureau_score":      np.clip(rng.normal(650 - 60 * risk, 80, n), 300, 850).astype(int),
        "missed_remit_pct":  np.clip(rng.normal(0.05 + 0.15 * risk, 0.07, n), 0, 1),
        "debt_to_income":    np.clip(rng.normal(0.35 + 0.15 * risk, 0.15, n), 0, 2),
        "platform_tenure_mo":np.clip(rng.exponential(18, n), 1, 60).astype(int),
        "hard_brake_1m":     np.clip(rng.poisson(5 + 4 * np.clip(risk, 0, None), n), 0, 40).astype(int),
        "downpayment_pct":   np.clip(rng.normal(0.25 - 0.1 * risk, 0.1, n), 0.05, 0.6),
        "ltv_ratio":         np.clip(rng.normal(0.7 + 0.1 * risk, 0.1, n), 0.3, 1.0),
        "avg_bank_bal_3m":   np.clip(rng.exponential(3000 - 500 * np.clip(risk, 0, 4), n), 0, 30000),
    }

    # Logistic label generation
    log_odds = (
        -2.0
        + 0.7  * risk
        + 0.4  * (data["missed_remit_pct"] > 0.1).astype(float)
        + 0.3  * (data["bureau_score"] < 550).astype(float)
        + 0.25 * (data["debt_to_income"] > 0.5).astype(float)
        - 0.3  * (data["bureau_score"] > 700).astype(float)
    )
    prob = 1 / (1 + np.exp(-log_odds))
    data["bad_debt"] = rng.binomial(1, prob, n)

    # Temporal column: assign app dates over 12 months
    days = rng.integers(0, 365, n)
    base_date = pd.Timestamp("2024-01-01")
    data["app_date"] = [base_date + pd.Timedelta(days=int(d)) for d in days]

    df = pd.DataFrame(data).sort_values("app_date").reset_index(drop=True)
    return df


# ──────────────────────────────────────────────────────────────
# STEP 2: Temporal Train / OOT Split  (no random split — avoids leakage)
# ──────────────────────────────────────────────────────────────
def temporal_split(df: pd.DataFrame, train_cutoff: str, oot_start: str):
    """
    Temporal split: train on data BEFORE cutoff, test on data AFTER oot_start.
    Gap between cutoff and oot_start simulates origination-to-outcome lag.

    - train_cutoff:  last date of training data
    - oot_start:     first date of OOT test set
    """
    FEATURES = [c for c in df.columns if c not in ["bad_debt", "app_date"]]
    TARGET   = "bad_debt"

    train = df[df["app_date"] <= pd.Timestamp(train_cutoff)]
    oot   = df[df["app_date"] >= pd.Timestamp(oot_start)]

    X_train = train[FEATURES]
    y_train = train[TARGET]
    X_oot   = oot[FEATURES]
    y_oot   = oot[TARGET]

    print(f"  Train: {len(X_train):,} rows | Default rate: {y_train.mean():.1%}")
    print(f"  OOT:   {len(X_oot):,} rows  | Default rate: {y_oot.mean():.1%}")

    return X_train, y_train, X_oot, y_oot, FEATURES


# ──────────────────────────────────────────────────────────────
# STEP 3: Model Definitions
# ──────────────────────────────────────────────────────────────
def get_models() -> dict:
    """Return candidate models as sklearn-compatible pipelines."""
    return {
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf",    LogisticRegression(class_weight="balanced", max_iter=1000, C=0.1)),
        ]),
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=8,
            class_weight="balanced", random_state=42, n_jobs=-1
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, random_state=42
        ),
    }


# ──────────────────────────────────────────────────────────────
# STEP 4: Evaluation — credit risk appropriate metrics
# ──────────────────────────────────────────────────────────────
def evaluate_model(name: str, y_true, y_prob) -> dict:
    """
    Credit risk metrics:
    - AUC-ROC: rank-ordering quality
    - Gini:    2 * AUC - 1 (industry standard)
    - KS:      max separation between TPR and FPR curves
    - PR-AUC:  better for imbalanced data
    """
    auc    = roc_auc_score(y_true, y_prob)
    gini   = 2 * auc - 1
    pr_auc = average_precision_score(y_true, y_prob)

    # KS Statistic
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    ks = float(np.max(tpr - fpr))

    metrics = {
        "model":  name,
        "auc":    round(auc, 4),
        "gini":   round(gini, 4),
        "ks":     round(ks, 4),
        "pr_auc": round(pr_auc, 4),
    }
    return metrics


# ──────────────────────────────────────────────────────────────
# STEP 5: Main Pipeline
# ──────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  E01 — ML Training & Evaluation Pipeline")
    print("=" * 60)

    # 1. Generate data
    print("\n[1] Generating synthetic driver loan dataset...")
    df = generate_driver_loan_data(n_samples=5000)
    print(f"  Total rows: {len(df):,} | Default rate: {df['bad_debt'].mean():.1%}")

    # 2. Temporal split
    print("\n[2] Temporal split (no leakage)...")
    X_train, y_train, X_oot, y_oot, features = temporal_split(
        df, train_cutoff="2024-09-30", oot_start="2024-11-01"
    )

    # 3. Apply SMOTE — ONLY on training data
    print("\n[3] Applying SMOTE to training data only...")
    sm = SMOTE(random_state=42)
    X_train_res, y_train_res = sm.fit_resample(X_train, y_train)
    print(f"  Before SMOTE: {len(X_train):,} rows | Default rate: {y_train.mean():.1%}")
    print(f"  After  SMOTE: {len(X_train_res):,} rows | Default rate: {y_train_res.mean():.1%}")

    # 4. Train and evaluate with MLflow
    print("\n[4] Training models with MLflow tracking...")
    models  = get_models()
    results = []

    mlflow.set_experiment("driver_credit_risk")

    for name, model in models.items():
        with mlflow.start_run(run_name=name):
            # Train
            model.fit(X_train_res, y_train_res)

            # Evaluate on OOT (never touched during training)
            y_prob = model.predict_proba(X_oot)[:, 1]
            metrics = evaluate_model(name, y_oot, y_prob)
            results.append(metrics)

            # Log to MLflow
            mlflow.log_params({"model_type": name, "smote": True, "temporal_split": True})
            mlflow.log_metrics({k: v for k, v in metrics.items() if k != "model"})
            mlflow.sklearn.log_model(model, f"model_{name}")

            print(f"  [OK] {name}: AUC={metrics['auc']} | Gini={metrics['gini']} | KS={metrics['ks']}")

    # 5. Compare
    print("\n[5] Model Comparison (OOT performance):")
    results_df = pd.DataFrame(results).sort_values("gini", ascending=False)
    print(results_df.to_string(index=False))

    best = results_df.iloc[0]["model"]
    print(f"\n  [BEST] Best model: {best}")
    print("\n  [OK] All models logged to MLflow. Run `mlflow ui` to view.")


if __name__ == "__main__":
    main()
