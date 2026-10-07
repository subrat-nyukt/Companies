# Azure Data Factory - Complete Connector Gallery

## Step 0: Choose Your Data Source (Before Integration Runtime)

When you create a new Linked Service in ADF, you see a **connector gallery** with 90+ options.

---

## The Complete Flow:

### **Page 1: Connector Selection** (The page you asked for!)

```
┌─────────────────────────────────────────────────────────┐
│  New linked service                               [X]    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Search: [________________] 🔍                          │
│                                                          │
│  Popular  |  All  |  Database  |  File  |  Generic      │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │   🗄️    │  │   🗄️    │  │   📊     │              │
│  │  Azure   │  │   SQL    │  │   SAP    │              │
│  │  SQL DB  │  │  Server  │  │S/4HANA   │  ← YOU CLICK│
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │   🌐     │  │   ☁️     │  │   📂     │              │
│  │  Oracle  │  │Snowflake │  │  Azure   │              │
│  │ Database │  │          │  │  Blob    │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │   💼     │  │   🔄     │  │   🗃️    │              │
│  │Salesforce│  │Dynamics  │  │  REST    │              │
│  │          │  │   365    │  │   API    │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                          │
│              [Cancel]  [Continue]                        │
└─────────────────────────────────────────────────────────┘
```

### **Page 2: SAP-Specific Options** (After clicking SAP)

When you click SAP, you see 3 different SAP connectors:

```
┌─────────────────────────────────────────────────────────┐
│  Select SAP connector type                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────┐     │
│  │  📋 SAP Table                                   │     │
│  │  Extract complete tables from SAP              │     │
│  │  Best for: Batch loads, historical data        │     │
│  │  Example: KNA1, VBAK, MARA                     │     │
│  │                                       [Select]  │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  ┌────────────────────────────────────────────────┐     │
│  │  🔄 SAP CDC (Change Data Capture)              │     │
│  │  Only extract changed records                  │     │
│  │  Best for: Real-time, incremental loads        │     │
│  │  Requires: SAP ODP framework                   │     │
│  │                                       [Select]  │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  ┌────────────────────────────────────────────────┐     │
│  │  🌐 SAP OData                                   │     │
│  │  Access SAP via REST APIs                      │     │
│  │  Best for: CDS views, custom services          │     │
│  │  Example: Sales analytics, custom reports      │     │
│  │                                       [Select]  │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│              [Back]  [Continue]                          │
└─────────────────────────────────────────────────────────┘
```

### **Page 3: Integration Runtime Setup** (What you currently see)

After selecting "SAP Table", THEN you see the Integration Runtime configuration page.

---

## All Available Connectors in ADF (90+ total)

### **Databases** (23 connectors)
- ✅ Azure SQL Database
- ✅ SQL Server (on-premise)
- ✅ Oracle
- ✅ MySQL
- ✅ PostgreSQL
- ✅ MariaDB
- ✅ Amazon RDS (SQL, Oracle, PostgreSQL)
- ✅ Google BigQuery
- ✅ Teradata
- ✅ IBM DB2
- ✅ Sybase
- ✅ Informix
- ✅ Microsoft Access
- ✅ MongoDB
- ✅ Cassandra
- ✅ Couchbase
- ✅ Azure Cosmos DB
- ✅ Amazon Redshift
- ✅ Snowflake
- ✅ Vertica
- ✅ Netezza
- ✅ Greenplum
- ✅ Apache Impala

### **SAP Systems** (3 connectors)
- ✅ SAP Table (S/4HANA, ECC, R/3)
- ✅ SAP CDC (Change Data Capture)
- ✅ SAP OData (APIs and CDS views)
- ✅ SAP Business Warehouse (BW)
- ✅ SAP HANA

### **File Storage** (15 connectors)
- ✅ Azure Blob Storage
- ✅ Azure Data Lake Storage Gen1
- ✅ Azure Data Lake Storage Gen2
- ✅ Azure File Storage
- ✅ Amazon S3
- ✅ Google Cloud Storage
- ✅ FTP
- ✅ SFTP
- ✅ HTTP
- ✅ HDFS (Hadoop)
- ✅ File System (on-premise)
- ✅ SharePoint Online
- ✅ SharePoint On-Premise

