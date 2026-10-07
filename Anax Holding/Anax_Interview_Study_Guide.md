# Anax Capital - AI & Data Engineering Interview Study Guide

This document captures all the architectural workflows, troubleshooting tips, and scripts we built today.

## Module 1: Databricks KPI Pipeline & Synapse Integration
**Goal:** Build a Medallion Architecture to calculate daily conversion metrics, save to a data lake, and serve via Power BI.

* **The Pipeline Flow:** 
  1. Databricks PySpark reads raw CSVs from Azure Data Lake Storage (ADLS Gen2).
  2. Data is cleansed and KPIs (e.g., Lead-to-Deposit Conversion) are calculated.
  3. Databricks writes the clean output as **Delta files** into a "Gold" folder.
* **The Serving Bridge:** Azure Synapse Serverless SQL creates a "Live View" (`OPENROWSET`) stretching over those Delta files. Synapse acts purely as a compute bridge without physically duplicating the data.
* **Power BI Trouble Shooting:** If Power BI hits `[Cannot find CREDENTIAL]` errors when connecting to Synapse via SQL Authentication, it is typically because Synapse wasn't given an explicit `DATABASE SCOPED CREDENTIAL` to talk to the Data Lake on behalf of the SQL user. (Alternatively, just use Microsoft Entra ID authentication).

## Module 2: Data Governance & End-Of-Day (EOD) Reconciliation 
**Goal:** Mathematically verify that the internal CRM Ledger perfectly matches the external MT5 Trading servers.

* **The Outer Join Strategy:** To do reconciliation, you MUST use a Full Outer Join (`pd.merge(how="outer")`). If you use an inner join, you will completely miss "Ghost Wallets" (missing in CRM) or "Unmapped Deposits" (missing in MT5). 
* **Anomaly Flagging:** The script builds logic to detect `NaN` values on either side of the join, throwing `CRITICAL` or `WARNING` tags based on where the data is missing.
* **Enterprise Automation:** In a real setting, you don't run `pd.read_csv()` locally. 
  * You pull data live via API or SQL.
  * You schedule the Python script on **Apache Airflow** or **Databricks Workflows** to run precisely at midnight (EOD).
  * You push the output flags to a Slack Webhook or a Power BI dashboard rather than a standard terminal printout.

## Module 3 & 4: Enterprise Data Centralization
**Goal:** Harmonize deeply fragmented systems into a single "Golden Record" to calculate accurate Client Lifetime Value.

* **The Data Swamp:** We simulated three highly disconnected datasets:
  1. `crm_users.json`: NoSQL document holding KYC status.
  2. `mt5_deals.csv`: Flat files exporting thousands of scattered trading events.
  3. `marketing_spend.db`: An SQLite relational database tracking Ad costs from Meta/Google.
* **The Medallion Approach:**
  * **Bronze:** Raw extraction scripts that securely wrap the APIs and dump the data exactly as-is into memory.
  * **Silver:** Aggregating granular logs (like thousands of MT5 deals) into a single "Total Profit" metric per user.
  * **Gold:** Performing a multi-table join resulting in a single pristine dashboard row per client holding `total_profit`, `acquisition_cost`, and `net_value`.

---
*Created on: April 12, 2026*
