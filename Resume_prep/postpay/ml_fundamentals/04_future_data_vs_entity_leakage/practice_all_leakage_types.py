"""
Practice: All 4 Leakage Types — Wrong vs Right
Scenario: PostPay trucking BNPL — 80 drivers, multiple applications
Install: pip install scikit-learn pandas numpy
"""

import numpy as np
import pandas as pd
from datetime import timedelta
from sklearn.model_selection import train_test_split, GroupKFold
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score

np.random.seed(42)

# ── Build base dataset ───────────────────────────────────────────────────────
all_apps, all_txns = [], []
for i in range(80):
    did = f"D-{i:03d}"
    for offset in sorted(np.random.choice(range(0, 360), np.random.choice([1,2,3]), replace=False)):
        all_apps.append({
            "driver_id": did,
            "app_date":  pd.Timestamp("2025-01-01") + timedelta(days=int(offset)),
            "label":     np.random.choice([0,1], p=[0.80, 0.20])
        })
    for day in range(0, 365, 7):
        all_txns.append({
            "driver_id":   did,
            "trans_date":  pd.Timestamp("2025-01-01") + timedelta(days=day),
            "amount":      np.random.randint(1000, 5000),
            "missed_flag": np.random.choice([0,1], p=[0.9, 0.1])
        })

apps = pd.DataFrame(all_apps).sort_values("app_date").reset_index(drop=True)
txns = pd.DataFrame(all_txns)

def pit_features(apps, txns, window=90, include_future_missed=False):
    """Build features. Set include_future_missed=True to simulate target leakage."""
    rows = []
    for _, app in apps.iterrows():
        adate = app["app_date"]
        # PIT: only pre-application transactions
        pit = txns[
            (txns["driver_id"] == app["driver_id"]) &
            (txns["trans_date"] <= adate) &
            (txns["trans_date"] >= adate - timedelta(days=window))
        ]
        # Target leak: use ALL transactions (including post-loan)
        all_d = txns[txns["driver_id"] == app["driver_id"]]

        rows.append({
            "driver_id":      app["driver_id"],
            "app_date":       adate,
            "label":          app["label"],
            "avg_spend":      round(pit["amount"].mean(), 1) if len(pit) > 0 else 0,
            "txn_count":      len(pit),
            # VALID: missed payments BEFORE application
            "pre_missed":     pit["missed_flag"].sum() if len(pit) > 0 else 0,
            # LEAKY: missed payments across ENTIRE loan period
            "total_missed":   all_d["missed_flag"].sum()
        })
    return pd.DataFrame(rows)

df = pit_features(apps, txns)

def temporal_split(df):
    train = df[df["app_date"] <= "2025-08-31"]
    oot   = df[df["app_date"] >  "2025-10-31"]
    return train, oot

# ── LEAKAGE TYPE 1: Temporal — using full txn history (future included) ──────
print("── Type 1: Temporal Leakage ────────────────────────────────────────")

# Leaky: avg_spend computed on ALL transactions per driver (includes future)
leaky_df = apps.copy()
leaky_df["avg_spend"]  = leaky_df["driver_id"].map(txns.groupby("driver_id")["amount"].mean())
leaky_df["txn_count"]  = leaky_df["driver_id"].map(txns.groupby("driver_id").size())

for label, fdf, fcols in [
    ("❌ Leaky (full history)", leaky_df, ["avg_spend","txn_count"]),
    ("✅ Clean (90-day PIT)",   df,       ["avg_spend","txn_count"])
]:
    tr, te = temporal_split(fdf)
    if len(te) == 0 or te["label"].nunique() < 2: continue
    sc = StandardScaler()
    m  = LogisticRegression(max_iter=500, class_weight="balanced")
    m.fit(sc.fit_transform(tr[fcols]), tr["label"])
    auc = roc_auc_score(te["label"], m.predict_proba(sc.transform(te[fcols]))[:,1])
    print(f"   {label}: OOT AUC = {auc:.3f}")

# ── LEAKAGE TYPE 2: Entity — same driver in train and test ───────────────────
print("\n── Type 2: Entity Leakage (same driver in both sets) ───────────────")
X = df[["avg_spend","txn_count"]].values;  y = df["label"].values;  g = df["driver_id"].values