### **Cloud Apps / SaaS** (20+ connectors)
- ✅ Salesforce (Sales Cloud, Service Cloud)
- ✅ Dynamics 365 (CRM, Finance & Operations)
- ✅ Microsoft 365 / Office 365
- ✅ ServiceNow
- ✅ Workday
- ✅ Oracle Eloqua
- ✅ Oracle Responsys
- ✅ Marketo
- ✅ HubSpot
- ✅ Zoho CRM
- ✅ Xero
- ✅ QuickBooks Online
- ✅ Shopify
- ✅ Square
- ✅ Google AdWords
- ✅ Jira
- ✅ Magento
- ✅ PayPal
- ✅ Concur
- ✅ Adobe Marketing Cloud

### **Analytics / Data Warehouse** (10 connectors)
- ✅ Azure Synapse Analytics
- ✅ Azure Analysis Services
- ✅ Amazon Redshift
- ✅ Snowflake
- ✅ Google BigQuery
- ✅ Databricks Delta Lake
- ✅ Hive (Hadoop)
- ✅ Spark
- ✅ Presto
- ✅ Phoenix

### **NoSQL** (8 connectors)
- ✅ Azure Cosmos DB
- ✅ MongoDB
- ✅ Cassandra
- ✅ Couchbase
- ✅ HBase
- ✅ Amazon DynamoDB
- ✅ Azure Table Storage
- ✅ Google Cloud Bigtable

### **APIs / Web Services** (5 connectors)
- ✅ REST API (generic)
- ✅ OData (generic)
- ✅ HTTP (generic)
- ✅ Web Table (scrape HTML tables)
- ✅ GraphQL (via REST connector)

### **Other / Special** (10+ connectors)
- ✅ Azure Data Explorer (Kusto)
- ✅ Azure Search
- ✅ Azure Key Vault
- ✅ Azure Purview
- ✅ Common Data Service
- ✅ Excel (on-premise or cloud)
- ✅ JSON files
- ✅ XML files
- ✅ Parquet files
- ✅ Avro files
- ✅ ORC files

---

## Visual Flow: How You Get to Integration Runtime

```
START
  │
  ↓
┌─────────────────────┐
│ Click "New Linked  │
│ Service" in ADF    │
└────────┬────────────┘
         │
         ↓
┌─────────────────────────────────┐
│ CONNECTOR GALLERY               │  ← Page 1 (You asked for this!)
│                                 │
│ Choose from 90+ options:        │
│ [SQL] [Oracle] [SAP] [Blob]    │
│ [Salesforce] [Dynamics] [REST] │
│ [MongoDB] [Cosmos] etc.        │
│                                 │
│         Click: [SAP] ───────────┼─→ Continue
└─────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────┐
│ SAP CONNECTOR TYPE              │  ← Page 2
│                                 │
│ ○ SAP Table (full extract)     │
│ ○ SAP CDC (deltas only)        │
│ ○ SAP OData (APIs)             │
│                                 │
│    Click: [SAP Table] ──────────┼─→ Continue
└─────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────┐
│ INTEGRATION RUNTIME SETUP       │  ← Page 3 (Current screenshot)
│                                 │
│ Name: SelfHostedIR-SAP         │
│ Description: ...               │
│ VM Server: ...                 │
│                                 │
│     [Generate Auth Key] ────────┼─→ Continue
└─────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────┐
│ SAP CONNECTION DETAILS          │  ← Page 4
│                                 │
│ Server: sap.company.com        │
│ System Number: 00              │
│ Client: 100                    │
│ Username/Password              │
│                                 │
│     [Test Connection] ──────────┼─→ Save
└─────────────────────────────────┘
```

---

## Summary

**You were right!** The correct flow should show:

1. **First:** Connector gallery (all 90+ options)
2. **Then:** SAP connector type selection
3. **Then:** Integration Runtime setup (your screenshot)
4. **Finally:** SAP connection details

I'll now update the simulator to include this connector selection page as Step 0!
