# System Design: Real-Time Fraud Detection System

> **Interviewer prompt**: "Design a real-time fraud detection system for a 
> mobile money fintech with 400K+ users and $2M MRR processing transactions 
> across multiple African markets."

---

## 1. Clarify Requirements First

- **Latency SLA**: How fast must a fraud decision be made? → *< 200ms*
- **Throughput**: Transactions per second at peak? → *~500 TPS*
- **Precision vs Recall tradeoff**: Block and investigate, or just flag? → *Flag + auto-block above threshold*
- **Multi-country**: Different fraud patterns per market? → *Yes, Nigeria ≠ Ghana ≠ Kenya*
- **Explainability needed?** → *Yes, for manual review team*

---

## 2. High-Level Architecture

```
User Transaction (Mobile App / USSD)
            │
            ▼
┌─────────────────────────────────┐
│     API Gateway / Load Balancer │
└──────────────┬──────────────────┘
               │ <200ms SLA starts here
               ▼
┌─────────────────────────────────┐
│    Feature Enrichment Service   │  ← Kafka consumer
│  - User velocity (last 1h, 24h) │
│  - Device fingerprint           │
│  - Geo-anomaly flag             │
│  - Historical default signals   │
│    (fetched from Redis ~1ms)    │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│    Fraud Scoring Engine         │
│  Model: LightGBM / XGBoost      │
│  Loaded in-memory (MLflow)      │
│  Output: fraud_score (0.0-1.0)  │
│  SHAP: top 3 reason codes       │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      Decision Engine            │
│  score > 0.85 → AUTO-BLOCK      │
│  score 0.5–0.85 → FLAG + review │
│  score < 0.5  → PASS            │
└──────┬────────────────┬─────────┘
       │                │
       ▼                ▼
  Block TX          Log to Kafka
  Return 403        → Fraud Events Topic
                    → Case Management DB
                    → Analyst Dashboard
```

---

## 3. Feature Engineering for Real-Time

Key: Features must be **pre-computed** and **cached** in Redis for low latency.

| Feature Category | Examples | Computation |
|-----------------|----------|-------------|
| **Velocity** | # of transactions in last 1h, 6h, 24h | Redis counter with TTL |
| **Anomaly** | Amount > 3× user's 30-day avg | Pre-computed in batch |
| **Device** | New device? Country mismatch? | Lookup in Redis |
| **Network** | Shared IP with known fraudsters | Graph lookup |
| **Behavioral** | Time-of-day pattern deviation | Rolling stats in Kafka |

---

## 4. Key Design Decisions

| Decision | Choice | Justification |
|----------|--------|---------------|
| Model | LightGBM | Faster inference than XGBoost; handles 500 TPS easily |
| Feature store | Redis | Sub-millisecond feature retrieval |
| Streaming | Kafka | Decouples transaction processing from scoring |
| Multi-market | Country-specific models | Fraud patterns vary; separate XGBoost per country |
| Threshold | Tiered (0.5 / 0.85) | Balance false positives (bad UX) vs false negatives (fraud loss) |
| Explainability | SHAP top-3 | Analyst can quickly review reason codes |

---

## 5. Monitoring in Production

```python
# Key metrics to track weekly
metrics = {
    "fraud_catch_rate": "TP / (TP + FN)",  # Did we catch the fraudsters?
    "false_positive_rate": "FP / (FP + TN)",  # Are we blocking good users?
    "model_latency_p99": "< 50ms",          # Is inference fast enough?
    "feature_freshness": "Redis TTL < 5min", # Are features stale?
    "psi_amount": "Population Stability Index on transaction amounts",
}
```

**Retraining Trigger**: 
- New fraud pattern detected (rules team alert)
- PSI > 0.2 on any top-5 feature
- Fraud catch rate drops > 5% week-over-week

---

## 6. Your Story (Link to TruKKer Experience)

> *"At TruKKer/MoXey, I built an ML-based fraud detection system using XGBoost 
> and Random Forest, reducing fraud cases by 20% across UAE and KSA markets. 
> The key challenge was that fraud patterns differed between markets, so I trained 
> country-specific models. For real-time decisions, we pre-computed velocity 
> features in batch and stored them in a lookup table, keeping inference under 
> 200ms. We monitored the system using a Power BI dashboard that tracked the 
> fraud catch rate and false positive rate weekly."*
