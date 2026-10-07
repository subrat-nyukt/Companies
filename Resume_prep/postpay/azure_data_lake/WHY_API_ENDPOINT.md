# Why Two Deployment Methods? (Batch vs. API)

You learned TWO different ways to use a model. They serve different purposes.

## 1. Batch Job (The "Nightly" Method)
*   **What you did**: Created `BATCH_SCORING.py`.
*   **How it works**: Every night at 3 AM, it wakes up, downloads the model, runs it on 10 million customers, and saves the results to a table.
*   **Why**: To update risk scores for **Existing Customers**.
    *   *Example*: User A was fine yesterday. Today `unpaid_count` went up. Tomorrow morning, his score in the table will change to "High Risk".

## 2. API Endpoint (The "Real-Time" Method)
*   **What you did**: Clicked "Create Serving Endpoint" in the UI.
*   **How it works**: It keeps the model running on a server 24/7. It waits for a specific request.
*   **Why**: For **NEW Customers** (who are not in the database yet!).
    *   *Scenario*: Ideally, a brand new user comes to your website. They sign up and click "Buy".
    *   *Problem*: They are NOT in your nightly batch job yet! You don't know who they are.
    *   *Solution*: Your website sends their data (Device Type, Order Amount) to the **API Endpoint**.
    *   *Result*: The API replies instantly: "Reject" or "Approve".

## Summary
*   **Batch Job**: For old friends (Existing Users).
*   **API Endpoint**: For strangers (New Users).
