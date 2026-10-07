"""
Practice: Imbalanced Dataset — Under / Over / SMOTE / Class Weights
Scenario: PostPay trucking loans — 1,000 drivers, ~18% default rate
Install: pip install imbalanced-learn scikit-learn pandas numpy
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, classification_report
from imblearn.over_sampling import SMOTE, RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler

np.random.seed(42)

# ── Dataset: 1,000 drivers, 18% default ─────────────────────────────────────
N = 1000
avg_spend   = np.random.randint(1000, 6000, N)
loan_amount = np.random.randint(5000, 50000, N)
txn_count   = np.random.randint(1, 25, N)

# default is more likely if high loan + low spend
prob = 0.05 + 0.10*(loan_amount > 30000) + 0.08*(avg_spend < 2000)
labels = np.random.binomial(1, prob)

X = np.column_stack([avg_spend, loan_amount, txn_count])
y = labels

print(f"Total: {N} | Defaulted: {y.sum()} ({y.mean():.0%}) | No Default: {(y==0).sum()}")

# ── Split FIRST (always) ─────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test  = scaler.transform(X_test)           # fit on train only!

print(f"\nTrain: {len(y_train)} rows | Test: {len(y_test)} rows (untouched)")
print(f"Train class dist → 0:{(y_train==0).sum()}  1:{(y_train==1).sum()}")

# ── ❌ WRONG: SMOTE before split (leakage demo) ──────────────────────────────
print("\n❌ WRONG — SMOTE applied BEFORE split:")
X_sm_all, y_sm_all = SMOTE(random_state=42).fit_resample(X, y)   # full dataset!
Xtr_l, Xte_l, ytr_l, yte_l = train_test_split(X_sm_all, y_sm_all, test_size=0.2)
Xtr_l = scaler.fit_transform(Xtr_l); Xte_l = scaler.transform(Xte_l)
m_leaky = LogisticRegression(max_iter=500).fit(Xtr_l, ytr_l)
print(f"   AUC: {roc_auc_score(yte_l, m_leaky.predict_proba(Xte_l)[:,1]):.3f}  ← inflated (test has synthetic samples!)")

# ── ✅ Compare all 4 strategies (all applied on training set only) ────────────
print("\n✅ Correct — all resampling done on TRAINING SET only:\n")
print(f"  {'Strategy':<22} {'Train rows':>10}  {'AUC':>6}  {'Recall(default)':>16}")
print("  " + "-"*58)

strategies = {
    "No resampling":     (X_train, y_train),
    "Undersample":       RandomUnderSampler(random_state=42).fit_resample(X_train, y_train),
    "Oversample":        RandomOverSampler(random_state=42).fit_resample(X_train, y_train),
    "SMOTE":             SMOTE(random_state=42).fit_resample(X_train, y_train),
    "Class weights":     (X_train, y_train),   # no resampling — just model param
}

for name, (Xr, yr) in strategies.items():
    cw = "balanced" if name == "Class weights" else None
    m  = LogisticRegression(max_iter=500, class_weight=cw, random_state=42).fit(Xr, yr)
    proba = m.predict_proba(X_test)[:, 1]
    pred  = (proba >= 0.5).astype(int)
    auc   = roc_auc_score(y_test, proba)
    # recall on defaulters (class 1)
    tp    = ((pred==1) & (y_test==1)).sum()
    fn    = ((pred==0) & (y_test==1)).sum()
    recall = tp / (tp + fn) if (tp+fn) > 0 else 0
    print(f"  {name:<22} {len(yr):>10}  {auc:>6.3f}  {recall:>16.0%}")

print("""
  Recall(default) = of all real defaulters, how many did we catch?
  
  No resampling  → misses most defaulters (low recall)
  Undersample    → fast but loses real data
  Oversample     → just duplicates — model memorises exact rows
  SMOTE          → creates synthetic in-between defaulters ✅ best for tabular
  Class weights  → no data change, safest for temporal/time-series data ✅
""")

# ── KS and Gini (credit scorecard metrics) ───────────────────────────────────
print("── Credit Scorecard Metrics ────────────────────────────────────────")
m_smote = LogisticRegression(max_iter=500, random_state=42)
Xr, yr  = SMOTE(random_state=42).fit_resample(X_train, y_train)
m_smote.fit(Xr, yr)
proba   = m_smote.predict_proba(X_test)[:, 1]
auc     = roc_auc_score(y_test, proba)
gini    = 2 * auc - 1

# KS = max(TPR - FPR) across thresholds
thresholds = np.linspace(0, 1, 100)
ks = max(
    ((proba >= t) & (y_test == 1)).sum() / y_test.sum() -
    ((proba >= t) & (y_test == 0)).sum() / (y_test == 0).sum()
    for t in thresholds
)
print(f"  AUC : {auc:.3f}")
print(f"  Gini: {gini:.3f}  (2×AUC - 1)   → ≥0.50 is good")
print(f"  KS  : {ks:.3f}   (max TPR-FPR)  → ≥0.40 is strong")


"""
KS = 0.20–0.40  → Acceptable model
KS = 0.40–0.60  → Good model  ✅
KS > 0.60       → Strong model
KS < 0.20       → Weak / useless

"""