# Postpay_Risk_Engine vs. daily_risk_scores

Think of it like **The Brain vs. The Exam Results**.

## 1. Postpay_Risk_Engine (The Brain)
*   **What is it?**: A file containing **Calculations (Code)**.
*   **Where is it?**: In the **Model Registry** (`models:/...`).
*   **Content**: A huge set of "IF/THEN" rules (learned by ML).
    *   *Rule*: `IF (unpaid > 0) AND (debt_ratio > 0.5) THEN Risk = 1`.
*   **Does it change?**: Only when you re-train it (maybe once a month).
*   **Size**: Tiny (~100MB).

## 2. daily_risk_scores (The Exam Results)
*   **What is it?**: A file containing **Data (Rows)**.
*   **Where is it?**: In the **Data Lake** (Table).
*   **Content**: The **Answers** for every single customer.
    *   `Customer_1 -> Risk: 0`
    *   `Customer_2 -> Risk: 1`
    *   `Customer_3 -> Risk: 0`
*   **Does it change?**: Every single night (new scores).
*   **Size**: Huge (100GB - 1TB).

## Summary
*   **Risk Engine** = The Logic ("How to calculate risk").
*   **Daily Scores** = The Output ("Who is risky today").
