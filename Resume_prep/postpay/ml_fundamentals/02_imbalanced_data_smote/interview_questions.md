# Interview Q&A: Imbalanced Datasets — Under/Over/SMOTE & Leakage Prevention

---

## Core Concept

> **"In credit risk, defaults are rare (5–20%). A naive model that predicts 'no default' for everyone achieves 90%+ accuracy but is completely useless. We must handle class imbalance — but the technique itself can introduce leakage if applied incorrectly."**

---

## Q1: How do you identify and quantify class imbalance in your dataset?

**Answer:**

```python
default_rate = df['label'].value_counts(normalize=True)
# Output: 0 → 83%, 1 → 17%
```

At PostPay, our trucker loan dataset had roughly **15–20% default rate** — a moderate imbalance, but enough to cause recall collapse on the minority class if unaddressed.

I always check:
1. `value_counts()` for the raw ratio
2. Confusion matrix — is the model predicting all 0s?
3. `classification_report` — check recall on class 1 (defaults)

---

## Q2: Compare undersampling, oversampling, and SMOTE. When do you use each?

**Answer:**

| Technique | What it does | Pros | Cons | Use When |
|-----------|-------------|------|------|----------|
| **Undersampling** (RandomUnderSampler) | Remove majority class rows | Fast, no synthetic data | Loses real information | Very large dataset, ratio is extreme (1:100) |
| **Oversampling** (RandomOverSampler) | Duplicate minority rows | Simple, preserves all data | Overfits to exact minority samples | Small dataset, mild imbalance |
| **SMOTE** | Create synthetic minority samples via interpolation | Adds variety, reduces overfitting vs. raw oversampling | Can create unrealistic samples near boundaries | Medium imbalance (1:5 to 1:20), tabular data |
| **Class Weights** | Penalize misclassifying minority more | No data modification | Less control | When you want to stay pure with original data |

**My go-to at PostPay:**
> *"I used SMOTE on the training set only and combined it with `class_weight='balanced'` in XGBoost as a belt-and-suspenders approach."*

Case 1: Undersampling — "Throw away good data"
What happens:

Before:  820 non-defaulters + 180 defaulters
After:   180 non-defaulters + 180 defaulters  (1:1 ratio)
You deleted 640 real customer records.
Real world when to use it — PostPay has 5 million drivers:

5 million rows:
  4.5M non-defaulters
  500K defaulters   →  ratio 1:9
Training on 5M rows takes 4 hours on Databricks.
Undersample to 500K + 500K = 1M rows → trains in 20 minutes.
AUC barely changes because you still have 500K defaulters to learn from.
When NOT to use it — your 1,000 driver dataset:

You already only have 180 defaulters.
Throw away 640 non-defaulters → model now has only 360 rows total.
Not enough data to learn meaningful patterns → model becomes unstable.
✅ Use when: Dataset is huge (millions) and you need speed
❌ Avoid when: Dataset is small — you can't afford to lose data

Case 2: Oversampling — "Photocopy the rare cases"
What happens:

Before:  820 non-defaulters + 180 defaulters
After:   820 non-defaulters + 820 defaulters
The 180 defaulters got duplicated ~4.5 times each.
Same 180 actual records, just repeated.
Real world example:

Driver D-786 defaulted. His record:
  avg_spend = 1,200  txn_count = 2  loan_amount = 40,000
After oversampling, D-786's exact record appears 5 times.
The model memorizes: "avg_spend=1200, txn=2, loan=40000 → default"
But what about a new driver with avg_spend=1,250? The model might miss him
because it only ever saw exactly 1,200 — no variation was introduced.
Risk in credit:
The model overfits to the exact same 180 drivers rather than learning the general pattern of default.

✅ Use when: Very small dataset (< 500 rows), no other choice
❌ Avoid when: You want the model to generalize — it will memorize, not learn

Case 3: SMOTE — "Create believable new defaulters"
What happens — the smart version of oversampling:

