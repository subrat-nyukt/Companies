# Interview Q&A: Time-Bound vs Rolling Window vs Group-by-Driver-ID

---

## The Core Question

> **"When splitting data to prevent leakage, which boundary should take priority — time, a fixed lookback window, or the driver's identity?"**

This is an architectural decision question. The answer is nuanced and depends on what *type* of leakage you're trying to prevent.

---

## Understanding the Three Approaches

### 1. Time-Bound Split (Temporal Cutoff)
Split the dataset at a fixed calendar date. All records before date D go to training; all after go to test.

```
|──── Training ────|── Val ──|── OOT ──|
Jan ──────────── Aug   Sep–Oct   Nov–Dec
```

**What leakage it prevents:**
- The model cannot use November data to predict June outcomes
- Mirrors real deployment: you train on historical data, predict on future applicants

**Weakness:**
- If Driver D-786 appears in **both** training (Jan application) AND test (Nov application), his early defaulting behavior could influence how the model learns about him — but he now appears in the validation set too

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

---

### 2. Rolling Window (90-day Lookback)
At each application date, only use the prior 90 days of that driver's transactions.

```
App_Date = May 15 → use [Feb 14 – May 15] only
App_Date = Nov 10 → use [Aug 12 – Nov 10] only
```

**What leakage it prevents:**
- Prevents "full history" contamination — you only see what a lender would have seen at decision time
- Ensures features are computed at the exact Point-in-Time

**Weakness:**
- Does NOT prevent the same driver from appearing in training AND test
- A driver who applies multiple times has correlated records across splits

---

### 3. Group-by-Driver-ID (Group Split)
Ensure that each driver appears in **only one** of train/validation/test — never across multiple sets.

```python
from sklearn.model_selection import GroupShuffleSplit
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(X, y, groups=df['driver_id']))
```

**What leakage it prevents:**
- The model doesn't "memorize" Driver D-786's patterns from training and then predict D-786 in the test set
- Essential when features contain strong individual identity signals

**Weakness:**
- If applied without time ordering, a driver could have a January test record and an August training record (reverse-temporal leakage!)

---

## Q1: Which takes priority — time-bound or group-by-driver-ID?

**Answer:**

**Time-bound ALWAYS takes priority.** Here's why:

1. **Real-world deployment is temporal** — In production, you train on historical applications and score new ones going forward. Time is the primary axis.

2. **Group split without time ordering can STILL leak future data** — If we randomly assign Driver D-786 to test, his March application might be in test while his November behavior (same driver) somehow leaks pattern signals during training.

3. **The industry standard for credit risk models** is:
   - **Primary boundary**: Temporal cutoff (train ≤ Aug, OOT > Oct)
   - **Secondary boundary**: Rolling window for feature construction (90-day PIT)
   - **Optional third layer**: If the business case involves multi-loan drivers, use `GroupKFold` within the training period for cross-validation

---

## Q2: When WOULD you use group-by-driver-ID as the primary split?

**Answer:**

Use group split when:
1. **Drivers appear many times** — If a driver makes 12 loan applications in a year, his record in December could be highly correlated with his January record. Training on July and testing on August for the same driver inflates metrics.
2. **No strong temporal signal** — If the data isn't time-ordered (unlikely in fintech, but possible in survey data)
3. **Cross-validation within training period** — Use `GroupKFold` for hyperparameter tuning so the same driver doesn't leak across CV folds

```python
from sklearn.model_selection import GroupKFold
gkf = GroupKFold(n_splits=5)
for train_idx, val_idx in gkf.split(X_train, y_train, groups=train_df['driver_id']):
    # Each fold has unique drivers in train vs val
    ...
```

---

## Q3: If a driver appears in ALL months, how do you handle them?

**Answer:**

This is a key scenario in trucking fintech where drivers take recurring loans.

**The correct approach — Stack Temporal + Group:**

```
Step 1: Temporal Split
─────────────────────────────────────────────────────────────
             Jan–Aug (Train)  |  Sep–Oct (Val)  | Nov–Dec (OOT)
Driver D-786: App1 (Mar)        App2 (Sep)        App3 (Dec)
─────────────────────────────────────────────────────────────

Step 2: Feature construction for each application uses PIT
   App1 (Mar): features from Jan–Mar
   App2 (Sep): features from Jun–Sep
   App3 (Dec): features from Sep–Dec

Step 3: For cross-validation WITHIN training, use GroupKFold
   (so App1 and any other D-786 training rows don't appear in the same fold)
```

**The dangerous pattern to avoid:**
- App1 (Mar) → Training
- App3 (Dec) → OOT Test
- Feature for App3 includes Sept-Dec data → Already covered by PIT
- But: Did Dec behavior influence how the model learned about D-786 in March? ✅ No — temporal split prevents this

The model never sees D-786's December in training; it only sees March. The March features are computed using only Jan-Mar data. This is **clean**.

---

## Q4: Rolling window vs full history — which is better for features?

**Answer:**

| Feature Type | Window | Rationale |
|-------------|--------|-----------|
| Spending pattern | 90 days | Recent behavior is most predictive |
| Transaction frequency | 60 days | Short-term activity signals |
| Long-term average | 12 months | Baseline behavior, less sensitive to outliers |
| Seasonality flag | Year-over-Year | Is this spend spike normal for this month? |

**Best practice:** Create features at multiple windows. The model learns which horizon matters most.

```python
for window in [30, 60, 90, 180]:
    pit_window = txns[(txns['trans_date'] >= app_date - timedelta(days=window)) &
                      (txns['trans_date'] <= app_date)]
    features[f'avg_spend_{window}d'] = pit_window['amount'].mean()
```

---

## Decision Framework (Summary)

```
Should I use Time Split, Rolling Window, or Group Split?
                        │
                        ▼
Is the data time-ordered (applications over months)?
         YES → PRIMARY SPLIT: Temporal cutoff
                        │
                        ▼
Do I also build features per application?
         YES → SECONDARY: 90-day Rolling PIT window
                        │
                        ▼
Does the same driver appear multiple times in training period?
         YES → TERTIARY: GroupKFold for cross-validation only
                        │
                        ▼
Final: Temporal > Rolling Window > Group (priority order)
```

---

## Tricky Follow-Up Questions

**"Can the rolling window itself cause leakage?"**
→ Yes, if you include driver-level statistics computed over the full dataset (e.g., "this driver's all-time average spend"). This is **global aggregation leakage** — the full history is used, including future loans.

**"What if you have a cold-start driver with only 10 days of history?"**
→ The 90-day window returns sparse data. You flag them as `new_driver=1` and either use a separate scorecard or fallback to fleet/segment-level priors. Never extrapolate from limited data.

**"Is sequential train-test split the same as time-bound split?"**
→ Yes, but "sequential" is vague. Always specify: *"We sort by App_Date and use a calendar cutoff — August 31 for training, October 31 for validation."*
