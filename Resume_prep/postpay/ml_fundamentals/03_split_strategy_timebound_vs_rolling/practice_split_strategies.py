"""
Practice: Time-Bound vs Rolling Window vs Group-by-Driver-ID
Scenario: 50 drivers, some apply multiple times across 2025
Install: pip install scikit-learn pandas numpy
"""

import numpy as np
import pandas as pd
from datetime import timedelta
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

np.random.seed(42)

# ── Build dataset: 50 drivers, 1–3 applications each ────────────────────────
all_apps, all_txns = [], []
for i in range(1, 51):
    did = f"D-{i:03d}"
    n_apps = np.random.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
    for offset in sorted(np.random.choice(range(0, 360), n_apps, replace=False)):
        all_apps.append({
            "driver_id": did,
            "app_date":  pd.Timestamp("2025-01-01") + timedelta(days=int(offset)),
            "label":     np.random.choice([0, 1], p=[0.80, 0.20])
        })
    for day in range(0, 365, 10):
        all_txns.append({
            "driver_id": did,
            "trans_date": pd.Timestamp("2025-01-01") + timedelta(days=day),
            "amount": np.random.randint(1000, 5000)
        })

apps = pd.DataFrame(all_apps).sort_values("app_date").reset_index(drop=True)
txns = pd.DataFrame(all_txns)
print(f"Applications: {len(apps)} | Drivers: {apps['driver_id'].nunique()} | "
      f"Multi-app drivers: {(apps.groupby('driver_id').size()>1).sum()}")

# ── Rolling PIT: build features with 90-day lookback ────────────────────────
rows = []
for _, app in apps.iterrows():
    pit = txns[
        (txns["driver_id"] == app["driver_id"]) &
        (txns["trans_date"] <= app["app_date"]) &
        (txns["trans_date"] >= app["app_date"] - timedelta(days=90))
    ]
    rows.append({
        "driver_id":    app["driver_id"],
        "app_date":     app["app_date"],
        "label":        app["label"],
        "avg_spend_90d": pit["amount"].mean() if len(pit) > 0 else 0,
        "txn_count_90d": len(pit)
    })
df = pd.DataFrame(rows)

feats  = ["avg_spend_90d", "txn_count_90d"]
X      = df[feats].values
y      = df["label"].values
groups = df["driver_id"].values

# ── ❌ WRONG: Random split — same driver can be in both sets ─────────────────
print("\n❌ Random split (ignores driver identity):")
Xtr, Xte, ytr, yte, gtr, gte = train_test_split(X, y, groups, test_size=0.2, random_state=42)
overlap = set(gtr) & set(gte)
print(f"   Drivers in BOTH train and test: {len(overlap)}  ← entity leakage!")

# ── ✅ Strategy 1: Temporal Split (PRIMARY — always use this) ─────────────────
print("\n✅ Strategy 1 — Temporal Split (recommended):")
train = df[df["app_date"] <= "2025-08-31"]
val   = df[(df["app_date"] > "2025-08-31") & (df["app_date"] <= "2025-10-31")]
oot   = df[df["app_date"] > "2025-10-31"]

cross = set(train["driver_id"]) & set(oot["driver_id"])
print(f"   Train:{len(train)}  Val:{len(val)}  OOT:{len(oot)}")
print(f"   Drivers in both Train+OOT: {len(cross)} → OK! Each has independent PIT features")

sc = StandardScaler()
Xtr_sc = sc.fit_transform(train[feats]);  Xot_sc = sc.transform(oot[feats])
m = LogisticRegression(max_iter=500, class_weight="balanced").fit(Xtr_sc, train["label"])
if oot["label"].nunique() > 1:
    print(f"   OOT AUC: {roc_auc_score(oot['label'], m.predict_proba(Xot_sc)[:,1]):.3f}")

# ── ✅ Strategy 2: GroupShuffleSplit (use ONLY when no time dimension) ─────────
print("\n✅ Strategy 2 — GroupShuffleSplit (no time ordering — use only for static data):")
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
ti, vi = next(gss.split(X, y, groups))
overlap_g = set(groups[ti]) & set(groups[vi])
print(f"   Driver overlap: {len(overlap_g)}  ← 0, clean group split")
print(f"   ⚠️  But: no guarantee test rows are LATER in time than training rows")

# ── ✅ Strategy 3: GroupKFold for CV within training period ───────────────────
print("\n✅ Strategy 3 — GroupKFold CV within training (hyperparameter tuning):")
print(f"   {'Fold':<6} {'Train drivers':>13}  {'Val drivers':>11}  {'Overlap':>7}  {'AUC':>6}")
print("   " + "-"*46)

gkf = GroupKFold(n_splits=3)
Xtr_arr = train[feats].values;  ytr_arr = train["label"].values;  gtr_arr = train["driver_id"].values

for fold, (ti, vi) in enumerate(gkf.split(Xtr_arr, ytr_arr, gtr_arr)):
    ov = set(gtr_arr[ti]) & set(gtr_arr[vi])
    sc_f = StandardScaler()
    Xf_tr = sc_f.fit_transform(Xtr_arr[ti]);  Xf_va = sc_f.transform(Xtr_arr[vi])
    m_f = LogisticRegression(max_iter=500, class_weight="balanced").fit(Xf_tr, ytr_arr[ti])
    fold_auc = roc_auc_score(ytr_arr[vi], m_f.predict_proba(Xf_va)[:,1]) \
               if ytr_arr[vi].nunique() if hasattr(ytr_arr[vi], 'nunique') \
               else len(np.unique(ytr_arr[vi])) > 1 else float('nan')
    print(f"   {fold+1:<6} {len(set(gtr_arr[ti])):>13}  {len(set(gtr_arr[vi])):>11}  {len(ov):>7}  {fold_auc:.3f}")

print("""
Priority order:
  1. Temporal Split  → primary (always)
  2. Rolling 90-day PIT  → for feature construction (always)
  3. GroupKFold  → only for CV folds within training period
""")