SMOTE looks at your 180 defaulters and creates synthetic new ones by interpolating between real ones:

Real defaulter A:  avg_spend=1,200  txn_count=2  loan=40,000
Real defaulter B:  avg_spend=1,500  txn_count=3  loan=35,000
SMOTE synthetic C: avg_spend=1,350  txn_count=2.5  loan=37,500
                   (midpoint between A and B — realistic but not a copy)
Real world result:

Before SMOTE:  820 non-defaulters + 180 defaulters
After  SMOTE:  820 non-defaulters + 820 synthetic defaulters
Model now sees defaulters with:
  avg_spend ranging 1,000 → 2,000 (not just the exact 180 values)
  → learns the PATTERN, not the individuals
Why better than oversampling:
Instead of photocopying D-786 five times, SMOTE creates new synthetic drivers that look like D-786 but aren't identical — the model generalises better.

✅ Best for: Your PostPay 1,000-driver dataset with 1:5 imbalance
❌ Avoid for: Temporal data (SMOTE ignores time ordering)

Case 4: Class Weights — "Change the penalty, not the data"
What happens — no data is added or removed:

python
model = XGBClassifier(scale_pos_weight=5)
# OR
model = LogisticRegression(class_weight='balanced')
What scale_pos_weight=5 means:

Getting a defaulter wrong costs the model 5× more than
getting a non-defaulter wrong.
Loss for missing a defaulter:  5  (heavy penalty)
Loss for missing a non-defaulter:  1  (normal)
→ Model tries much harder to catch the defaulters
Real world — why this is safest for PostPay's temporal data:

Jan–Aug: train set (ordered by time)
If you apply SMOTE, synthetic rows have no real date.
Where do you insert them? Before Jan? After Aug?
The time ordering breaks.
Class weights: same 800 training rows, same order, same dates.
Just the model's loss function changes. No data touched.
→ Temporal integrity preserved.
Which Is Better? — Decision Guide
Your dataset has...
Millions of rows?
  └─ YES → Undersampling (speed, you have enough defaulters)
  └─ NO  →  ↓
Very few rows (< 500)?
  └─ YES → Oversampling (last resort)
  └─ NO  →  ↓
Is it time-series / temporal data?
  └─ YES → Class Weights (safe, no data modification)
  └─ NO  →  ↓
Medium imbalance (1:5 to 1:20), tabular features?
  └─ YES → SMOTE ✅ (PostPay 1,000-driver case lands here)
PostPay Answer for Interview
"Our trucking loan dataset had ~1,000 applications with an 18% default rate — a 1:5 imbalance. We used SMOTE on the training set only (never on val or OOT) to generate synthetic defaulter profiles. For the temporal OOT evaluation, we switched to scale_pos_weight in XGBoost since SMOTE would break the time ordering. We evaluated using KS statistic and Gini — not accuracy — because with 18% defaults, accuracy is meaningless."


## Q3: ⚠️ How does SMOTE cause data leakage if applied incorrectly?

**Answer — This is the most critical question:**

**The Wrong Way:**
```python
# LEAKY — Apply SMOTE BEFORE splitting
X_resampled, y_resampled = SMOTE().fit_resample(X, y)
X_train, X_test, y_train, y_test = train_test_split(X_resampled, y_resampled)
```

**Why it leaks:**
- SMOTE synthesizes new minority samples by interpolating between **existing minority samples**
- If a test-set default is a "neighbor" used to create a synthetic training point, the model has indirect access to test-set information
- Validation AUC is artificially inflated — you're essentially testing on data derived from your test set

**The Right Way:**
```python
# CLEAN — Split FIRST, then apply SMOTE only on training data
X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y)

# Apply SMOTE ONLY on training data
sm = SMOTE(random_state=42)
X_train_res, y_train_res = sm.fit_resample(X_train, y_train)

# Model trains on resampled training set
# Evaluation happens on original, untouched test set
model.fit(X_train_res, y_train_res)
model.predict(X_test)  # X_test has NO synthetic samples
```

