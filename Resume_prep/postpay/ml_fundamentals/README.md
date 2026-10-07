# ML Fundamentals — PostPay Interview Prep

**Context:** PostPay trucking BNPL credit risk model | Azure Databricks | XGBoost

---

## Folder Structure

```
ml_fundamentals/
├── 01_data_leakage_temporal_split/
│   ├── interview_questions.md     ← Q&A: PIT logic, temporal splits, Driver D-786 example
│   └── practice_pit_logic.py      ← Hands-on: PIT filtering, temporal split demo
│
├── 02_imbalanced_data_smote/
│   ├── interview_questions.md     ← Q&A: Under/Over/SMOTE + leakage prevention
│   └── practice_imbalanced.py     ← Hands-on: Wrong SMOTE vs correct SMOTE + metrics
│
├── 03_split_strategy_timebound_vs_rolling/
│   ├── interview_questions.md     ← Q&A: Time-bound vs rolling vs group-by-driver
│   └── practice_split_strategies.py ← Hands-on: GroupShuffleSplit vs temporal vs GroupKFold
│
├── 04_future_data_vs_entity_leakage/
│   ├── interview_questions.md     ← Q&A: Two leakage types explained + 5-type taxonomy
│   └── practice_all_leakage_types.py ← Hands-on: All 4 leakage types + clean pipeline
│
└── README.md  ← This file
```

---

## Quick-Reference: The 5 Leakage Types

| # | Type | Cause | Fix |
|---|------|-------|-----|
| 1 | **Temporal** | Future data in features | PIT filter + temporal split |
| 2 | **Entity** | Same driver in train & test | GroupKFold for CV |
| 3 | **Target** | Post-outcome features used | Only use pre-app-date features |
| 4 | **Pipeline** | Scaler/encoder fit on full data | Fit only on training fold |
| 5 | **Aggregation** | Global stats include test rows | Compute stats on train only |

---

## Priority Order (What interviewers want to hear)

```
Temporal Split  →  Rolling PIT  →  GroupKFold (CV)  →  Pipeline Safety
    (Primary)         (Features)      (Hyperparameter)    (Preprocessing)
```

---

## The One-Liner Answers

> **"What is PIT logic?"**
> *"For each loan application, only transactions dated on or before the application date are included in feature computation — nothing from the future."*

> **"Why temporal split and not random?"**
> *"Random split can put December data in training and June data in test. That breaks temporal causality — the model learns from the future."*

> **"SMOTE before or after split?"**
> *"Always AFTER splitting. SMOTE before-split creates synthetic samples from test-set neighbors, inflating validation metrics."*

> **"Time-bound or group-by-driver-id?"**
> *"Temporal split is always primary — it controls for time. Group split is secondary and used only for cross-validation folds within the training period."*

> **"Future data vs same driver-id leakage — what's the difference?"**
> *"Temporal leakage is about when (future data). Entity leakage is about who (the same driver seen in both sets). Both need separate fixes."*

---

## How to Run Practice Scripts

```bash
# Install dependencies
pip install scikit-learn imbalanced-learn pandas numpy xgboost

# Run each practice file
python 01_data_leakage_temporal_split/practice_pit_logic.py
python 02_imbalanced_data_smote/practice_imbalanced.py
python 03_split_strategy_timebound_vs_rolling/practice_split_strategies.py
python 04_future_data_vs_entity_leakage/practice_all_leakage_types.py
```

Run each, read the console output section by section, and match it to the corresponding interview Q&A file.
