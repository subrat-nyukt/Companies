# Credit Risk & Fraud Detection Project Plan

## Objective
Build a Machine Learning model to predict whether a returning customer will default on their next Buy Now Pay Later (BNPL) installment plan.

## Curriculum
This project is divided into 5 practical steps. We will execute them one by one.

### Phase 1: Data Engineering (SQL)
**Goal**: Transform raw transaction logs into a "Customer Feature Store".
1.  **Data Understanding**: Analyze `instalment_plans`, `orders`, and `customers` tables.
2.  **Feature Engineering**: 
    *   **Velocity Features**: Count of orders in last 30d, 90d, etc.
    *   **Ratio Features**: Debt-to-Order value.
    *   **Identity Features**: Device usage (Apple vs Android), Card types.
3.  **Target Definition**: Define what a "Default" is (e.g., `status='paid'` vs `status='incinerated'`).

### Phase 2: Exploratory Data Analysis (Python/Pandas)
**Goal**: Find patterns and correlations.
1.  **Distribution Analysis**: Are defaulters rare? (Class Imbalance).
2.  **Correlation Matrix**: Do people with 'Android' devices default more?
3.  **Missing Values**: How to handle nulls in `days_to_expiry`.

### Phase 3: Model Development (Scikit-Learn)
**Goal**: Train a predictive model.
1.  **Preprocessing**: Scaling numerical values, One-Hot Encoding categorical ones.
2.  **Algorithm Selection**: Logistic Regression vs. XGBoost/LightGBM.
3.  **Training**: Splitting Train/Test sets to avoid leakage.

### Phase 4: Evaluation & Interpretation
**Goal**: Prove the model works.
1.  **Metrics**: ROC-AUC, Precision-Recall (Accuracy is misleading in fraud!).
2.  **Feature Importance**: specific features that drive risk (e.g., "3 missed payments in last month").
3.  **SHAP Values**: Explaining individual predictions.

### Phase 5: Production & Monitoring
**Goal**: Deploy the model.
1.  **Inference Pipeline**: How to score a new customer in real-time.
2.  **Monitoring**: Checking if the model degrades over time (Drift).

---
**Current Status**: Starting Phase 1.
