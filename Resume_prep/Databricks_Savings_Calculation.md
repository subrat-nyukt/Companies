# Azure Databricks Cost Optimization & Savings Calculation Guide

This document provides a detailed, real-world breakdown of the **~$330K annual infrastructure cost savings** achieved by optimizing the Azure Databricks setup and query architecture. 

Use this guide to prepare for interview questions such as:
> *"You mention saving $330K annually on Databricks. Can you walk me through exactly how you calculated this figure and the specific technical changes you implemented?"*

---

## Executive Summary: The $330K Optimization Framework

The annual savings of **~$336,780** were achieved across three primary engineering buckets:

| Bucket | Optimization Area | Technical Lever | Annual Savings |
| :--- | :--- | :--- | :--- |
| **Bucket 1** | **Cluster Pricing & Scheduling** | Interactive to Jobs Cluster Migration + Spot Instance Integration | **~$165,650** |
| **Bucket 2** | **Query & Data Pipeline Tuning** | Delta Lake Incremental Processing (`MERGE INTO`) + Z-Ordering | **~$49,220** |
| **Bucket 3** | **BI & SQL Warehouse Downsizing** | Power BI DirectQuery Optimization + Warehouse Auto-Suspend Tuning | **~$121,910** |
| **Total** | | | **~$336,780** |

---

## Detailed Breakdown of the Calculation

### Bucket 1: Migrating from Interactive to Jobs Compute Clusters
* **The Problem**: 4 main data pipelines (ingesting transaction logs, processing installment plans, calculating risk features, and updating the customer gold table) were scheduled through Azure Data Factory (ADF) but targeted a shared, always-on **All-Purpose Interactive** cluster. Because jobs ran every 2 hours, the cluster was kept active continuously.
* **Before Optimization Configuration**:
  - **Cluster**: 1 Driver + 16 Worker Nodes (VM type: `Standard_D8s_v5` with 8 vCPUs, 32 GB RAM).
  - **VM Cost**: $0.384/hour per node.
  - **DBU Rate (All-Purpose Premium)**: $0.40/DBU. A `Standard_D8s_v5` node consumes 2 DBUs/hour ($0.80/hour DBU cost).
  - **Total Hourly Cost per Node**: $0.384 (VM) + $0.80 (DBU) = $1.184/hour.
  - **Total Cluster Hourly Cost**: 17 nodes × $1.184 = **$20.13/hour**.
  - **Annual Cost (Running 24/7)**: $20.13/hour × 24 hours × 365 days = **$176,338.80**.
* **After Optimization Configuration**:
  - Migrated the ADF pipelines to spin up transient **Jobs Compute Clusters** that terminate immediately upon pipeline completion.
  - **Jobs DBU Rate**: $0.15/DBU (representing a **62.5% discount** over All-Purpose DBU rates).
  - **Azure Spot Instances**: Replaced standard Pay-As-You-Go worker nodes with Spot VMs (saving ~70% on VM costs, reducing hourly VM cost from $0.384 to $0.115/hour). Drivers were kept on On-Demand VMs for stability.
  - **Spot Node Hourly Cost**: $0.115 (VM) + $0.30 (2 DBUs × $0.15) = $0.415/hour.
  - **On-Demand Driver Hourly Cost**: $0.384 (VM) + $0.30 (2 DBUs × $0.15) = $0.684/hour.
  - **New Cluster Hourly Cost**: (16 workers × $0.415) + $0.684 = **$7.324/hour**.
  - **Run Time**: Transient clusters run for a total of 4 hours daily across all pipeline runs.
  - **New Annual Cost**: $7.324/hour × 4 hours/day × 365 days = **$10,693.04**.
* **Bucket 1 Annual Savings**: $176,338.80 - $10,693.04 = **$165,645.76**

---

### Bucket 2: Simplifying Calculation Logic & Delta Lake Optimization
* **The Problem**: The feature engineering SQL query (generating the `gold_customer_risk_profile`) performed full table scans on millions of records, repeated joins, and scanned entire history records over sliding windows (1m, 3m, total) daily. Shuffling and data transfer overhead caused the job to take **8 hours** daily on an expensive cluster.
* **The Solution**:
  1. **Incremental daily merges**: Switched from a daily full-history overwrite to an incremental daily logic using Delta Lake's `MERGE INTO` statement.
  2. **Z-Ordering & Data Skipping**: Co-located data files (Z-Ordering) by `customer_id` and partitioned by transaction date, allowing Spark to skip reading 90% of files.
  3. **Caching**: Cached lookup tables to avoid redundant scans.
  - These optimizations reduced the pipeline run time from **8 hours to 45 minutes** (a **90.6% runtime reduction**).
