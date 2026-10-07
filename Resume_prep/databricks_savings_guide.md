# Azure Databricks Cost Optimization & Savings Guide

This guide compiles the detailed, real-world breakdown of the **~$330K annual infrastructure cost savings** achieved by optimizing the Azure Databricks setup, simplifying calculation logic, and tuning Power BI query patterns.

Use these points to update your resume and prepare for technical and behavioral interviews.

---

## 1. Resume Bullet Point Variations

Depending on the specific focus of the roles you are applying for, you can use or adapt these variations:

### Option A: Balanced Data Engineering & BI Focus (Recommended)
> *"Optimized Azure Databricks architecture, delivering **~$330K in annual cloud savings** through a 90% reduction in ETL runtime (via Delta Lake Z-ordering & incremental merges), migrating pipelines to Spot-enabled Job clusters, and restructuring Power BI access flows to downsize SQL Warehouses."*

### Option B: Focus on Cloud Cost Governance & Performance
> *"Delivered **~$330K in annualized infrastructure cost savings** on Azure Databricks by migrating scheduled pipelines from All-Purpose to transient Jobs clusters, configuring Spot instances for worker nodes, and optimizing calculation logic to resolve data shuffling."*

### Option C: Focus on Analytics & BI Architecture
> *"Reduced annual Databricks compute spend by **~$330K** by transitioning Power BI dashboards from live DirectQuery to optimized Import Mode with incremental refreshes, reducing active SQL Warehouse uptime by 80% and downsizing compute sizes."*

---

## 2. Technical Levers of the Optimization

To achieve these savings, optimizations were implemented across three primary areas:

1. **Cluster Pricing & Scheduling**: Shifting production pipelines from expensive All-Purpose Interactive compute to automated Job clusters, and integrating Azure Spot instances for compute workers.
2. **Query & Pipeline Optimization**: Transitioning from daily full-history overrides to incremental daily processing using Delta Lake's `MERGE INTO`, combined with Z-Ordering and caching to reduce data shuffle.
3. **Power BI & SQL Warehouse Downsizing**: Migrating high-impact dashboards from live DirectQuery to Import Mode with incremental refresh, and tuning SQL Warehouse configurations (auto-suspend and sizing).

---

## 3. The Mathematics of the Savings (~$330K/Year)

The total annualized savings of **$336,805** are calculated across the following three categories:

### Bucket 1: Interactive to Jobs Compute Migration (~$165.6K saved)
* **The Problem**: 4 scheduled ADF pipelines were running on an always-on **All-Purpose Interactive** cluster (used for developer notebooks) because they triggered every 2 hours.
* **Before Configuration**:
  - Cluster: 1 Driver + 16 Worker Nodes (VM type: `Standard_D8s_v5` with 8 vCPUs, 32 GB RAM).
  - VM Cost: $0.384/hour per node.
  - DBU Rate (All-Purpose Premium): $0.40/DBU. A `Standard_D8s_v5` consumes 2 DBUs/hour ($0.80/hour DBU cost).
  - Total Hourly Cost per Node: $0.384 (VM) + $0.80 (DBU) = $1.184/hour.
  - Total Cluster Hourly Cost: 17 nodes × $1.184 = **$20.13/hour**.
  - **Annual Cost (Running 24/7)**: $20.13/hour × 24 hours × 365 days = **$176,338.80**.
* **After Configuration**:
  - Migrated the pipelines to transient **Jobs Compute Clusters** that terminate immediately upon completion.
  - Jobs DBU Rate: $0.15/DBU (representing a **62.5% discount** over All-Purpose DBU rates).
  - Azure Spot Instances: Replaced standard Pay-As-You-Go worker nodes with Spot VMs (saving ~70% on VM costs, reducing hourly VM cost from $0.384 to $0.115/hour). Drivers were kept on On-Demand VMs for stability.
  - Spot Node Hourly Cost: $0.115 (VM) + $0.30 (2 DBUs × $0.15) = $0.415/hour.
  - On-Demand Driver Hourly Cost: $0.384 (VM) + $0.30 (2 DBUs × $0.15) = $0.684/hour.
  - New Cluster Hourly Cost: (16 workers × $0.415) + $0.684 = **$7.324/hour**.
  - Run Time: Transient clusters run for a total of 4 hours daily across all pipeline runs.
  - **New Annual Cost**: $7.324/hour × 4 hours/day × 365 days = **$10,693.04**.
* **Bucket 1 Annual Savings**: $176,338.80 - $10,693.04 = **$165,645.76**

