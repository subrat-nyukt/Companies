# Ecobank Project: Interview Questions & Answers

This document contains potential interview questions based on your resume point: **"Partnered with Ecobank to integrate fintech payment systems across African market and built automated reporting for mobile money transactions & merchant settlements for operations."**

The questions are broken down by technical domains. Use the provided answers as a template and customize them with any specific details from your actual experience.

---

## Part 1: API & System Integration

### Q1: "Can you walk me through the architecture of the payment integration with Ecobank?"
**A:** "We essentially acted as middleware between Ecobank/merchants and various telecom providers (like MTN, Airtel). The architecture relied on an API gateway that received incoming webhooks from the mobile networks whenever a transaction occurred. We captured this JSON payload, performed validation and security signature checks, standardized the data format (since each telecom provider has a different schema), and wrote it into our core transaction database. We also had outward-facing endpoints for merchants to initiate payments or check status."

### Q2: "Webhooks from telecom providers can be unreliable or duplicated. How did you handle failures or double-processing?"
**A:** "To prevent double processing, we implemented **idempotency**. Every transaction came with a unique transaction ID from the provider; we enforced a uniqueness constraint in our database. If an identical webhook arrived, we returned a `200 OK` to the provider but skipped reprocessing. For unreliability, we stored the raw payload immediately into a message queue or logs upon receipt before doing any heavy processing. If our system went down, we could replay those events. We also had a batch polling fallback mechanism in case webhooks didn't arrive."

### Q3: "How did you handle security for these integrations over standard internet connections?"
**A:** "All traffic was enforced over HTTPS (TLS). More importantly, we utilized HMAC (Hash-based Message Authentication Code) signatures. The telecom providers would sign the request body using a shared secret key, and we would verify that signature on our end before parsing the data. We also locked down incoming IP addresses (IP whitelisting) to only accept requests from known mobile money provider IP blocks."

---

## Part 2: Data Engineering & Automated Reporting

### Q4: "You mentioned building automated reporting. What did that pipeline look like?"
**A:** "The goal was to move from raw, unstructured transaction logs to clean business metrics. I built an ETL (Extract, Transform, Load) pipeline. 
*   **Extract:** It scheduled daily pulls of successful transactions from the previous day. 
*   **Transform:** It cleaned the data, applied merchant-specific fee structures to calculate the 'processing fee,' and determined the final 'settlement amount'. We then aggregated this by merchant ID and transaction type.
*   **Load:** The summarized data was exported as automated CSV/Excel reports and delivered directly to the Operations and Finance teams via email or cloud storage."

### Q5: "How did you calculate merchant settlements?"
**A:** "Settlement calculations required joining our raw transaction table with a merchant catalog. Our script took the Gross Transaction Value (e.g., the 500 XOF a customer paid), looked up that specific merchant's contract fee rate (e.g., 2.5%), calculated the fee, and calculated the Net Settlement. We had to ensure accuracy because the output directly determined how much money was wired to the merchants' bank accounts the next morning."

---

## Part 3: Operations & Edge Cases

### Q6: "What happens when a transaction is marked as 'Pending' forever?"
**A:** "This is a common issue with asynchronous mobile networks. We built a reconciliation script. Every hour, our system would query the telecom provider's status API for transactions that had been 'Pending' for more than 15 minutes. If it finally failed, we updated our system; if it succeeded, we moved it to settlement. If we still couldn't resolve it after 24 hours, the automated report flagged it into an 'Exceptions' queue for the Operations team to manually investigate."

### Q7: "How did your reporting system handle refunds or chargebacks?"
**A:** "Refunds are tricky because they affect the settlement. Our data model included a transaction type (e.g., `PAYMENT` vs. `REFUND`). In the reporting aggregation step, refunds were processed as negative values against the merchant's gross volume. We also had to account for refunding the fee portion correctly. If a merchant's daily refunds exceeded their daily sales, the system would flag a negative settlement balance to Operations to hold future payouts."

---

## Part 4: Behavioral & Impact

### Q8: "What was the biggest challenge of standardizing payments across different African markets?"
**A:** "The biggest challenge is fragmentation. You are dealing with multiple currencies (XOF, NGN, KES), different mobile money limits, and completely different API specifications from Vodafone, MTN, and Airtel. Building a unified data model that could gracefully handle all of these provider quirks centrally without writing messy, hard-coded custom logic for every single region was a major architectural hurdle, but it was key for the Operations team to have one clean dashboard."
