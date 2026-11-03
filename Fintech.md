# Fintech Capabilities & Experience Mapping: MoXey (TruKKer) & Africa Mobile Wallet

Comprehensive mapping of end-to-end fintech capabilities across **11 core solution blocks**, connecting hands-on experience from:
1. **MoXey (TruKKer) – B2B2C Fleet Fintech & Prepaid Cards (UAE & KSA)**
2. **African Mobile Wallet Launch (Ecobank & Telecom Integration)**

---

## Executive Narrative: The Strategic Overview

### 1. MoXey (TruKKer) – B2B2C Fleet Fintech & Prepaid Cards (UAE & KSA)
* **The Product:** A B2B2C digital financial ecosystem for logistics. TruKKer works with enterprise shippers (B2B), but the truck drivers and small fleet owners are individual consumers / micro-enterprises (B2B2C).
* **The Problem:** Drivers suffer from 30–60 day payment cycles, high fuel costs, and lack of banking access.
* **The Solution:** Issued co-branded **Prepaid Cards** and a digital driver **Wallet**. Integrated with fuel/maintenance chains (negotiating 2–4% **Merchant Discounts** while capturing **MDR / Interchange**). Built an **ML prediction model** for trip completion and early freight invoice factoring (**Financing / Working Capital**). Built real-time **Fraud Detection** (cutting card fraud by 20%).

### 2. African Mobile Wallet Launch (Ecobank & Telecom Integration)
* **The Product:** Multi-country mobile money and merchant settlement ecosystem across West & East Africa (partnering with Ecobank and telecom providers like MTN, Airtel, Orange, Vodafone).
* **The Solution:** Built the middleware API gateway, webhook ingestion engine, automated daily merchant settlement pipeline, POS/QR acquiring, and multi-currency accounting (XOF, NGN, KES).

```
                       ┌─────────────────────────┐
                       │   Merchant Solutions    │
                       └────────────┬────────────┘
  ┌───────────────────────┐         │
  │  Processing Solutions ├─────────┤
  └───────────────────────┘         │
  ┌───────────────────────┐         │
  │        Loyalty        ├─────────┤
  └───────────────────────┘         │         ┌─────────────────────────┐
                                    ├─────────┤           POS           │
  ┌───────────────────────┐         │         └─────────────────────────┘
  │        Tokens         ├─────────┤
  └───────────────────────┘         │         ┌─────────────────────────┐
                                    ├─────────┤        Financing        │
  ┌───────────────────────┐         │         └─────────────────────────┘
  │         Cards         ├─────────┤
  └───────────────────────┘         │         ┌─────────────────────────┐
                                    ├─────────┤        Analytics        │
  ┌───────────────────────┐         │         └─────────────────────────┘
  │        Wallets        ├─────────┤
  └───────────────────────┘         │         ┌─────────────────────────┐
                                    ├─────────┤       E-commerce        │
  ┌───────────────────────┐         │         └─────────────────────────┘
  │         Fraud         ├─────────┘
  └───────────────────────┘
```

---

## PART 1: Block-by-Block Experience Mapping

### 1. Merchant Solutions
* **MoXey (TruKKer):** Closed/semi-closed merchant network with national fuel retailers (e.g., ADNOC, ENOC, SASCO) and maintenance/tire merchants. Managed merchant contracts, tiered rebates, and negotiated fuel discounts (2% to 4%).
* **Africa Mobile Wallet:** Onboarded corporate merchants and micro-merchants to accept mobile money. Implemented automated daily payout calculations, contract fee tiering, and invoice/statement reconciliation.
* **Key Terminology:** Merchant Discount Rate (MDR), Net Settlement, Merchant Onboarding, Closed-Loop Merchant Aggregation, SLA Reconciliation.

### 2. Processing Solutions
* **Africa & MoXey:** Built API middleware and webhook processors integrating core banking switches (Ecobank) with telecom mobile money networks (MTN, Airtel). Managed card processor switches for MoXey prepaid cards, handling sub-second balance checks, webhook retries, signature verification (HMAC), and database idempotency to stop duplicate charges.
* **Key Terminology:** Payment Switch, Webhook Architecture, Idempotency Keys, ISO 8583 message specs, HMAC SHA-256 Signatures, Transaction Routing.

