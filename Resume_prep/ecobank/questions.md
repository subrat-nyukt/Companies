# Ecobank Payments Integration & Automated Reporting: Deep-Dive Q&A

This guide covers advanced technical and operational questions based on the automated payment integration and reporting system in the `ecobank` directory. These questions simulate real-world, high-stakes system design and data engineering interviews.

---

## Section 1: System Architecture & API Integration

### Q1: Walk me through the high-level architecture of your payment integration with Ecobank.
**Answer:**
The system acts as a high-throughput, secure middleware layer between Ecobank's regional gateways, local telecommunication providers (MTN Mobile Money, Airtel Money, Orange Money, etc.), and corporate merchants across multiple African markets. 
1. **Ingest & API Gateway:** Telecom providers or Ecobank forward transaction updates via HTTP POST webhooks to our API gateway.
2. **Security & Signature Validation:** Every incoming webhook is authenticated using HMAC-SHA256 signature verification to prevent spoofing.
3. **Queueing (Decoupled Architecture):** Upon validation, raw JSON payloads are parsed and published to a message queue (e.g., Apache Kafka or RabbitMQ) to decouple ingestion from database writes, ensuring zero dropped transactions during traffic spikes.
4. **Data Standardization & Persistence:** Ingestion workers consume messages from the queue, map fragmented provider schemas (e.g., different fields for payment status or carrier reference) to our unified database schema, and write to a PostgreSQL transactional database.

*See implementation reference:*
*   [`02_payment_webhook_simulator.py`](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/ecobank/02_payment_webhook_simulator.py): Demonstrates HMAC signature verification simulation and incoming payload validation.

---

### Q2: Telecom webhooks in Africa can be highly volatile, leading to duplicate deliveries or network dropouts. How did you ensure data integrity and prevent double payouts to merchants?
**Answer:**
We solved this by enforcing **Idempotency** and implementing a **State Reconciliation Loop**.
*   **Idempotency Engine:** We enforced a unique database constraint on the combination of `provider` + `transaction_id`. Before processing any settlement, the API handler queries the idempotency key database. If a webhook with an identical transaction ID arrives (e.g., MTN MoMo retrying due to a late HTTP acknowledgment response), the system returns a `200 OK` (to stop the telecom from retrying) but skips processing the payload to prevent duplicate ledger updates.
*   **Reconciliation Pull-Fallback:** For network dropouts where webhooks are lost, we built a cron-scheduled script that polls telecom provider status APIs every 15 minutes. It fetches all transactions still marked as `PENDING` in our database. It matches the status with the provider's source-of-truth and updates the local state accordingly.

