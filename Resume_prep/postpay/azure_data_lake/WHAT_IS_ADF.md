# What is Azure Data Factory (ADF)?

## Simple Answer
**Azure Data Factory is a "data moving truck" in the cloud.** It takes data from one place (like SAP, SQL databases, files) and moves it to another place (like Azure Data Lake, Databricks, or another database).

---

## The Problem ADF Solves

### Before ADF:
```
❌ Manual data exports from SAP every night
❌ Custom scripts written in Python/PowerShell to copy files
❌ No centralized monitoring
❌ Scripts break when data format changes
❌ No retry logic when something fails
```

### With ADF:
```
✅ Automated scheduled data movement
✅ Visual pipeline designer (no code needed)
✅ Centralized monitoring dashboard
✅ Built-in error handling and alerts
✅ Auto-retry on failures
✅ Scales to handle big data
```

---

## Real-World Analogy

Think of your data architecture like a **supply chain**:

| Component | Real World | Data World |
|-----------|------------|------------|
| **Warehouse** | Physical storage of goods | SAP S/4HANA (source system) |
| **Truck** | Moves goods from warehouse to store | **Azure Data Factory** (moves data) |
| **Distribution Center** | Sorts and organizes goods | Azure Data Lake (storage) |
| **Store** | Final destination where customers shop | Power BI / Databricks (analytics) |

**ADF is the truck.** It doesn't store data (that's Data Lake), and it doesn't analyze data (that's Databricks/Power BI). It just **moves and transforms** data reliably.

---

## What ADF Does (5 Main Functions)

### 1. **Extract** (Copy Data from Sources)
ADF connects to 90+ different systems and extracts data:

**Supported Sources:**
- SAP S/4HANA, SAP BW, SAP ECC
- SQL Server, Oracle, MySQL, PostgreSQL
- Salesforce, Dynamics 365
- REST APIs, Web services
- Files (CSV, JSON, Excel, Parquet)
- Azure services (Blob Storage, Cosmos DB, Synapse)

**Example:**
```
Every night at 2 AM, ADF extracts the "Customers" table from SAP 
and copies it to Azure Data Lake
```

### 2. **Transform** (Clean and Modify Data)
ADF can change data while moving it:

**Common Transformations:**
- Filter rows (e.g., only customers from USA)
- Rename columns (`KUNNR` → `customer_id`)
- Join tables (combine customers + orders)
- Aggregate data (sum sales by country)
- Remove duplicates
- Convert data types

**Example:**
```
Input:  KUNNR | NAME1        | LAND1
        1000  | Customer A   | US

Output: customer_id | customer_name | country
        1000        | Customer A    | United States
```

### 3. **Load** (Write Data to Destination)
ADF writes the data to wherever you need it:

**Supported Destinations:**
- Azure Data Lake Storage
- Azure SQL Database
- Azure Synapse (Data Warehouse)
- Azure Databricks
- SQL Server on-premise
- Cosmos DB

**Example:**
```
Load the transformed customer data into Azure Data Lake 
in Parquet format for Databricks to process
```

### 4. **Orchestrate** (Coordinate Complex Workflows)
ADF can run multiple tasks in a specific order:

**Pipeline Example:**
```
Step 1: Extract customers from SAP
   ↓
Step 2: Extract orders from SAP
   ↓
Step 3: Join customers + orders
   ↓
Step 4: Load to Data Lake
   ↓
Step 5: Trigger Databricks to process
   ↓
Step 6: Send email notification "Job Complete"
```

If Step 2 fails, ADF can:
- Retry 3 times
- Send an alert email
- Skip to the next step
- Or stop the entire pipeline

### 5. **Schedule** (Run Automatically)
ADF runs your pipelines on a schedule without you doing anything:

**Schedule Types:**
- **Daily**: Every day at 2:00 AM
- **Hourly**: Every hour
- **Weekly**: Every Monday at 9:00 AM
- **Custom**: Every 15 minutes during business hours
- **Event-based**: When a new file arrives in storage

---

## Common Use Cases

### Use Case 1: **Data Warehouse Loading**
**Problem:** You have data in 10 different systems (SAP, Salesforce, SQL Server). You need it all in one place for reporting.

