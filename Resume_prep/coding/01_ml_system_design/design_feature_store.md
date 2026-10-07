# System Design: ML Feature Store

> **Interviewer prompt**: "Design a Feature Store for a company running 
> 5+ ML models across credit risk, fraud, churn, and recommendation domains.
> Multiple teams are duplicating feature logic — fix this."

---

## The Problem Feature Stores Solve

```
Without Feature Store:           With Feature Store:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Credit team: computes RFM        Single RFM definition
Fraud team:  computes RFM (diff) → used by ALL teams
Churn team:  computes RFM (diff) 
= 3 different "truths"           = 1 truth, consistent everywhere

Training features ≠ Serving      Training == Serving features
= Training-serving skew          (point-in-time correctness)
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                            │
│  Transactional DB  │  Event Streams  │  3rd Party (Bureau)   │
└──────────────────────────┬───────────────────────────────────┘
                           │
                    ┌──────▼───────┐
                    │  Ingestion   │  Batch (ADF) + Stream (Kafka)
                    └──────┬───────┘
                           │
          ┌────────────────▼──────────────────┐
          │         FEATURE COMPUTATION        │
          │  Python / Spark transformation     │
          │  e.g., user_avg_loan_30d,          │
          │        cancel_rate_7d,             │
          │        days_since_last_payment     │
          └────────────────┬──────────────────┘
                           │
          ┌────────────────▼──────────────────┐
          │           FEATURE STORE           │
          │                                   │
          │  ┌─────────────────────────────┐  │
          │  │  Offline Store (Historical)  │  │
          │  │  Delta Lake / Parquet        │  │
          │  │  - Training data generation  │  │
          │  │  - Point-in-time joins       │  │
          │  └──────────────┬──────────────┘  │
          │                 │                  │
          │  ┌──────────────▼──────────────┐  │
          │  │  Online Store (Real-time)    │  │
          │  │  Redis / DynamoDB           │  │
          │  │  - Sub-ms feature serving   │  │
          │  │  - Synced from offline store│  │
          │  └─────────────────────────────┘  │
          └────────────────┬──────────────────┘
                           │
          ┌────────────────┴──────────────────┐
          │                                   │
          ▼                                   ▼
   Model Training                      Model Serving
   (offline features                   (online features
    with time-travel)                   from Redis)
```

---

## Key Concepts to Nail in the Interview

### 1. Point-in-Time Correctness (Most Important!)
```python
# WRONG — future leakage: uses features computed AFTER the label date
training_df = features.join(labels, on="user_id")

# CORRECT — only use features available BEFORE the label date
training_df = features.join(
    labels,
    on="user_id",
    how="left"
).filter(
    features["feature_timestamp"] < labels["label_date"]
)
```
> *"At Postpay, this was critical. If I joined RFM features computed in September 
> to loan labels from August, I was using future data — leakage. The feature store 
> enforces that features used for training were available BEFORE the prediction date."*

### 2. Feature Versioning
- Every feature definition is versioned (v1, v2, v3)
- Old models pin to v1; new models use v2
- No breaking changes for live models

### 3. Feature Registry
```python
# Each feature has metadata
{
  "name": "user_cancel_rate_7d",
  "version": "v2",
  "owner": "credit_risk_team",
  "description": "Trip cancellation rate over last 7 days",
  "data_type": "float",
  "freshness_sla": "1 hour",
  "used_by_models": ["credit_risk_v3", "churn_predictor_v1"]
}
```

---

## Tools Comparison

| Tool | Best For | Used At |
|------|---------|---------|
| **Databricks Feature Store** | Azure-native, Spark-based | Postpay / Robustrade |
| **Feast** | Open-source, cloud-agnostic | Startups |
| **Tecton** | Enterprise, real-time | Large FIs |
| **Redis** | Online store / cache layer | Fraud real-time serving |
