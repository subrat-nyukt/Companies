# Lead ML Engineer Interview Cheat Sheet

This is your "final layer" of preparation. It summarizes the high-level patterns from the `/coding` repo and links them to your **Postpay** and **Robustrade** experience.

---

## 1. System Design: The PEDALS Checklist
When asked to "Design X", follow this flow:
1.  **P**arameters: What is the scale? (Users, TPS, Latency budget)
2.  **E**nd-to-End: High-level block diagram (Data -> Model -> App)
3.  **D**ata Strategy: Batch vs Streaming? Feature Store? Point-in-time correctness.
4.  **A**lgorithms: Why XGBoost over Deep Learning? (Explainability, tabular performance).
5.  **L**atency & Scaling: Redis for features, Model quantization, Kafka for decoupling.
6.  **S**afety & Monitoring: PSI for drift, Gini decay, SHAP for reason codes.

---

## 2. Core Architectural Patterns

### Real-Time Serving (Fraud/Credit)
-   **Pattern**: Lambda Architecture (Batch for historical features + Streaming for velocity).
-   **Stack**: FastAPI + Redis + MLflow.
-   **Critical Insight**: "We pre-calculate 90% of features (earnings, tenure) in batch, but use Kafka/Redis for the last 10% (last-hour transaction count) to catch bursty fraud."

### Feature Store
-   **Pattern**: Dual-store (Offline for training, Online for serving).
-   **Critical Insight**: "The primary value is **consistency**. By using a single feature definition in Spark, we ensure the model sees the *exact* same numbers in production as it did during training."

---

## 3. Algorithmic Toolbox (ML-Relevant)
| Pattern | Problem Example | ML Use Case |
| :--- | :--- | :--- |
| **Sliding Window** | Rolling average of earnings | Feature Engineering (RFM) |
| **Heap / Top-K** | Top-10 fraud scores | Real-time Alerting / Feature Importance |
| **Graph BFS** | Connected components | Fraud Ring Detection |
| **LRU Cache** | Key-Value Store | Feature Store Serving Layer |
| **Two Heaps** | Streaming Median | Online Drift Monitoring |

---

## 4. Production ML Engineering (The "Lead" Perspective)

### Data Leakage Prevention
-   **Technique**: **Temporal Splitting**.
-   **Explain**: "Never use random `train_test_split` for credit risk. We split by month (e.g., Train: Jan-Aug, OOT: Sept-Oct) to simulate how the model actually originates loans and waits for outcomes."

### Handling Imbalance
-   **Technique**: SMOTE (Oversampling) vs `scale_pos_weight` (Cost-sensitive learning).
-   **Explain**: "At Postpay, I preferred `scale_pos_weight` in XGBoost because it doesn't create synthetic data, it just makes the model pay more attention to the 'Bad' class."

### Model Monitoring (The PSI/Gini Duo)
-   **Technique**: Population Stability Index (PSI).
-   **Explain**: "If the PSI of 'Bureau Score' shifts above 0.2, it means our incoming customers are different from our training data. We investigate before the Gini actually drops."

---

## 5. Behavioral "Lead" Narrative
-   **Mentorship**: "I established code review standards for our Data Science team to ensure feature definitions were reusable across models."
-   **Collaboration**: "I worked with the Platform team to migrate our batch scoring jobs to Databricks, reducing runtime by 40%."
-   **Impact**: "Scaled the risk engine to handle 400K+ drivers, maintaining sub-100ms latency for real-time approvals."

---
**Everything is ready in your `/coding` directory. Good luck!**