Xtr, Xte, ytr, yte, gtr, gte = train_test_split(X, y, g, test_size=0.2, random_state=42)
print(f"   ❌ Random split  → {len(set(gtr)&set(gte))} drivers in BOTH sets")

train, oot = temporal_split(df)
print(f"   ✅ Temporal split → {len(set(train['driver_id'])&set(oot['driver_id']))} drivers overlap")
print(f"      (multi-app drivers are fine — their features are independently PIT-computed)")

# ── LEAKAGE TYPE 3: Pipeline — scaler fitted on full data ───────────────────
print("\n── Type 3: Pipeline Leakage (scaler fit on full data) ──────────────")
train, oot = temporal_split(df)
fcols = ["avg_spend", "txn_count"]

# WRONG
sc_wrong = StandardScaler().fit(df[fcols])           # sees OOT data!
print(f"   ❌ Scaler mean (full data):  {sc_wrong.mean_.round(1)}")

# RIGHT — sklearn Pipeline handles this automatically
pipe = Pipeline([("sc", StandardScaler()), ("m", LogisticRegression(max_iter=500, class_weight="balanced"))])
pipe.fit(train[fcols], train["label"])               # scaler only sees training data
print(f"   ✅ Pipeline scaler mean (train only): {pipe['sc'].mean_.round(1)}")
if oot["label"].nunique() > 1:
    print(f"   ✅ OOT AUC: {roc_auc_score(oot['label'], pipe.predict_proba(oot[fcols])[:,1]):.3f}")

# ── LEAKAGE TYPE 4: Target — post-outcome features ───────────────────────────
print("\n── Type 4: Target Leakage (post-loan missed payments as feature) ────")
for label, fcols in [
    ("❌ Leaky  (total_missed = post-loan)", ["avg_spend","total_missed"]),
    ("✅ Clean  (pre_missed  = pre-app)",    ["avg_spend","pre_missed"])
]:
    tr, te = temporal_split(df)
    if len(te) == 0 or te["label"].nunique() < 2: continue
    sc = StandardScaler()
    m  = LogisticRegression(max_iter=500, class_weight="balanced")
    m.fit(sc.fit_transform(tr[fcols]), tr["label"])
    auc = roc_auc_score(te["label"], m.predict_proba(sc.transform(te[fcols]))[:,1])
    print(f"   {label}: OOT AUC = {auc:.3f}")
print("   → Higher AUC on leaky version = false, model won't work in production")

# ── Clean final pipeline ─────────────────────────────────────────────────────
print("\n── ✅ Full Clean Pipeline (GroupKFold CV + PIT + Temporal) ──────────")
train, oot = temporal_split(df)
clean_feats = ["avg_spend", "txn_count", "pre_missed"]
pipe2 = Pipeline([("sc", StandardScaler()), ("m", LogisticRegression(max_iter=500, class_weight="balanced"))])

gkf   = GroupKFold(n_splits=3)
Xt    = train[clean_feats].values;  yt = train["label"].values;  gt = train["driver_id"].values
aucs  = []
for ti, vi in gkf.split(Xt, yt, gt):
    pipe2.fit(Xt[ti], yt[ti])
    if len(np.unique(yt[vi])) > 1:
        aucs.append(roc_auc_score(yt[vi], pipe2.predict_proba(Xt[vi])[:,1]))

pipe2.fit(Xt, yt)
print(f"   CV AUC  : {np.mean(aucs):.3f} ± {np.std(aucs):.3f}")
if oot["label"].nunique() > 1:
    print(f"   OOT AUC : {roc_auc_score(oot['label'], pipe2.predict_proba(oot[clean_feats])[:,1]):.3f}")
print("""
   Rules recap:
     1. PIT filter    → trans_date <= app_date (no future)
     2. Temporal split → sort by app_date, cut by calendar date
     3. GroupKFold    → no driver ID shared across CV folds
     4. Pipeline      → scaler.fit() on training only, auto-handled
     5. Pre-app only  → no post-disbursement features
""")
