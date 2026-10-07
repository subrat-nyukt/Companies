# ML System Design — Universal Framework

> Use this 6-step framework for ANY design question in your interview.
> Tailor the example to your Postpay / Robustrade / TruKKer experience.

---

## The PEDALS Framework

| Step | What You Do | Time |
|------|------------|------|
| **P** — Problem Scoping | Clarify the goal, constraints, scale | 2 min |
| **E** — Estimation | Data volume, QPS, latency requirements | 2 min |
| **D** — Data Pipeline | Ingestion → Feature Store → Training data | 5 min |
| **A** — Algorithm / Model | Model choice + justification | 4 min |
| **L** — Live Serving | Batch vs. real-time, APIs, latency | 4 min |
| **S** — Scaling & Monitoring | Drift, retraining, CI/CD, rollback | 3 min |

---

## Template Answer for Any Design Question

### Step 1 — Clarify
*"Before I design, let me ask a few questions:*
- *Is this batch (e.g., daily scoring) or real-time (e.g., sub-100ms fraud decisions)?*
- *How many predictions per day / second?*
- *Is interpretability required (regulator / explainability needs)?*
- *What's the cost of a false positive vs. false negative?*"

### Step 2 — Estimate
- Data scale: e.g., 60K drivers × 111 features × 1 year = ~26M rows
- QPS: 10 predictions/sec real-time OR 50K/night batch
- Latency: <100ms (real-time) / <6 hours (batch)
- Storage: Features in Parquet on Azure Data Lake

### Step 3 — Data Pipeline
```
Raw Sources (ERP, App Events, Bureau)
        ↓
Bronze Layer (Raw ingestion — Databricks Delta Lake)
        ↓
Silver Layer (Cleaned, joined, PII masked)
        ↓
Feature Store (Point-in-Time correct features — Feast / Databricks Feature Store)
        ↓
Gold Layer (Model-ready training / serving datasets)
```
**Key call-out**: Always mention **Point-in-Time correctness** to avoid leakage.

### Step 4 — Model Choice
- **Credit Risk (structured, tabular)**: XGBoost → best AUC, handles missing values
- **Real-time Fraud**: GBM with threshold tuning; consider LightGBM for speed
- **Recommendations**: Matrix Factorization or Two-Tower DNN
- **NLP/GenAI**: Fine-tuned LLM (LoRA/PEFT) + RAG for grounded responses

Justify always: *"I choose XGBoost because it handles class imbalance via `scale_pos_weight`, natively handles missing values, and gives us SHAP-based explainability for the regulator."*

### Step 5 — Serving
```
Option A: Batch Scoring
  Spark job → Predict → Write to Gold table → BI / API layer
  Use when: Daily credit decisions, weekly retention scores

Option B: Real-time API
  FastAPI / Flask → Model loaded from MLflow Registry → Redis cache for features
  Use when: Fraud detection, loan approval at point-of-origination
```

### Step 6 — Monitoring & Retraining
- **PSI (Population Stability Index)**: Detect input drift. Threshold: PSI > 0.2 → retrain
- **Gini / KS decay**: If Gini drops >10% from baseline → alert
- **Champion-Challenger**: Shadow-mode for 2 weeks before promotion
- **CI/CD for ML**: GitHub Actions → test → retrain → register → deploy (MLflow + Docker)
- **Rollback**: Always keep last 2 model versions in registry

---

## Common Design Questions for This Role

1. **"Design a real-time fraud detection system for a fintech with 400K users."**
2. **"Design an end-to-end credit risk scoring platform."**
3. **"Design a feature store for an ML platform."**
4. **"How would you detect and handle model drift in production?"**
5. **"Design a recommendation system for a lending product."**