* **Savings Calculation**:
  - **Cluster Configuration**: Jobs cluster with 12 workers (`Standard_D16s_v5` instances costing a total of $18.60/hour).
  - **Before Annual Run Cost**: 8 hours/day × 365 days × $18.60/hour = **$54,312.00**.
  - **After Annual Run Cost**: 0.75 hours/day (45 mins) × 365 days × $18.60/hour = **$5,091.75**.
* **Bucket 2 Annual Savings**: $54,312.00 - $5,091.75 = **$49,220.25**

---

### Bucket 3: Power BI DirectQuery Optimization & SQL Warehouse Downsizing
* **The Problem**: 90+ complex reports loaded directly via Power BI **DirectQuery** against Databricks. Power BI sent unoptimized DAX/SQL queries that forced the Databricks SQL Warehouses to scale to maximum worker limits and remain active. The auto-termination timeout was left at the default 120 minutes, keeping warehouses running up to 16 hours a day (9:00 AM to 1:00 AM) due to scattered dashboard usage.
* **Before Optimization Configuration**:
  - **SQL Warehouses**: 3 active SQL Warehouses (Medium size: 16 DBUs each).
  - **DBU Rate (SQL Premium)**: $0.22/DBU. DBU cost = $3.52/hour.
  - **VM Cost (8 workers Standard_E8ds_v5)**: $0.52 × 8 = $4.16/hour.
  - **Warehouse Hourly Cost**: $3.52 (DBU) + $4.16 (VM) = $7.68/hour per warehouse.
  - **Daily Runtime**: 16 hours/day.
  - **Annual Cost for 3 Warehouses**: 3 × $7.68/hour × 16 hours/day × 365 days = **$134,553.60**.
* **After Optimization Configuration**:
  1. **Semantic Aggregation**: Replaced raw data DirectQuery access with a Gold pre-aggregated reporting layer.
  2. **Power BI Import Mode + Incremental Refresh**: Converted 80% of reports from live DirectQuery to Power BI Import Mode (refreshing 2-4 times a day instead of executing SQL queries on every dashboard click).
  3. **Auto-Termination Tuning**: Reduced SQL Warehouse auto-termination from 120 minutes to 10 minutes.
  4. **Downsized SQL Warehouses**: Downsized warehouses from Medium to Small (8 DBUs, costing $3.84/hour) as query volume and size dropped.
  - Due to caching and the 10-minute auto-termination, the active warehouse uptime dropped from 16 hours/day to an average of **3 hours/day**.
  - **New Annual Cost for 3 Warehouses**: 3 × $3.84/hour × 3 hours/day × 365 days = **$12,614.40**.
* **Bucket 3 Annual Savings**: $134,553.60 - $12,614.40 = **$121,939.20**

---

## Total Annualized Cost Savings
* **Bucket 1**: $165,645.76
* **Bucket 2**: $49,220.25
* **Bucket 3**: $121,939.20
* **Grand Total**: **$336,805.21** (approximately **$330K/year**)

---

## How to Explain This in an Interview

### 1. The Elevator Pitch
> *"I noticed our cloud spend was growing rapidly due to always-on All-Purpose clusters and live DirectQueries from Power BI. I led a cost optimization initiative across three areas: cluster policy governance, query and data structure optimization, and BI access patterns. By migrating ETL jobs to transient Job clusters, configuring Spot VMs for worker pools, moving from full historical rewrites to daily incremental merges using Delta Lake, and moving reports to import mode with aggressive auto-suspend settings, I reduced our compute runtime by 90% and cut our annualized Databricks spend by over $330K."*

### 2. Deep Dive Topics to Emphasize
* **All-Purpose vs. Job Clusters**: Highlight that scheduling production workloads on interactive clusters is a major anti-pattern. Shifting to Job-specific clusters saves 62.5% on licensing costs (DBUs) instantly.
* **Z-Ordering & Data Skipping**: Explain that by Z-ordering tables by key lookup fields (like `customer_id` and transaction dates), you enabled Spark's metadata data skipping, avoiding full table scans.
* **Spot Instances**: Explain that you separated driver and worker pools, utilizing On-Demand VMs for drivers to keep the cluster manager stable, but using Spot VMs for workers to achieve a 70% discount on raw compute.
* **Power BI Governance**: Explain that DirectQuery runs a new SQL query on Databricks for every single visual filter click. Switching to Import Mode with incremental refreshes allowed the warehouse to auto-terminate quickly.
