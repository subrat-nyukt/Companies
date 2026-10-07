# Interview Q&A: Data Leakage & Point-in-Time Logic

---

## Core Concept

> **"Data leakage occurs when information from outside the training boundary is used to build the model — making it appear better in development but fail catastrophically in production."**

---

## Q1: What is temporal data leakage in a credit/loan risk model?

**Answer:**

Temporal leakage happens when future data leaks into the training set — the model "sees" information it would never have access to in a real deployment.

In a trucking loan scenario at PostPay:
- A driver applies for a loan on **May 15, 2025**
- If we accidentally include his **June** or **July** transaction history in his feature set for training, the model has "future" information
- In production (going live), June hasn't happened yet at the May decision point
- The model performs brilliantly in testing but **fails live** because those features don't exist yet

**The fix is strict Point-in-Time (PIT) feature construction:**
> *"Only use data that was available AT or BEFORE the loan application date."*

---

## Q2: Walk me through your temporal train/validation/test split strategy.

**Answer (framed as Postpay experience):**

At PostPay, we followed a **temporal chronological split** — never a random shuffle:

| Set | Period | Purpose |
|-----|--------|---------|
| Training | Jan – Aug | Model learns patterns |
| Validation | Sep – Oct | Hyperparameter tuning |
| OOT Test | Nov – Dec | Simulate going live |

**Why not random split?**
- A random split might put December data in training and June in test
- The model learns from "future" patterns and scores artificially high
- OOT (Out-of-Time) test gives a realistic estimate of production decay

**Key line I'd say in interview:**
> *"We sort by `App_Date`, take the first 8 months for training, the next 2 for validation, and the final 2 months as an out-of-time holdout — this mirrors the real deployment lag."*

---

## Q3: What is Point-in-Time (PIT) logic? Give a concrete example.

**Answer:**

PIT logic means: *When building features for a loan application, you filter all source tables to only include records with a date ≤ the application date.*

**Concrete Example — Driver D-786:**

```
App_Date = May 15, 2025
Lookback Window = 90 days → Feb 14 to May 15, 2025
```

| Trans_Date | Amount | Include? |
|------------|--------|----------|
| Jan 10 | 2,000 | ❌ Outside 90-day window |
| Feb 20 | 2,500 | ✅ Within window |
| Mar 15 | 3,000 | ✅ Within window |
| Apr 10 | 2,500 | ✅ Within window |
| May 10 | 2,000 | ✅ Within window |
| **May 15** | — | **APPLICATION DATE** |
| May 20 | 4,000 | ❌ FUTURE — EXCLUDE |
| Jun 05 | 3,500 | ❌ FUTURE — EXCLUDE |

**Feature computed:** `avg_spend_90d = (2500+3000+2500+2000)/4 = 2,500 AED`

This is the only "truth" available to the underwriter on May 15th.

---

## Q4: How do you implement PIT in PySpark / SQL on Azure Databricks?

**Answer:**

```python
# PySpark implementation
features_df = transactions_df.filter(
    (col("Trans_Date") <= col("App_Date")) &          # No future data
    (col("Trans_Date") >= col("App_Date") - expr("INTERVAL 90 DAYS"))  # 90-day window
)
```

In SQL on Databricks:
```sql
SELECT
    driver_id,
    AVG(amount) AS avg_spend_90d,
    COUNT(*) AS txn_count_90d
FROM transactions t
JOIN applications a ON t.driver_id = a.driver_id
WHERE t.trans_date BETWEEN DATE_SUB(a.app_date, 90) AND a.app_date
GROUP BY driver_id
```

**I'd emphasize:** Every feature table must be joined using both `driver_id` AND the date condition — not just `driver_id` alone.

---

## Q5: What happens if you DON'T apply PIT logic?

**Answer:**

1. **Inflated validation AUC** — Model looks great (AUC 0.85) but drops to 0.62 in production
2. **Wrong feature signals** — A driver who defaults in August might have increasing spending in Sep–Nov; those signals leak backward into his May feature set
3. **Business impact** — Loans approved based on a broken model → higher NPL (Non-Performing Loan) rate
4. **Auditing failure** — Regulators require explainability at the decision date; if features used post-date the application, the model isn't compliant

---

## Q6: Why use a 90-day lookback window specifically?

**Answer:**

- **Industry standard** for short-term behavioral signals in BNPL/trucking fintech
- Long enough to capture monthly patterns (3 full cycles)
- Short enough to remain "fresh" and predictive
- Avoids mixing seasonal effects from the prior year
- Could be tuned — some models use 30d / 60d / 180d windows as additional features

---

## Follow-Up Tricky Questions

**"What if a driver has no transactions in the 90-day window?"**
→ Impute with zeros or a "no activity" flag — but flag them separately; cold-start drivers need a different scorecard

**"Can you have leakage even with a temporal split?"**
→ Yes! If you compute global statistics (e.g., `mean_spend_all_drivers`) using the full dataset before splitting, or if target encoding uses the test set labels.

**"What's the difference between leakage and overfitting?"**
→ Leakage is a data problem (wrong information in); overfitting is a model complexity problem (too much memorization of noise).