### 3. Loyalty
* **MoXey B2B2C:** Built dynamic loyalty and rebate tiers for truck drivers. Using K-Means clustering and RFM analysis on driver transaction history, top-tier drivers unlocked higher merchant fuel discounts (e.g., 4% vs. 1.5%), waived card renewal fees, and priority load dispatch.
* **Key Terminology:** RFM-driven Tiering, Fuel Cash-back Engine, Merchant-funded Rewards, Retention Loops, Gamified Milestones.

### 4. POS (Point of Sale)
* **MoXey:** Terminal-level card swipe tracking at highway service stations. Enforced terminal restrictions using Merchant Category Codes (**MCC 5541 / 5542** for fuel) so fuel cards could not be swiped at unauthorized terminals (e.g., electronics or supermarkets).
* **Africa Mobile Wallet:** Terminal telemetry and cash-in/cash-out (CICO) agent POS network integration, capturing terminal IDs (`TID`) and merchant IDs (`MID`) into Azure Databricks for settlement audits.
* **Key Terminology:** Terminal ID (TID), Merchant ID (MID), MCC Filtering, EMV / Magstripe / Contactless POS, CICO Agent Terminals.

### 5. Tokens
* **MoXey & Africa:** 
  * Implemented network tokenization for MoXey cards so drivers could link cards to mobile wallets (Apple Pay, Google Pay, in-app virtual cards) without exposing raw Primary Account Numbers (PANs), ensuring PCI-DSS Level 1 compliance.
  * In the Africa wallet, tokenized user phone numbers and wallet credentials into single-use session tokens to authenticate merchant checkouts and API calls.
* **Key Terminology:** Network Tokenization, PAN Masking, Vaultless Tokenization, PCI-DSS, One-Time Dynamic Tokens.

### 6. Financing (Working Capital / Micro-Loans)
* **MoXey:** **Early Freight Payout & Fuel Advances**: Small fleet owners usually wait 45–60 days for shippers to pay invoices. MoXey offered instant working capital loaded onto their cards. Built an **ML prediction model (XGBoost)** to predict the probability of trip completion and shipper invoice payment, enabling safe credit underwriting with low default rates.
* **Africa Mobile Wallet:** Transaction-velocity-based merchant advances—extending micro-overdrafts to mobile money merchants based on their 90-day rolling cash flow.
* **Key Terminology:** Freight Factoring, Working Capital Advances, Alternative Credit Scoring, Default Probability Modeling, Float Management.

### 7. Cards (Prepaid & Co-Branded)
* **MoXey:** End-to-end card lifecycle management: issuing co-branded physical and virtual cards. Designed business logic for card top-ups (tied to load delivery milestones), daily ATM withdrawal limits, instant card freezing from the app, and card ledger accounting.
* **Interchange & MDR Economics:** Captured card interchange fees on every swipe while passing a portion back to the fleet as fuel discounts.
* **Key Terminology:** Card Issuing & Lifecycle, Virtual vs. Physical Cards, Interchange Fee Breakdown, Dual-Message Systems, Spend Limit Controls.

### 8. Analytics
* **TruKKer / MoXey / Ecobank:**
  * **Lakehouse Architecture:** Built Star Schema and Delta Lake pipelines in Azure Databricks / Fabric modeling transactions, settlements, and MDR.
  * **Executive BI:** Created 25+ executive Power BI dashboards tracking Gross Payment Volume (GPV), Net Take Rate, Driver Churn, and CAC/LTV.
  * **Automated Settlement Reporting:** Automated daily financial reconciliations across multi-timezone, multi-currency datasets (AED, SAR, XOF, NGN).
* **Key Terminology:** Star Schema, GPV (Gross Payment Volume), Take Rate, Interchange Share, Float Yield, Financial Reconciliation.