**Solution with ADF:**
```
ADF Pipeline:
1. Extract from SAP S/4HANA (customers, sales)
2. Extract from Salesforce (leads, opportunities)
3. Extract from SQL Server (inventory)
4. Transform: Standardize date formats, currency conversion
5. Load: Write to Azure Synapse Analytics
6. Schedule: Run every night at 2 AM
```

### Use Case 2: **Real-Time Analytics**
**Problem:** You need near-real-time sales data in Power BI.

**Solution with ADF:**
```
ADF Pipeline:
1. Extract from SAP using Change Data Capture (CDC)
2. Get only new/changed records (not full table)
3. Load to Data Lake in streaming mode
4. Trigger Databricks to update aggregates
5. Schedule: Run every 5 minutes
```

### Use Case 3: **Data Lake Migration**
**Problem:** Move 10 years of historical data from on-premise SQL Server to Azure.

**Solution with ADF:**
```
ADF Pipeline:
1. Connect to On-Premise SQL Server via Self-Hosted IR
2. Copy 50 tables (10 TB of data)
3. Use incremental loading (copy year by year)
4. Write to Data Lake in Parquet format
5. Run once, then schedule incremental updates daily
```

### Use Case 4: **Machine Learning Data Prep**
**Problem:** You need clean data for training ML models.

**Solution with ADF:**
```
ADF Pipeline:
1. Extract raw transactions from multiple sources
2. Transform: Remove nulls, deduplicate, feature engineering
3. Load to Databricks Delta tables
4. Trigger ML training job
5. Schedule: Run when new data arrives (event-based)
```

---

## Why Not Just Use Python Scripts?

| Aspect | Python Script | Azure Data Factory |
|--------|---------------|-------------------|
| **Scalability** | Runs on 1 machine | Distributed across cloud |
| **Monitoring** | Check logs manually | Visual dashboard |
| **Error Handling** | Write custom try/catch | Built-in retry logic |
| **Scheduling** | Use cron or Task Scheduler | Built-in triggers |
| **Security** | Hardcode passwords 😱 | Integrated with Key Vault |
| **Maintenance** | You fix when it breaks | Microsoft maintains it |
| **Cost** | Keep server running 24/7 | Pay only when running |

**When to use Python:**
- Quick one-time data migration
- Prototyping
- Custom transformations ADF can't do

**When to use ADF:**
- Production data pipelines
- Multiple data sources
- Need monitoring and alerts
- Enterprise-scale data movement

---

## ADF in Your SAP to Databricks Architecture

In your specific project, **ADF is the bridge** between SAP and Azure:

```
┌─────────────┐
│ SAP S/4HANA │ ← Source System (ERP)
│  (On-Prem)  │
└──────┬──────┘
       │
       │ (Connection via Self-Hosted IR)
       ↓
┌─────────────────────┐
│ Azure Data Factory  │ ← THE MOVER
│  - Scheduled daily  │
│  - Extracts tables  │
│  - Handles errors   │
└──────┬──────────────┘
       │
       │ (Writes Parquet files)
       ↓
┌─────────────────┐
│ Data Lake Gen2  │ ← STORAGE
│  - Bronze Layer │
└──────┬──────────┘
       │
       │ (Databricks reads from here)
       ↓
┌─────────────────┐
│  Databricks     │ ← PROCESSOR
│  - Transforms   │
└──────┬──────────┘
       │
       ↓
┌─────────────────┐
│   Power BI      │ ← VISUALIZATION
└─────────────────┘
```

**Without ADF:**
- You'd need to manually export CSVs from SAP every day
- Or write complex Python code to connect
- No monitoring when it breaks
- No automatic retry

**With ADF:**
- Set it once, runs forever
- Automatic retries
- Email alerts on failure
- Visual monitoring dashboard

---

## Summary

**Azure Data Factory = The "FedEx" of Data**

Just like FedEx:
- ✅ Picks up packages from your door (extracts from SAP)
- ✅ Tracks every shipment (monitoring dashboard)
- ✅ Delivers on schedule (triggers and schedules)
- ✅ Handles problems automatically (retry logic)
- ✅ Works 24/7 without you managing it

**Bottom Line:** ADF automates the boring, repetitive task of moving data so you can focus on analyzing it instead of manually copying it.