### Bucket 2: Simplifying Calculation Logic & Delta Lake Tuning (~$49.2K saved)
* **The Problem**: The feature engineering SQL query (generating the `gold_customer_risk_profile`) performed full table scans on millions of records, repeated joins, and scanned entire history records over sliding windows (1m, 3m, total) daily. Shuffling and data transfer overhead caused the job to take **8 hours** daily.
* **The Solution**:
  - **Incremental daily merges**: Switched from a daily full-history overwrite to an incremental daily logic using Delta Lake's `MERGE INTO` statement.
  - **Z-Ordering & Data Skipping**: Co-located data files (Z-Ordering) by `customer_id` and partitioned by transaction date, allowing Spark to skip reading 90% of files.
  - **Caching**: Cached lookup tables to avoid redundant scans.
  - This reduced pipeline runtime from **8 hours to 45 minutes** (a **90.6% runtime reduction**).
* **Savings Calculation**:
  - Cluster Configuration: Jobs cluster with 12 workers (`Standard_D16s_v5` instances costing a total of $18.60/hour).
  - **Before Annual Run Cost**: 8 hours/day × 365 days × $18.60/hour = **$54,312.00**.
  - **After Annual Run Cost**: 0.75 hours/day (45 mins) × 365 days × $18.60/hour = **$5,091.75**.
* **Bucket 2 Annual Savings**: $54,312.00 - $5,091.75 = **$49,220.25**

### Bucket 3: Power BI DirectQuery Optimization & SQL Warehouse Downsizing (~$121.9K saved)
* **The Problem**: 90+ complex reports loaded directly via Power BI **DirectQuery** against Databricks. Power BI sent unoptimized DAX/SQL queries that forced the Databricks SQL Warehouses to scale to maximum worker limits and remain active. The auto-termination timeout was left at the default 120 minutes, keeping warehouses running up to 16 hours a day (9:00 AM to 1:00 AM) due to scattered dashboard usage.
* **Before Configuration**:
  - SQL Warehouses: 3 active SQL Warehouses (Medium size: 16 DBUs each).
  - DBU Rate (SQL Premium): $0.22/DBU. DBU cost = $3.52/hour.
  - VM Cost (8 workers Standard_E8ds_v5): $0.52 × 8 = $4.16/hour.
  - Warehouse Hourly Cost: $3.52 (DBU) + $4.16 (VM) = $7.68/hour per warehouse.
  - Daily Runtime: 16 hours/day.
  - **Annual Cost for 3 Warehouses**: 3 × $7.68/hour × 16 hours/day × 365 days = **$134,553.60**.
* **After Configuration**:
  - **Semantic Aggregation**: Replaced raw data DirectQuery access with a Gold pre-aggregated reporting layer.
  - **Power BI Import Mode + Incremental Refresh**: Converted 80% of reports from live DirectQuery to Power BI Import Mode (refreshing 2-4 times a day instead of executing SQL queries on every dashboard click).
  - **Auto-Termination Tuning**: Reduced SQL Warehouse auto-termination from 120 minutes to 10 minutes.
  - **Downsized SQL Warehouses**: Downsized warehouses from Medium to Small (8 DBUs, costing $3.84/hour) as query volume and size dropped.
  - Due to caching and the 10-minute auto-termination, the active warehouse uptime dropped from 16 hours/day to an average of **3 hours/day**.
  - **New Annual Cost for 3 Warehouses**: 3 × $3.84/hour × 3 hours/day × 365 days = **$12,614.40**.
* **Bucket 3 Annual Savings**: $134,553.60 - $12,614.40 = **$121,939.20**

---

## 4. How to Articulate This in Interviews

### The Elevator Pitch
> *"I noticed our monthly cloud spend was climbing due to always-on All-Purpose clusters and unoptimized DirectQueries from Power BI. I led a cost optimization initiative that targeted three areas: cluster policy governance, query and data structure optimization, and BI access patterns. By migrating to transient job clusters, configuring Spot instances for worker nodes, writing incremental daily merges using Delta Lake, and moving reports to import mode with aggressive auto-suspend settings, I reduced our compute runtime by 90% and cut our annualized Databricks spend by over $330K."*

### Deep Dive Topics to Emphasize
* **Interactive vs. Jobs Compute**: Explain that scheduling production workloads on interactive All-Purpose clusters is a major anti-pattern. Shifting to Job-specific clusters saves 62.5% on licensing costs (DBUs) instantly.
* **Delta Lake Z-Ordering (Data Skipping)**: Explain that by Z-ordering tables by key lookup fields (like `customer_id` and transaction dates), you enabled Spark's metadata data skipping, avoiding full table scans.
* **Spot Instances with On-Demand Fallback**: Explain that you separated driver and worker pools, utilizing On-Demand VMs for drivers to keep the cluster manager stable, but using Spot VMs for workers to achieve a 70% discount on raw compute.
* **Power BI Governance**: Explain that DirectQuery runs a new SQL query on Databricks for every single visual filter click. Switching to Import Mode with incremental refreshes allowed the warehouse to auto-terminate quickly.