### 9. Wallets
* **Africa Mobile Wallet:** Built the data integration and settlement framework for a multi-country mobile wallet enabling Peer-to-Peer (P2P), Cash-In/Cash-Out (CICO), utility bill payments, and cross-border remittances.
* **MoXey Driver Wallet:** Designed a dual-pocket wallet architecture (Pocket A: "Fuel-only balance" restricted to fuel POS; Pocket B: "Cash balance" withdrawable at ATMs).
* **Key Terminology:** Dual-Pocket Ledger, Stored-Value Facility (SVF), P2P Transfers, CICO Agent Cash Flow, Real-time Balance Ingestion.

### 10. E-commerce
* **MoXey:** In-app B2B logistics marketplace where drivers/fleet owners purchased tires, spare parts, engine oil, and insurance at bulk-negotiated prices directly using their card balance or pre-approved working capital.
* **Africa Mobile Wallet:** Hosted checkout and payment gateway plugins (SDK/APIs) allowing online web merchants to accept mobile money wallets, analyzing checkout drop-offs and success rates.
* **Key Terminology:** In-App B2B Marketplace, Payment Gateway SDK, Checkout Conversion Funnel, 3D Secure / 2FA, Drop-off Optimization.

### 11. Fraud
* **MoXey:** Built an ML-based fraud detection system using **XGBoost and Random Forest**, cutting fraud cases by **20%**. 
  * Detected "fuel skimming" (driver swiping a fuel card for non-company vehicles in exchange for cash).
  * Flagged geo-velocity anomalies (card swiped in Riyadh, then swiped in Dammam 40 minutes later).
* **Africa Mobile Wallet:** Detected SIM-swap fraud, sudden velocity spikes on dormant agent accounts, and smurfing (structuring payments under regulatory reporting limits).
* **Key Terminology:** Geo-Velocity Checks, Fuel Skimming Anomaly Detection, Precision/Recall optimization, False Positive Rate (FPR), Rule Engine + ML Ensemble.

---

## PART 2: Comprehensive Interview Q&A by Block

### Block 1: Merchant Solutions
#### Q1: "How did you manage merchant pricing, MDR, and discount agreements at MoXey?"
**A:**  
"At MoXey, we negotiated bulk agreements with major fuel retailers and maintenance networks across UAE and KSA. We structured a two-way revenue model:
1. We negotiated a **2% to 4% merchant discount** on fuel and consumables because we brought aggregate fleet volume.
2. We earned a portion of the **Merchant Discount Rate (MDR)** through our card issuing partner on every terminal swipe.
To pass value back to drivers, we retained a 1% platform fee and credited the remaining 2% back to the driver's wallet as an instant fuel rebate. In our Databricks pipeline, I built automated merchant settlement logic that matched terminal receipts with contracted discount tiers to calculate daily net payouts and rebate accruals."

---

### Block 2: Processing Solutions
#### Q2: "In the African mobile wallet project, how did you guarantee payment reliability and avoid double-charging over unstable telecom networks?"
**A:**  
"When integrating Ecobank with telecom providers like MTN and Airtel, the biggest challenge was intermittent network timeouts and duplicate webhook retries. 
To solve this, I designed an **idempotent processing layer**. Every incoming transaction payload contained a unique provider transaction reference. Our API gateway checked this key against a distributed Redis cache. If the key already existed, we returned an immediate HTTP 200 without executing the debit/credit logic twice. 
For dropped webhooks, we built an hourly reconciliation pipeline that queried the telecom status API for any transaction stuck in 'Pending' for over 15 minutes, automatically reconciling them into 'Success' or 'Reversed' before daily settlement runs."

---

### Block 3: Loyalty
#### Q3: "How did you use data and machine learning to build customer loyalty in a B2B2C logistics product?"
**A:**  
"In MoXey, truck drivers are micro-entrepreneurs driven heavily by operating cash flow. We realized that generic point systems don't drive loyalty; immediate operational cost savings do.
I built a **K-Means clustering and RFM model** that analyzed drivers' monthly trip completion rates, on-time delivery scores, and fuel spend volume. Drivers in the top quartile were upgraded to our 'Gold Tier', which gave them:
1. An extra 1.5% cashback on fuel purchases.
2. Zero ATM withdrawal fees on their prepaid cards.
3. Accelerated working capital approvals.
This data-driven loyalty loop increased driver retention on the platform by **15%** and lowered driver acquisition costs (CAC) by **20%**."