*See implementation reference:*
*   [`02_payment_webhook_simulator.py`](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/ecobank/02_payment_webhook_simulator.py#L25-L48): Checks required fields and logs/updates status safely to avoid double-processing.

---

### Q3: How did you implement security and verify that webhooks actually originated from Ecobank or the telecom provider, and not a malicious actor?
**Answer:**
We secured our endpoints using a three-layer security model:
1. **HMAC Signature Verification:** Each telecom provider was provisioned with a unique, cryptographically secure shared secret. The provider hashed the raw HTTP request body with this secret using SHA-256 and transmitted the hash in the headers (e.g., `X-Signature`). Our backend intercepted the request, hashed the incoming payload using the corresponding merchant secret, and verified that the computed hash matched the header signature.
2. **IP Whitelisting / Firewalls:** We configured our API gateway (such as AWS API Gateway or NGINX) to reject any webhook traffic not originating from the public CIDR blocks whitelisted by Ecobank and telecom partners (MTN, Airtel, etc.).
3. **Transport Layer Security (TLS):** We mandated HTTPS with a minimum TLS version of 1.2 for all webhook endpoints and outgoing payment initiation calls.

---

## Section 2: Automated Reporting & Pandas ETL

### Q4: You automated daily settlement reporting. How does the business logic calculate the payout to the merchant?
**Answer:**
The settlement engine applies contractual transaction fee structures to calculate net payouts:
1. **Filter by Success:** We load raw transactions and filter strictly for `SUCCESS` states (excluding `PENDING` or `FAILED`).
2. **Relational Join:** We perform a relational join between the transaction record and the corporate merchant directory (which acts as a catalog containing fee schedules).
3. **Business Logic Calculation:**
   $$\text{Processing Fee} = \text{Gross Amount} \times \text{Corporate Fee Rate}$$
   $$\text{Net Settlement} = \text{Gross Amount} - \text{Processing Fee}$$
4. **Aggregation:** We aggregate metrics by merchant and output reports containing:
   * Total transaction count
   * Gross transaction volume (Gross amount paid by customers)
   * Total fees collected (Ecobank's revenue)
   * Net settlement payout (Amount wired to the merchant's corporate bank account)

*See implementation reference:*
*   [`03_automated_reporting.py`](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/ecobank/03_automated_reporting.py#L21-L48): Shows the Pandas filtering, joining (`pd.merge`), fee math, and `.groupby().agg()` code.

---

### Q5: Describe the difference between the operational branch view and the corporate finance view in your reporting engine.
**Answer:**
In a retail model, a corporate merchant (e.g., a supermarket chain) operates multiple branches, each possessing several payment terminals (such as point-of-sale registers or QR tables).
*   **Operational Branch Performance Report:** Designed for store managers to assess individual branch performance. It aggregates data by `branch_id`, `branch_name`, and `city` to calculate `total_transactions` and `gross_volume`. It excludes fees and payouts since branch managers only manage sales volume.
*   **Corporate Finance / Settlement Report:** Designed for Ecobank and the merchant's corporate treasury. It aggregates metrics at the `corporate_id` level, tracking the total number of unique active branches, total corporate volume, aggregate fees, and the final net payout sent to the corporate bank account.

*See implementation reference:*
*   [`05_advanced_reporting.py`](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/ecobank/05_advanced_reporting.py#L30-L55): Implements both of these aggregate outputs using separate Pandas aggregations.
*   [`06_add_terminal_data.py`](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/ecobank/06_add_terminal_data.py#L16-L35): Demonstrates how multiple payment terminals (registers/QR codes) roll up to a single branch.

---

## Section 3: Data Warehousing, Star Schema & PySpark (Databricks)

### Q6: Why did you transition from local Python scripts to a Databricks PySpark pipeline for this reporting?
**Answer:**
As we scaled across multiple African markets, the transaction volume grew to millions of payments per day. Pandas processes data in-memory on a single node, which causes out-of-memory (OOM) errors and slow performance at this scale. 
We migrated the pipeline to **Databricks PySpark** because:
1. **Distributed Computing:** Spark divides the processing across a cluster of worker nodes, enabling us to compute settlements on billions of transactions in parallel.
2. **Delta Lake Architecture:** It allowed us to implement a Lakehouse pattern, where raw webhook logs are saved as Silver tables, and clean, aggregated financial models are built as Gold tables.
3. **ACID Transactions:** Delta Lake provides reliability for financial calculations, ensuring that partial failures in a run are automatically rolled back, protecting against corrupt reports.

---

### Q7: Explain the design of your Gold-tier Star Schema in the Databricks pipeline.
**Answer:**
To support fast business intelligence (BI) querying and analytics, we modeled the data into a classic Star Schema:
*   **`fact_transactions` (Fact Table):** Contains transactional measures (`gross_amount`, `processing_fee_amount`, `net_settlement_amount`) and foreign keys referencing dimension tables.
*   **`dim_branch` (Dimension Table):** Contains branch metadata such as `branch_name`, `location` (city), and operational email address.
*   **`dim_merchant` (Dimension Table):** Contains terminal-specific information, including `terminal_id`, `qr_code_id`, `merchant_wallet_number`, `corporate_name`, and the contract `corporate_fee_rate`.
*   **`dim_date` (Dimension Table):** A dedicated date dimension containing pre-calculated columns (`year`, `month_num`, `month_name`, `day_of_week`) to enable rapid time-series analysis and eliminate expensive date-parsing operations during runtime.

*See implementation reference:*
*   [`07_databricks_pyspark_job.py`](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/ecobank/07_databricks_pyspark_job.py#L30-L119): Implements the full extraction of dimensions and the creation of `fact_transactions` using PySpark joins and select mappings.

---

### Q8: What are Surrogate Keys, and why did you use different generation strategies (UUID vs MD5) for your dimensions?
**Answer:**
Surrogate keys are system-generated, integer or string identifiers that serve as the primary key of a dimension table. They decouple the data warehouse from the operational database's natural keys (like `branch_id` or `terminal_id`).
*   **UUID for `dim_branch` (SCD Type 2):** Since a branch can change attributes over time (e.g., moving to a new city), we implemented Slowly Changing Dimension Type 2 (SCD2). Under SCD2, a branch will have multiple historical rows in the dimension table. If we used the natural `branch_id` as the primary key, we would violate uniqueness. Therefore, we generate a random `uuid()` for `branch_sk` every time a row is inserted, allowing multiple versions of the same `branch_id` to coexist.
*   **MD5 for `dim_merchant` (SCD Type 0 / 1):** In this model, payment terminals are fixed physical assets whose attributes are treated as static. Because we don't track historical changes for terminals, we generate a deterministic surrogate key using `md5(col("terminal_id"))`. This is safe because a terminal ID will always map to exactly one surrogate key, saving storage and execution cost compared to generating UUIDs on the fly.

*See implementation reference:*
*   [`07_databricks_pyspark_job.py`](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/ecobank/07_databricks_pyspark_job.py#L35): Generating `branch_sk` with `uuid()`.
*   [`07_databricks_pyspark_job.py`](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/ecobank/07_databricks_pyspark_job.py#L59): Generating `terminal_sk` with `md5()`.

---

## Section 4: Slowly Changing Dimensions (SCD) in Spark

### Q9: How did you implement Slowly Changing Dimensions (SCD) Type 1 and Type 2 in your PySpark job?
**Answer:**
We processed changes by segmenting incoming updates into SCD Type 1 (overwrite) and SCD Type 2 (historical tracking):
*   **SCD Type 1 (Email Updates):** When a branch's email address is modified, we overwrite the email value in-place for the existing active record in the dimension table. Historical tracking is unnecessary here as email updates do not impact past financial aggregates. We achieve this by joining the updates to the active dimension records and applying a conditional write (`when(col("new_email").isNotNull(), col("new_email")).otherwise(col("email_id"))`).
*   **SCD Type 2 (Location Updates):** When a branch moves to a new city, we must retain the old location history for financial reporting (so past sales are correctly attributed to the old city). We execute this in two steps:
    1.  **Expire the Old Record:** We filter the dimension for the existing active row (`is_active = True`), update its `is_active` flag to `False`, and set `valid_to` to the current timestamp.
    2.  **Insert the New Record:** We insert a new row with a new surrogate key (`branch_sk`), `is_active = True`, `valid_from` set to the current timestamp, and `valid_to` set to a far-future date (`9999-12-31`).

*See implementation reference:*
*   [`07_databricks_pyspark_job.py`](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/ecobank/07_databricks_pyspark_job.py#L126-L179): Demonstrates the full SCD1 update and SCD2 union/anti-join logic in PySpark.

---

### Q10: How does your Star Schema guarantee that historic transactions are mapped to the correct version of a branch?
**Answer:**
During the fact table creation, we join the incoming transactions with the **active** version of the branch dimension *at the time of the transaction*. 
1. The transaction is joined with `dim_branch` where `is_active == True`, retrieving the branch's current `branch_sk` (e.g., `SK_1`).
2. When the branch moves the next day, a new record is created in `dim_branch` with `SK_2` (active), and `SK_1` is marked inactive.
3. Because the fact table stores the surrogate key (`branch_sk`) directly inside the transaction record, the transaction from yesterday permanently points to `SK_1`.
4. When finance runs a report grouping by location, yesterday's transaction resolves to `SK_1` (which still contains the old city name), while today's transactions resolve to `SK_2` (which contains the new city name). This ensures historical reporting remains accurate.

*See implementation reference:*
*   [`07_databricks_pyspark_job.py`](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/ecobank/07_databricks_pyspark_job.py#L181-L191): Proves this behavior by printing the final transaction history, showing the transaction retains the old location even after the branch updates.

---

## Section 5: Production Operational Questions

### Q11: What occurs in the automated reporting script if a merchant's daily refunds or chargebacks exceed their daily sales?
**Answer:**
If refunds exceed sales, the net settlement amount for that merchant becomes negative. 
*   **In our Pandas simulation:** The aggregated DataFrame aggregates `net_settlement` as a negative float value.
*   **Operational Solution:** We cannot wire a negative amount to a merchant's bank account. In our production pipeline, the ETL pipeline flags any negative settlement balances and redirects them to an **Exception Queue**. The corporate finance system automatically holds this negative balance and carries it forward to deduct from the merchant's future settlements, while alerting the operations team to review the merchant's account for high-risk activity (e.g., fraud or high refund rates).

---

### Q12: How would you optimize the Databricks Spark pipeline if the transaction volume scaled to hundreds of millions of daily rows?
**Answer:**
We would apply several Spark optimization techniques:
1. **Partitioning by Date:** We would partition our Delta tables by `date_sk` (or transaction date). This prevents Spark from performing full table scans when compiling daily reports, as it can leverage partition pruning to read only the target day's directory in ADLS.
2. **Z-Ordering (Multi-dimensional Clustering):** We would apply Z-Ordering on high-cardinality join columns like `terminal_sk` or `branch_sk` within our daily partitions. This co-locates related data within files, optimizing file-skipping and speeding up dimension-to-fact joins.
3. **Broadcast Joins:** Since dimension tables like `dim_merchant` and `dim_branch` are relatively small (thousands of rows) compared to the fact table (millions of rows), we would explicitly hint Spark to broadcast the dimensions (`broadcast(dim_df)`). This copies the small dimension tables to the memory of all worker nodes, eliminating expensive data shuffling across the network during joins.
4. **Incremental Loading / Structured Streaming:** Instead of full daily batch re-processing, we would utilize Delta Lake's `readStream` to process transactions incrementally as they write to the Silver layer, updating the Gold aggregates near real-time.