---

## Q4: Should you use stratified split with imbalanced data?

**Answer:**

Yes — always use `stratify=y` in `train_test_split`:

```python
train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
```

Without stratification, a small dataset might have 0 defaults in the test set by random chance, making evaluation meaningless.

**For temporal data**, you cannot use stratification — the split must be chronological. In that case, monitor default rates in each temporal split manually and accept small variance.

---

## Q5: What metrics do you use for imbalanced classification?

**Answer — Never rely on accuracy alone:**

| Metric | Why it matters | Formula |
|--------|---------------|---------|
| **AUC-ROC** | Rank-ordering quality across all thresholds | Area under TPR vs FPR |
| **Precision-Recall AUC** | Better for highly imbalanced; focuses on positive class | Area under Precision vs Recall |
| **F1 Score** | Harmonic mean of precision and recall | 2PR/(P+R) |
| **KS Statistic** | Industry standard in credit scoring | Max(TPR - FPR) across thresholds |
| **Gini** | 2 × AUC - 1; used in credit risk | Same as AUC, different scale |

**PostPay context:**
> *"We optimized for KS statistic and Gini — standard in credit scorecards. We accepted slightly lower precision to maximize recall on defaulters, because missing a default (False Negative) is far more costly than a False Positive."*

---

## Q6: SMOTE variants — when might vanilla SMOTE fail?

**Answer:**

| Variant | Use Case |
|---------|---------|
| **SMOTE** | Standard; good for tabular |
| **BorderlineSMOTE** | Focus on samples near decision boundary — better when minority class is well-clustered |
| **ADASYN** | Adaptive; generates more samples in harder-to-learn regions |
| **SMOTEENN** | SMOTE + Edited Nearest Neighbors (removes noisy majority) — combined cleaning |
| **SMOTETomek** | SMOTE + Tomek Links — removes borderline overlapping samples |

**When vanilla SMOTE fails:**
- Highly overlapping classes → synthetic samples land in majority territory
- Categorical features → must use `SMOTENC` (handles mixed types)
- Time series → SMOTE ignores temporal ordering; use class weights instead

---

## Q7: In a temporal split scenario, how do you handle class imbalance?

**Answer:**

This is a subtle intersection:

1. **Cannot stratify** the temporal split (it would break chronological ordering)
2. Apply SMOTE **only to the training fold** after temporal split
3. Check that OOT test set has a realistic default rate — matches production expectations
4. Use `scale_pos_weight` in XGBoost or `class_weight='balanced'` as a safer alternative (no data modification)

```python
# Safe approach for temporal data
train = df[df['app_date'] <= '2025-08-31']
oot   = df[df['app_date'] >  '2025-10-31']

X_train, y_train = train[features], train['label']
X_oot, y_oot     = oot[features],   oot['label']

# Only apply SMOTE to training — OOT is never touched
sm = SMOTE(random_state=42)
X_train_bal, y_train_bal = sm.fit_resample(X_train, y_train)

model = XGBClassifier(scale_pos_weight=5)  # belt-and-suspenders
model.fit(X_train_bal, y_train_bal)
```

---

## Follow-Up Tricky Questions

**"If SMOTE generates synthetic samples, doesn't that distort the real distribution?"**
→ It does introduce artificial variance. That's why SMOTEENN or SMOTETomek (which clean after oversampling) are sometimes preferred. The key is that in production, the model sees real data — we only use synthetic data to improve learning, not evaluation.

**"Would you use SMOTE in production scoring?"**
→ No. SMOTE is a training-time technique. The production scoring pipeline applies the trained model to real data — no resampling.

**"What if your default rate changes over time (concept drift)?"**
→ This is why the OOT test set is important — if the default rate in OOT is different from training, you examine whether the model's rank-ordering still holds (KS, Gini). If not, schedule model retraining.