---

### Block 4: POS (Point of Sale)
#### Q4: "How did you prevent drivers from abusing their prepaid cards at unauthorized POS terminals?"
**A:**  
"Fuel theft is the biggest risk in fleet operations. If an employer loads $500 for a trip, a driver might be tempted to swipe at a supermarket or cash out at an ATM.
We implemented strict **MCC (Merchant Category Code) filtering** and terminal ID whitelisting at the authorization switch:
* Fuel cards were locked exclusively to **MCC 5541 (Service Stations)** and **MCC 5542 (Automated Fuel Dispensers)**.
* If a driver swiped at an unauthorized terminal (e.g., MCC 5411 for grocery stores), the switch declined the authorization code in under 100ms.
* Furthermore, we captured the Terminal ID (TID) to verify that the fuel station was physically located along the registered freight route of that driver’s active trip."

---

### Block 5: Tokens
#### Q5: "What was your approach to tokenization and data security for cards and mobile wallets?"
**A:**  
"We operated under strict zero-trust and PCI-DSS compliance guidelines. In the MoXey mobile application, we never stored raw Primary Account Numbers (PANs), CVVs, or card expiration dates in our databases.
Instead, we integrated with our banking partner's **Network Tokenization** API. When a driver provisioned their virtual card, the bank issued a surrogate cryptographic token that mapped to their payment credentials. 
In our African wallet project, we tokenized sensitive API communications between Ecobank and mobile operators using **HMAC SHA-256 signatures** generated via shared rotating secrets. Even if a webhook payload was intercepted over public telco infrastructure, it could not be replayed or altered."

---

### Block 6: Financing
#### Q6: "Walk me through the predictive model you built for early invoice payouts and working capital."
**A:**  
"In logistics, small transporters complete a job today but have to wait 45 to 60 days for enterprise shippers to pay their invoices. MoXey offered **Instant Freight Factoring**—paying the driver 80% of the invoice immediately upon delivery.
The core problem was credit risk: *How do we ensure the shipper won't dispute the invoice, and the driver actually completed the job properly?*
I built an **XGBoost classification and risk model** with three sets of features:
1. **Driver Historical Reliability:** Delivery on-time rate, past trip disputes, platform tenure.
2. **Shipper Payment Track Record:** Average Days Sales Outstanding (DSO), invoice dispute rate, financial health tier.
3. **Trip Telematics Verification:** GPS dwell time at the drop-off destination and digital Proof of Delivery (e-POD) validation.
If the model’s predicted risk score fell below our threshold, the system auto-approved the working capital and loaded the funds directly onto the driver's MoXey card in minutes."

---

### Block 7: Cards
#### Q7: "How did the MoXey prepaid card lifecycle work, and how did the unit economics function?"
**A:**  
"The MoXey card was a co-branded prepaid card issued via a regional partner bank. 
The lifecycle was directly linked to our operational logistics backend:
* **Issuance & KYC:** Transporter onboarding through digital KYC (national ID OCR and facial liveness).
* **Event-Driven Funding:** The card was not funded manually; our Databricks pipeline triggered automated API top-ups when specific ERP trip milestones were reached (e.g., 50% advance upon loading cargo, 50% remainder upon e-POD signoff).
* **Unit Economics:** We monetized through a combination of **interchange fee split** (earning ~1–1.5% on non-fuel merchant spend), platform SaaS subscription fees for fleet management dashboards, and the spread on early invoice factoring."

---

