# Churn Definitions & Metrics: 6-Month Timeline Analysis

This document contains interview questions and answers explaining churn definitions, calculation methodologies, and financial implications on a **6-month timeline**. It is customized to fit a **trucking fintech context** (card signups, transaction activity, and CAC/LTV calculations).

---

## Part 1: Churn Definition & Calculation Logic

### Q1: If a user is active in Month 1, inactive in Month 2, and inactive in Month 3, does this user count as "churned" when calculating Month 3's churn rate?
**Answer:**
*   **In standard Month-over-Month (MoM) Churn:** **No.** This user is counted as churned in **Month 2**, not Month 3.
    *   *Why?* The active base (starting pool) for Month 3's calculation consists strictly of users active in Month 2. Since this user was inactive in Month 2, they do not enter the Month 3 calculation. They cannot churn in Month 3 because they were already dead/inactive in Month 2.
*   **In Month 1 Cohort Retention (Month 3 analysis):** **Yes.** When tracking the Month 1 cohort over time, they are counted as part of the **cumulative Month 3 churn** because they were active in the starting cohort (Month 1) but inactive in Month 3.
*   **In a 60-Day Rolling Inactivity Definition:** **Yes.** If churn is defined as *"60 consecutive days of inactivity,"* they cross the threshold at the end of Month 3, making Month 3 the exact point they are flagged as churned.

---

### Q2: How do you mathematically define the difference between Gross Churn and Net Churn?
**Answer:**
*   **Gross User Churn Rate:** Measures only the lost active users without accounting for any reactivation.
    $$\text{Gross Churn Rate}_M = \frac{\text{Active Users in } M-1 \text{ who processed } 0 \text{ txns in } M}{\text{Total Active Users in } M-1}$$
*   **Net User Churn Rate:** Factors in **Resurrected / Reactivated** users (users who were inactive in $M-1$ but transacted again in Month $M$).
    $$\text{Net Churn Rate}_M = \frac{\text{Churned Users}_M - \text{Resurrected Users}_M}{\text{Total Active Users in } M-1}$$
    *Note: Net churn can theoretically be negative if you reactivate more historical users than you lose in a month.*

---

### Q3: How do you define "Active User" in a transactional fintech model compared to a SaaS model?
**Answer:**
*   **SaaS Model:** Activity is contract-based (e.g., active subscription) or login-based (Daily/Monthly Active Users).
*   **Fintech / Card-Processing Model (e.g., Trucking Fleet Cards):** A user is only active if they generate **revenue-producing transaction volume** (GTV). Simply logging into the app is not enough. We define an active user as someone who:
    *   Conducts at least 1 successful card transaction (e.g., fuel purchase at terminal).
    *   Funds their wallet or makes an ATM withdrawal.
    *   Maintains a minimum transaction value threshold (to weed out accidental card swipes).

---

## Part 2: Financial Impact (CAC, LTV, & Payback Period)

### Q4: Why is tracking 90-day retention and churn so critical when optimizing marketing spend using Marketing Mix Modeling (MMM)?
**Answer:**
Acquisition channel performance is deceptive if you only look at first-month signups and CAC. 
1. **High Churn / Cheap Channels:** Some channels (like Facebook or general display ads) may yield a low Cost Per Acquisition (CAC) but suffer from extremely high churn (low 90-day retention). Users sign up for a card but never use it or churn immediately.
2. **Low Churn / Premium Channels:** Other channels (like **Driver Referrals** or **Fuel Promotions**) have a higher initial CAC but demonstrate strong 90-day retention. Because truckers trust word-of-mouth and fuel discounts, they integrate the card into their daily route operations.
3. **The MMM Decision:** Our Scipy Budget Optimizer slashed spend on high-churn channels (Facebook/Billboards down to 5% floor limits) and shifted budget into **Referrals** and **Fuel Promos**. Even if the nominal CAC per channel was slightly higher, the **Quality-Adjusted CAC** (cost per active, non-churned driver) decreased, leading to a **~10% reduction in blended CAC** and a **15% retention uplift**.

---

### Q5: Can you walk through the math of how merchant/driver churn impacts the payback period for CAC?
**Answer:**
Let’s use the actual unit economics of our trucking fintech project:
*   **Optimized Customer Acquisition Cost (CAC):** \$2.50 (or 8–11 local currency units).
*   **Average Transaction Volume per Active User:** \$10,000.
*   **Take-Rate / Revenue Margin on Transaction:** 0.1% (resulting in \$1.00 net revenue per transaction).
*   **Transaction Frequency:** 2 transactions per month (\$2.00 net revenue per month).

#### Payback Calculation:
1. **Transactions needed to recover CAC:** 
   $$\text{Required Transactions} = \frac{\text{CAC}}{\text{Revenue per Transaction}} = \frac{\$2.50}{\$0.10} = 25 \text{ transactions}$$
2. **Payback Period (Months):**
   $$\text{Payback Period} = \frac{\text{Required Transactions}}{\text{Transactions per Month}} = \frac{25}{2} = 12.5 \text{ months}$$

#### The Churn Connection:
*   If a driver churns **within 3 months**, the company only recovers \$6.00 of transaction revenue against a \$2.50 CAC (and factoring in operational overhead, may never reach profitability on that user).
*   This proves why **retention-focused channels (like Referrals)** are mathematically superior: by keeping drivers active past the 12.5-month payback threshold, we unlock high customer lifetime value (LTV).
