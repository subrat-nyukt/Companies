# Interview Q&A: Future Data, Driver ID Isolation & What Leakage Actually Means

---

## The Clarifying Question Being Asked

> **"We don't use future data for predicting past outcomes — OR — we don't use the same driver ID in both training and validation?"**

**Answer: BOTH are true, but they solve DIFFERENT problems.**

---

## Two Distinct Types of Leakage

### Type 1: Temporal Leakage — "Don't use future data for past predictions"

**Definition:** The model training process uses data that would not have been available at the time of the prediction.

**Example:**
- Driver D-786 applies in May
- His June spending (which happens AFTER the application) leaks into his May feature set
- The model learns: "high June spending → likely to default" — but in production, June doesn't exist yet when we score May applicants

**The Fix:** Point-in-Time (PIT) feature filtering + Temporal train/test split

---

### Type 2: Entity Leakage — "Don't use the same driver in training and validation"

**Definition:** The same individual (driver) appears in both the training and test/validation sets, allowing the model to "recognize" and overfit to specific entities.

**Example:**
- Driver D-786 applies in March → training set
- Driver D-786 applies again in September → validation set
- The model has "seen" D-786's behavior in training
- During validation, it gets credit for "recognizing" him even if the underlying relationship hasn't generalized

**The Fix:** GroupKFold using `driver_id` as the group variable

---

## Q1: What exactly happens when the same driver appears in both sets?

**Answer:**

The issue is **identity memorization**, not temporal leakage specifically.

Imagine Driver D-786 has a very unique spending pattern — always pays AED 2,500 exactly, 4 times per month. No other driver does this.

**Without group separation:**
- Training: The model sees D-786's March application (2,500 × 4 pattern) → label = 0 (no default)
- Validation: The model scores D-786's September application → same 2,500 × 4 pattern
- The model correctly predicts 0, **but only because it memorized D-786**, not because it learned a generalizable pattern

**In production:** A new driver with a similar pattern might be scored differently because the model learned "D-786" not "drivers who spend 2,500 exactly 4 times."

---

## Q2: Are these leakage types always both active?

**Answer:**

Not always — depends on the data structure:

| Scenario | Temporal Leakage Risk | Entity Leakage Risk |
|----------|----------------------|---------------------|
| One application per driver, time split | ✅ Prevented by temporal split | ✅ Automatically prevented (driver only in one set) |
| Multiple applications per driver, time split | ✅ Temporal split handles this | ⚠️ Same driver in train + OOT possible |
| No time ordering, random split | ❌ Leakage possible | ⚠️ Same driver in both sets |
| GroupShuffleSplit only | ❌ Temporal not controlled | ✅ Entity controlled |

**PostPay reality:** Drivers take recurring loans → both risks apply. Solution: temporal primary + GroupKFold for CV.

---

## Q3: Practical walkthrough — if Driver D-786 appears in all 12 months

**The complete safe pipeline:**

```
Month:  Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec
D-786:  App1                                    App2            App3
               │                                    │               │
               ▼                                    ▼               ▼
          [Train set]                         [Val set]         [OOT set]
          Features:                           Features:         Features:
          Jan only                            Jun-Sep           Sep-Dec
          (PIT: 90d lookback)                 (PIT: 90d)        (PIT: 90d)
```

**Key insight:** D-786 appears in all three sets — but this is NOT leakage because:
1. His training features (Jan data) cannot "see" his Sep or Dec behavior
2. His Sep features cannot see his Dec behavior
3. The temporal split ensures his **label** in training doesn't influence the model's scoring of his later applications

**The only remaining risk:** If the model overfit specifically to D-786's identity pattern. This is addressed by GroupKFold in CV.

---

## Q4: How do you explain the "no future data" rule simply in an interview?

**Answer (keep it punchy):**

> *"It's the same as forbidding a student from using tomorrow's answer key to study for today's exam. In production, when a loan officer scores Driver D-786 in May, November hasn't happened yet. So we must ensure our training features are built exclusively from data available on or before the application date — that's Point-in-Time logic. Anything after May 15th is 'the future' and gets cut."*

---

## Q5: What about target leakage — is it different from temporal leakage?

**Answer:**

Yes — **target leakage** is when a feature is a *direct proxy* for the target variable (label), making the model trivially correct rather than genuinely predictive.

**Example in credit risk:**
- Feature: "number_of_missed_payments" computed over the *entire loan tenure* (including after disbursement)
- This leaks the outcome — of course someone with 5 missed payments defaulted!
- At prediction time, the loan hasn't been disbursed yet, so there ARE no missed payments to count

**The Fix:**
- Use only PRE-LOAN behavioral features (transactions, on-time delivery rates, fleet age)
- Never include post-disbursement loan performance metrics as features

**Types of leakage summary:**

| Type | Cause | Example |
|------|-------|---------|
| **Temporal** | Future data in training | Post-application transactions used as features |
| **Entity** | Same ID in train & test | Driver D-786 in both splits |
| **Target** | Feature is outcome proxy | "Total missed payments" during the very loan being scored |
| **Pipeline** | Transformation fit on full data | Scaler fit before train/test split |
| **Aggregation** | Global stats include test data | Mean spend across ALL drivers including test set |

---

## Q6: Pipeline leakage — the scaler trap

**Answer:**

This is the most common subtle leakage in ML pipelines:

```python
# WRONG — fits scaler on full data (test min/max leaks into scaler)
scaler = StandardScaler()
X_all_scaled = scaler.fit_transform(X)  # ← uses test data stats!
X_train, X_test = train_test_split(X_all_scaled)

# RIGHT — fit scaler only on training data
X_train, X_test = train_test_split(X)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)   # fit on train only
X_test  = scaler.transform(X_test)        # transform only
```

**In a Scikit-learn Pipeline:**
```python
from sklearn.pipeline import Pipeline

pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('model', LogisticRegression())
])
# Pipeline.fit() automatically fits scaler on training fold only
pipe.fit(X_train, y_train)
pipe.predict(X_test)  # clean — no leakage
```

---

## Interview Decision Tree (Memorize This)

```
Interviewer: "How would you prevent leakage in your PostPay model?"

You:
  ├─ "First, I apply a temporal split — train on Jan–Aug, test on Nov–Dec
  │   to prevent the model from learning from future loan behaviors."
  │
  ├─ "Second, for each application, I build features using a 90-day PIT
  │   window — only transactions before the application date are included."
  │
  ├─ "Third, within the training period, I use GroupKFold with driver_id
  │   so cross-validation folds don't share drivers."
  │
  ├─ "Fourth, I fit all transformers (scalers, encoders) on the training
  │   fold only and transform the validation/test sets separately."
  │
  └─ "Fifth, I audit features for target leakage — any feature that
      directly encodes post-disbursement loan outcomes is excluded."
```

This answer covers all 5 leakage types and shows production-level thinking.