### Block 8: Analytics
#### Q8: "How did you design the analytics and reporting architecture for multi-currency transactions and merchant settlement?"
**A:**  
"In both MoXey and our Ecobank African deployments, our transaction data was fragmented across multiple currencies, countries, and time zones.
I architected a **Lakehouse medallion pattern on Azure Databricks**:
* **Bronze Layer:** Ingested raw webhook JSONs and core banking change-data-capture (CDC) logs.
* **Silver Layer:** Cleaned the data, applied currency conversion tables (converting XOF, NGN, KES, SAR to USD/AED base currencies using daily FX rates), and deduplicated transactions using idempotency keys.
* **Gold Layer:** Modeled the data into a **Star Schema** with Fact Transactions joined against Dim Merchant, Dim Terminal, Dim Driver, and Dim Currency.
On top of this, I built 25+ automated Power BI dashboards that tracked Gross Payment Volume (GPV), Net Take Rate, settlement exceptions, and unpaid reconciliation balances for the Finance team."

---

### Block 9: Wallets
#### Q9: "How did you design the wallet ledger architecture to ensure money was never spent incorrectly?"
**A:**  
"For the MoXey driver app, we implemented a **Dual-Pocket Stored-Value Ledger**:
1. **Pocket A (Restricted Fuel / Trip Funds):** When an employer or shipper disbursed a fuel advance, it was credited to Pocket A. This pocket was locked via middleware logic to only authorize transactions from Fuel MCCs.
2. **Pocket B (Unrestricted Earnings / Profit):** When the final trip settlement occurred, the driver’s net profit margin was credited to Pocket B, which allowed full ATM cash withdrawals, P2P transfers, or personal spend.
For the Africa project, we supported multi-tier wallet balances with regulatory daily transaction limits (e.g., Tier 1 unbanked wallets capped at $200/day vs. Tier 3 fully-KYC verified wallets up to $5,000/day)."

---

### Block 10: E-commerce
#### Q10: "How does e-commerce tie into a B2B2C fleet fintech product?"
**A:**  
"Many people think e-commerce is only consumer retail (like Amazon), but in fleet fintech, it is an **In-App Closed Marketplace**.
Truck owners frequently need replacement tires, engine oil, batteries, and insurance. Individual drivers usually pay retail markups of 20–30% at roadside shops.
We built a B2B marketplace within the MoXey app where vetted parts manufacturers and distributors listed products at wholesale prices. 
The checkout was frictionless: drivers purchased parts directly using their MoXey wallet balance or applied for micro-financing. I analyzed the **checkout conversion funnel** in our analytics stack, optimizing catalog search, checkout drop-off points, and re-order frequency."

---

### Block 11: Fraud
#### Q11: "Explain how you cut fraud by 20% using machine learning at TruKKer/MoXey."
**A:**  
"Fleet card fraud typically falls into two major schemes: **fuel skimming** (drivers swiping their card to fill third-party passenger cars in exchange for cash) and **phantom trips**.
I built a dual-layer fraud detection system:
1. **Real-time Velocity Rules:** Hard thresholds, such as flagging more than two full tank purchases within a 3-hour window or swiping at two stations separated by 300km in under an hour (impossible travel velocity).
2. **Machine Learning Model (XGBoost):** Trained on historical transactional features, including:
   * Ratio of fuel volume purchased vs. truck fuel tank capacity.
   * Deviation of fuel spend from the expected liters-per-kilometer profile for that specific truck payload weight.
   * Time-of-day anomalies (e.g., fuel transactions at 3:00 AM on parked routes).
When a transaction was flagged as high-risk, the system either declined the swipe immediately or sent an automated push notification requiring the driver to upload a photo of the truck's odometer and fuel pump receipt. This system reduced our fraudulent transaction rate by **20%** across UAE and KSA."

---

### The Interview Pitch Summary

"My fintech background bridges both **commercial acquiring and B2B2C issuing**. 
On the issuing and card side, at **MoXey**, I built a prepaid card and wallet ecosystem for hundreds of thousands of fleet drivers, creating an in-app marketplace, an ML model for working capital advances, and an XGBoost fraud detection system. 
On the acquiring, processing, and merchant side, through both MoXey's fuel merchant network and our **African mobile money integration with Ecobank**, I managed merchant discount structures (MDR), POS terminal controls, idempotent processing switches, tokenized transactions, and automated multi-currency lakehouse analytics."
