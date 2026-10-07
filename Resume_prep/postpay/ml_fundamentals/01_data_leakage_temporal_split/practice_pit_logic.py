"""
Practice: Point-in-Time (PIT) Logic & Temporal Leakage
Scenario: Driver D-786 applies for a loan on May 15, 2025
"""

import pandas as pd
from datetime import timedelta
from sklearn.model_selection import train_test_split

# ── Raw data: Driver D-786's full year of transactions ──────────────────────
txns = pd.DataFrame({
    "trans_date": pd.to_datetime(["2025-01-10", "2025-02-20", "2025-03-15",
                                   "2025-04-10", "2025-05-10",
                                   "2025-05-20",   # FUTURE (after app date)
                                   "2025-06-05"]), # FUTURE
    "amount":      [2000, 2500, 3000, 2500, 2000, 4000, 3500],
    "description": ["Fuel","Maintenance","Fuel","Fuel","Fuel","New Tires","Fuel"]
})

app_date = pd.Timestamp("2025-05-15")
print("All transactions:\n", txns.to_string(index=False))

# ── WRONG: Use all data — future rows included (leakage!) ───────────────────
print("\n❌ WRONG — avg using all rows:", txns["amount"].mean())
print("   (Includes May 20 tire purchase that hasn't happened yet at app time)")

# ── RIGHT: PIT filter — only data on or before app_date, within 90 days ─────
window_start = app_date - timedelta(days=90)   # Feb 14

pit = txns[
    (txns["trans_date"] <= app_date) &          # no future data
    (txns["trans_date"] >= window_start)         # 90-day lookback
]

print(f"\n✅ RIGHT — 90-day window: {window_start.date()} → {app_date.date()}")
print(pit[["trans_date", "amount", "description"]].to_string(index=False))
print("\nPIT features:")
print(f"  avg_spend_90d  : {pit['amount'].mean():.0f}")
print(f"  txn_count_90d  : {len(pit)}")
print(f"  total_spend_90d: {pit['amount'].sum()}")

# ── Temporal split: train Jan–Aug, val Sep–Oct, OOT Nov–Dec ─────────────────
print("\n── Temporal Split ──────────────────────────────────────────────────")

# Fake dataset with 200 applications spread across 2025
import numpy as np
np.random.seed(42)
n = 200
df = pd.DataFrame({
    "app_date": pd.date_range("2025-01-01", "2025-12-31", periods=n),
    "label":    np.random.choice([0, 1], n, p=[0.8, 0.2])
})

train = df[df["app_date"] <= "2025-08-31"]
val   = df[(df["app_date"] > "2025-08-31") & (df["app_date"] <= "2025-10-31")]
oot   = df[df["app_date"] > "2025-10-31"]

print(f"Training (Jan–Aug) : {len(train)} rows | default rate: {train['label'].mean():.0%}")
print(f"Validation(Sep–Oct): {len(val)}  rows | default rate: {val['label'].mean():.0%}")
print(f"OOT Test (Nov–Dec) : {len(oot)}  rows | default rate: {oot['label'].mean():.0%}")

# ── DANGER: Random split puts future dates in training ───────────────────────
print("\n── Why Random Split is WRONG ───────────────────────────────────────")
r_train, r_test = train_test_split(df, test_size=0.2, random_state=42)
leaked = r_train[r_train["app_date"] > r_test["app_date"].max()]
print(f"Training rows dated AFTER the latest test row: {len(leaked)}")
print("→ Model trains on future data — leakage!")

# ── Key rules ────────────────────────────────────────────────────────────────
print("""
Key Rules:
  1. trans_date <= app_date          (no future data)
  2. trans_date >= app_date - 90d    (90-day lookback window)
  3. Sort by app_date, split by date — NEVER random split
  4. Join on driver_id AND date, not driver_id alone
""")
