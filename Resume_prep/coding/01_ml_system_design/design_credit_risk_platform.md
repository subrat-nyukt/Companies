# System Design: End-to-End Credit Risk Scoring Platform

> **Interviewer prompt**: "Design a credit risk scoring platform for a fintech
> that issues driver loans. 60K drivers, 18K active borrowers, batch + 
> real-time scoring needed."

---

## 1. Clarify Requirements (Ask These)
- Batch nightly score OR real-time at loan origination? → **Both**
- Do we need reason codes (explainability)? → **Yes (regulator)**
- What's the latency SLA for real-time? → **< 500ms**
- Data sources available? → **App events, Bureau, ERP/SAP, Telematics**

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       DATA SOURCES                          │
│  SAP / ERP   │   App Events   │  Bureau API  │  Telematics  │
└──────────────────────────┬──────────────────────────────────┘
                           │ Ingestion (ADF / Kafka)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           BRONZE LAYER — Azure Data Lake (Delta)            │
│         Raw data, schema-on-read, full history              │
└──────────────────────────┬──────────────────────────────────┘
                           │ Databricks ETL
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          SILVER LAYER — Cleaned, Joined, PII-masked         │
│    feature_engineering.py runs here (RFM, rolling stats)    │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   ┌──────────────────┐      ┌──────────────────────┐
   │  TRAINING PATH   │      │    SERVING PATH       │
   │                  │      │                       │
   │ Temporal Split   │      │  Feature Store        │
   │ SMOTE (train)    │      │  (point-in-time safe) │
   │ XGBoost train    │      │         │             │
   │ MLflow log       │      │         ▼             │
   │ Model Registry   │      │  Batch: Spark job     │
   └──────────────────┘      │  Real-time: FastAPI   │
                             │  + Redis feature cache│
                             └──────────────────────┘
                                        │
                                        ▼
                           ┌────────────────────────┐
                           │  GOLD LAYER             │
                           │  credit_scores table    │
                           │  reason_codes table     │
                           └────────────────────────┘
                                        │
                          ┌─────────────┴──────────────┐
                          ▼                             ▼
                    Power BI Dash             Loan Origination API
                    (Risk team)               (Approve / Decline)
```

---

## 3. Key Design Decisions & Why

| Decision | Choice | Reason |
|----------|--------|--------|
| Model | XGBoost | Handles imbalance, missing values, gives SHAP explainability |
| Imbalance | SMOTE + scale_pos_weight | Belt-and-suspenders; SMOTE only on train set |
| Split | Temporal (not random) | Prevents future-data leakage; mirrors production |
| Feature store | Databricks + Delta | Point-in-time correctness; avoids leakage at serving |
| Explainability | SHAP values | Required for regulatory reason codes |
| Monitoring | PSI weekly | Detects input drift before Gini decays |
| Serving | Batch + Real-time API | Batch for daily portfolio scoring; RT for loan approval |

---

## 4. Monitoring & Retraining Strategy

```python
# PSI Monitoring (runs weekly)
def compute_psi(expected, actual, buckets=10):
    """Population Stability Index — detects input drift"""
    breakpoints = np.percentile(expected, np.linspace(0, 100, buckets+1))
    expected_pcts = np.histogram(expected, bins=breakpoints)[0] / len(expected)
    actual_pcts   = np.histogram(actual,   bins=breakpoints)[0] / len(actual)
    # Avoid division by zero
    expected_pcts = np.where(expected_pcts == 0, 0.0001, expected_pcts)
    actual_pcts   = np.where(actual_pcts   == 0, 0.0001, actual_pcts)
    psi = np.sum((actual_pcts - expected_pcts) * np.log(actual_pcts / expected_pcts))
    return psi

# Thresholds:
# PSI < 0.1  → Stable (no action)
# PSI 0.1-0.2 → Monitor more closely
# PSI > 0.2  → RETRAIN triggered
```

---

## 5. What You Say in the Interview

> *"At Postpay, I built exactly this — a PD model for 60K drivers using 111 features
> across 8 domains. We used XGBoost trained on a temporal split (Jan–Aug train, 
> Sep–Oct OOT test), scored weekly via a Databricks batch job writing to a Gold table.
> For real-time loan origination, we exposed a FastAPI endpoint that fetched 
> pre-computed features from a Delta table and returned a score + SHAP reason codes 
> in under 200ms. We monitored PSI weekly and had a Champion-Challenger process 
> before any model upgrade."*
