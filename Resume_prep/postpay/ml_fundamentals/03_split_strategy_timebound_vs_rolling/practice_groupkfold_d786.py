"""
What is GroupKFold? — Simple visual explanation using D-786
===========================================================
D-786 applied for loans TWICE in the training period (March + July).
The question: when we do cross-validation, can D-786's records
end up in BOTH train and val of the same fold?

Regular KFold → YES (bad — driver memorisation)
GroupKFold   → NO  (good — each driver is always on ONE side)
"""

import pandas as pd
from sklearn.model_selection import KFold, GroupKFold

# ── 6 loan applications in training period (Jan–Aug) ────────────────────────
#    D-786 has 2 records.  D-001 to D-004 have 1 record each.

df = pd.DataFrame({
    "row":       [1,       2,       3,       4,       5,       6      ],
    "driver_id": ["D-786", "D-786", "D-001", "D-002", "D-003", "D-004"],
    "month":     ["March", "July",  "Feb",   "Apr",   "May",   "Jun"  ],
    "label":     [1,       0,       0,       1,       0,       1      ],
})

print("Training data (Jan–Aug):")
print(df.to_string(index=False))

print("""
Each row is one loan application.
D-786 appears TWICE (row 1 = March, row 2 = July).
─────────────────────────────────────────────────────
""")

groups = df["driver_id"].values   # tells sklearn which rows belong to same driver

# ════════════════════════════════════════════════════════════════════════
# REGULAR KFold — splits ROWS randomly, ignores driver identity
# ════════════════════════════════════════════════════════════════════════
print("❌ REGULAR KFold (splits rows, ignores who the driver is)")
print("─"*55)

kf = KFold(n_splits=2, shuffle=False)

for fold, (train_idx, val_idx) in enumerate(kf.split(df)):
    train_rows = df.iloc[train_idx][["row","driver_id","month"]].values.tolist()
    val_rows   = df.iloc[val_idx][["row","driver_id","month"]].values.tolist()

    train_drivers = [r[1] for r in train_rows]
    val_drivers   = [r[1] for r in val_rows]
    d786_both     = "D-786" in train_drivers and "D-786" in val_drivers

    print(f"\n  Fold {fold+1}:")
    print(f"    TRAIN → {train_rows}")
    print(f"    VAL   → {val_rows}")
    if d786_both:
        print(f"    ⚠️  D-786 is in BOTH sides!")
        print(f"        Model trains on his March (default) record")
        print(f"        Then validates on his July record")
        print(f"        → Model 'remembers' D-786 — unfair score!")
    else:
        print(f"    D-786 only in one side this fold (happened by chance, not design)")

# ════════════════════════════════════════════════════════════════════════
# GROUPKFOLD — keeps ALL rows of one driver TOGETHER on the same side
# ════════════════════════════════════════════════════════════════════════
print("\n\n✅ GROUPKFOLD (keeps all D-786 rows on same side)")
print("─"*55)
print("Rule: ALL rows of D-786 go to train OR val — never split between them\n")

gkf = GroupKFold(n_splits=2)

for fold, (train_idx, val_idx) in enumerate(gkf.split(df, groups=groups)):
    train_rows = df.iloc[train_idx][["row","driver_id","month"]].values.tolist()
    val_rows   = df.iloc[val_idx][["row","driver_id","month"]].values.tolist()

    train_drivers = set(r[1] for r in train_rows)
    val_drivers   = set(r[1] for r in val_rows)
    overlap       = train_drivers & val_drivers

    print(f"  Fold {fold+1}:")
    print(f"    TRAIN → {train_rows}")
    print(f"    VAL   → {val_rows}")

    if "D-786" in train_drivers and "D-786" not in val_drivers:
        print(f"    D-786: Both his rows are in TRAIN only ✅")
    elif "D-786" in val_drivers and "D-786" not in train_drivers:
        print(f"    D-786: Both his rows are in VAL only ✅")

    print(f"    Overlap (drivers in both sides): {overlap if overlap else '✅ None'}\n")

# ════════════════════════════════════════════════════════════════════════
# SIDE-BY-SIDE SUMMARY
# ════════════════════════════════════════════════════════════════════════
print("""
─────────────────────────────────────────────────────────────
SUMMARY — What's the difference?

  Regular KFold:
    Splits by ROW NUMBER.
    Row 1 (D-786 March) → Train
    Row 2 (D-786 July)  → Val        ← same driver, different sides!
    Model learns D-786 defaulted in March, then is "tested" on July.
    It cheats by recognising D-786.

  GroupKFold:
    Splits by DRIVER ID (the group).
    Row 1 (D-786 March) → Train  ┐
    Row 2 (D-786 July)  → Train  ┘  ← both rows travel together!
    D-786 is NEVER in val when he's in train.
    Model is tested only on drivers it has never seen before.

  Use GroupKFold when:
    - Same driver/customer appears multiple times in your dataset
    - You want hyperparameter tuning that generalises to NEW drivers
    - Not just memorising known drivers
─────────────────────────────────────────────────────────────
""")
