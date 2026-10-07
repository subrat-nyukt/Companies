# Joining Datasets & Feature Engineering

## 1. Is it okay to join multiple datasets?
**YES, absolutely!** In fact, it is **mandatory** for Credit Risk modeling.

Raw data is usually stored in separate tables for efficiency (Normalization):
*   **Customers Table**: Who they are (Name, ID).
*   **Orders Table**: What they bought (Date, Amount, Device).
*   **Installments Table**: How they paid (Paid, Unpaid, Due).

**The Problem**:
If you only look at the **Orders Table**, you see "User A bought $500 worth of goods."
If you only look at the **Installments Table**, you see "Order #123 was never paid."

**The Solution (The Join)**:
By joining them, you get the full story: "**User A** (from Customers) bought **$500** (from Orders) and **did not pay** (from Installments)."
*   Now you know User A is a risk.
*   This joined view is often called a **Customer 360** or **ABT (Analytical Base Table)**.

---

## 2. How to do Feature Engineering?
Feature Engineering is the art of translating **Raw Data** into **Risk Signals**.

### The 4 Major Techniques:

#### A. Aggregations (Summarizing History)
Instead of listing every transaction, summarize them.
*   **Count**: `COUNT(orders)` -> "Total Orders" (Frequency)
*   **Sum**: `SUM(case when status='unpaid'...)` -> "Total Defaults" (Severity)
*   **Average**: `AVG(amount)` -> "Average Spend" (Value)
*   *In your SQL*: This is exactly what `No_of_instalment_plan_1m` does.

#### B. Ratios (Relative Health)
Absolute numbers can be misleading. Ratios give context.
*   **Debt-to-Value**: `Sum(Unpaid Amount) / Sum(Total Amount)`
    *   *User A*: Unpaid $100, Total Spend $10,000 -> Ratio 0.01 (Low Risk)
    *   *User B*: Unpaid $100, Total Spend $100 -> Ratio 1.0 (High Risk!)
*   *In your SQL*: `Debt_to_order_1m`

#### C. Time-Based Features (Recency)
Fraudsters often act quickly.
*   **Days Since Last Order**: `Current Date - Max(Order Date)`
*   **Velocity**: "Number of orders in last 10 minutes" (High velocity = Bot/Fraud)
*   *In your SQL*: `days_to_expiry_lst_used_card`

#### D. Categorical Information (Identity)
Turning text into numbers.
*   **Device Type**: iPhone users might default less than Unknown Browser users.
*   **Email Domain**: `@corporate.com` might be safer than `@temp-mail.com`.

---

### Summary
You are not just "joining tables." You are **building a dossier** on every customer. The more datasets you join (Bureau Data, Device Fingerprint, Social Data), the more accurate your model becomes.
