# Azure Data Factory: SAP S/4HANA Integration - Complete Hands-On Guide

This guide provides step-by-step instructions for extracting, loading, and transforming data from SAP S/4HANA using Azure Data Factory.

---

## 📋 Table of Contents

1. [Prerequisites & Architecture](#prerequisites)
2. [Connection Setup](#connection-setup)
3. [Self-Hosted Integration Runtime](#integration-runtime)
4. [SAP Connectors Explained](#sap-connectors)
5. [Creating the Pipeline](#creating-pipeline)
6. [Data Transformation](#transformation)
7. [Scheduling & Monitoring](#scheduling)

---

## Prerequisites & Architecture {#prerequisites}

### What You Need
1. **SAP S/4HANA System**: Access credentials (username, password, or client certificate)
2. **Azure Subscription**: Active subscription with Data Factory resource
3. **Windows VM**: To install Self-Hosted Integration Runtime (can be on-premise or Azure VM)
4. **Network Access**: SAP system must be reachable from the VM

### Architecture Flow
```
SAP S/4HANA (On-Premise)
    ↓ [Port 8000/3300/443]
Self-Hosted Integration Runtime (VM)
    ↓ [Outbound HTTPS 443]
Azure Data Factory (Cloud)
    ↓ [Write]
Azure Data Lake Gen2 (Storage)
```

---

## Connection Setup {#connection-setup}

### Step 1: Create Linked Service to SAP

A **Linked Service** is ADF's way of storing connection information.

#### In Azure Data Factory Studio:

1. **Open ADF Studio** → Click **Manage** (toolbox icon) → **Linked services** → **+ New**

2. **Select Connector**: Search for **"SAP"**. You'll see three options:
   - **SAP Table** (Recommended for batch extraction)
   - **SAP OData** (For real-time APIs)
   - **SAP CDC** (Change Data Capture - for deltas only)

3. **Choose SAP Table** for this guide

#### Configuration Parameters:

```json
{
  "name": "LinkedService_SAP_HANA",
  "properties": {
    "type": "SapTable",
    "typeProperties": {
      "server": "sap-server.yourcompany.com",
      "systemNumber": "00",
      "clientId": "100",
      "language": "EN",
      "userName": "SAP_USER",
      "password": {
        "type": "AzureKeyVaultSecret",
        "store": {
          "referenceName": "AzureKeyVault1",
          "type": "LinkedServiceReference"
        },
        "secretName": "sap-password"
      }
    },
    "connectVia": {
      "referenceName": "SelfHostedIR",
      "type": "IntegrationRuntimeReference"
    }
  }
}
```

#### Field Explanations:

| Field | Description | Example |
|-------|-------------|---------|
| `server` | SAP Application Server hostname | `sap.company.com` |
| `systemNumber` | SAP system number (2 digits) | `00` or `01` |
| `clientId` | SAP client (mandant) | `100` or `800` |
| `language` | Logon language | `EN`, `DE`, `AR` |
| `userName` | SAP username | `RFC_USER` |
| `password` | Retrieved from Azure Key Vault | (stored securely) |

**Security Best Practice**: Never hardcode passwords! Always use Azure Key Vault.

---

## Self-Hosted Integration Runtime {#integration-runtime}

### What is it?
A bridge software installed on a Windows machine that can access both SAP (private network) and Azure (public cloud).

### Installation Steps:

#### 1. Create the IR in ADF:
```
ADF Studio → Manage → Integration runtimes → + New → Azure, Self-Hosted → Self-Hosted
```
- Name: `SelfHostedIR-SAP`
- Copy the **Authentication Key** (you'll need this)

#### 2. Install on Windows VM:

**Download:**
```powershell
# Run this on your Windows VM
Invoke-WebRequest -Uri "https://www.microsoft.com/en-us/download/details.aspx?id=39717" -OutFile "$env:TEMP\IntegrationRuntime.msi"
```

**Install:**
- Double-click the MSI
- Paste the **Authentication Key** when prompted
- The IR will register with Azure

#### 3. Verify Connection:
- Back in ADF Studio → Manage → Integration runtimes
- You should see `SelfHostedIR-SAP` with status: **Running** (green)

### Network Requirements:

**Outbound from VM:**
- Port 443 (HTTPS) to Azure endpoints
- Port 80 (HTTP) for certificate validation

**To SAP:**
- Port 3300 (SAP Gateway)
- Port 8000-8099 (SAP Application Server)
- Or Port 443 if using HTTPS/OData

---

## SAP Connectors Explained {#sap-connectors}

### Connector Comparison:

| Connector | Use Case | Data Volume | Speed | Delta Support |
|-----------|----------|-------------|-------|---------------|
| **SAP Table** | Full table extraction | Large (GB) | Fast | No (full refresh) |
| **SAP OData** | APIs, custom CDS views | Small (MB) | Medium | Yes (filters) |
| **SAP CDC** | Change Data Capture | Delta only | Very Fast | Yes (built-in) |

### Which One to Use?

**For this tutorial, use SAP Table because:**
- Works with standard SAP tables (KNA1, VBAK, BSEG, etc.)
- No special SAP configuration needed
- Fastest for initial loads

**When to use SAP CDC:**
- You need real-time updates (e.g., every 5 minutes)
- You've configured SAP Operational Data Provisioning (ODP)
- You only want changed/new records

---

## Creating the Pipeline {#creating-pipeline}

### Step 1: Create a New Pipeline

1. **ADF Studio** → **Author** (pencil icon) → **+ Pipeline** → Name: `SAP_to_DataLake_KNA1`

2. **Add Copy Data Activity:**
   - Drag **"Copy data"** from Activities → Move & transform
   - Name it: `Copy_KNA1_Customers`

### Step 2: Configure Source (SAP)

Click on the Copy activity → **Source** tab:

#### Create Source Dataset:

**Dataset Properties:**
```yaml
Name: DS_SAP_KNA1
Type: SapTableResource
Linked Service: LinkedService_SAP_HANA

Table Name: KNA1  # Customer Master
```

#### Advanced Options (Optional):

**Row Filter:**
```sql
LAND1 EQ 'US' OR LAND1 EQ 'DE'
```
*(Only extract US and Germany customers)*

**Column Selection:**
```
KUNNR, NAME1, LAND1, REGIO, ORT01, PSTLZ
```
*(Only these columns, not all 200+ fields in KNA1)*

**Partition:**
```yaml
Partition Option: Physical partitions of SAP table
Number of Partitions: 4
```
*(Split table into 4 chunks for parallel extraction = faster)*

### Step 3: Configure Sink (Data Lake)

Click **Sink** tab:

#### Create Sink Dataset:

**Dataset Properties:**
```yaml
Name: DS_ADLS_Bronze_KNA1
Type: DelimitedText (CSV) or Parquet
Linked Service: LinkedService_ADLS_Gen2

File Path:
  Container: bronze
  Directory: sap/kna1
  File Name: KNA1_@{formatDateTime(utcnow(),'yyyyMMdd_HHmmss')}.parquet
```

**Dynamic File Naming:**
- `@{formatDateTime(utcnow(),'yyyyMMdd_HHmmss')}` creates: `KNA1_20260214_123045.parquet`
- Every run creates a new file with timestamp

**Format Settings:**
```yaml
File Format: Parquet (Recommended - smaller, faster)
Compression: Snappy
First row as header: Yes (if CSV)
```

### Step 4: Configure Mapping

Click **Mapping** tab:

**Auto-detect schema** or manually map:

| Source (SAP) | Sink (ADLS) | Type |
|--------------|-------------|------|
| KUNNR | customer_id | String |
| NAME1 | customer_name | String |
| LAND1 | country_code | String |
| REGIO | region | String |

**Data Type Conversion:**
```json
{
  "translator": {
    "type": "TabularTranslator",
    "mappings": [
      {
        "source": {"name": "KUNNR", "type": "String"},
        "sink": {"name": "customer_id", "type": "String"}
      },
      {
        "source": {"name": "NAME1", "type": "String"},
        "sink": {"name": "customer_name", "type": "String"}
      }
    ]
  }
}
```

### Step 5: Settings Tab

```yaml
Enable Staging: No (for direct copy)
Degree of copy parallelism: Auto (or 4 for faster)
Data Integration Units: Auto (or 4-8 for large data)
Fault Tolerance: Skip incompatible rows
Enable logging: Yes (for debugging)
```

---

## Data Transformation {#transformation}

### In-Pipeline Transformations

While Copy Activity just moves data, you can add transformation activities:

#### 1. Data Flow Activity (for complex transformations)

**Add to pipeline**: Activities → Move & transform → **Data Flow**

**Example Transformation:**
```
Source (SAP KNA1)
  ↓
[Filter] → WHERE LAND1 IN ('US', 'DE', 'AE')
  ↓
[Select] → Rename columns, drop sensitive fields
  ↓
[Derived Column] → full_address = CONCAT(STREET, CITY, COUNTRY)
  ↓
[Aggregate] → COUNT customers by LAND1
  ↓
Sink (Data Lake Silver)
```

#### 2. Mapping Data Flow Script:

```
source(
  allowSchemaDrift: true,
  validateSchema: false
) ~> SAPSource

SAPSource filter(LAND1 == 'US' || LAND1 == 'DE') ~> FilterCountries

FilterCountries select(
  mapColumn(
    customer_id = KUNNR,
    name = NAME1,
    country = LAND1
  ),
  skipDuplicateMapInputs: true
) ~> RenameColumns

RenameColumns sink(
  allowSchemaDrift: true,
  validateSchema: false,
  format: 'parquet'
) ~> DataLakeSink
```

---

## Scheduling & Monitoring {#scheduling}

### Create a Trigger

1. **Pipeline** → **Add trigger** → **New/Edit**

2. **Trigger Types:**

#### Schedule Trigger (Most Common):
```yaml
Name: Daily_2AM_SAP_Extract
Type: Schedule
Recurrence: Daily
Start Time: 02:00 AM (UTC+4)
Time Zone: (UTC+04:00) Abu Dhabi, Muscat
End: No end date
```

#### Tumbling Window Trigger (for guaranteed execution):
```yaml
Name: Hourly_Delta_Extract
Type: Tumbling Window
Recurrence: Every 1 hour
Start Time: 2026-02-14 00:00:00
```

#### Event Trigger (when a file arrives):
```yaml
Trigger when: Blob created in container 'landing'
Storage Account: sapfiledrop
```

### Monitoring Runs

**Monitor Tab** → **Pipeline runs**

You'll see:
- Run ID
- Pipeline name
- Trigger type
- Status (Succeeded, Failed, In Progress)
- Duration
- Rows copied

**Click on a run** → See activity-level details:
- Copy Activity 1: 50,000 rows copied in 45 seconds
- Data throughput: 2.5 MB/s

---

## Practical Exercise: Hands-On Steps

### Exercise 1: Create Your First SAP Copy Pipeline

1. ✅ Install Self-Hosted IR on a VM
2. ✅ Create Linked Service to SAP (use demo credentials)
3. ✅ Create Linked Service to ADLS
4. ✅ Create Pipeline with Copy Activity
5. ✅ Configure Source: SAP Table `KNA1`
6. ✅ Configure Sink: ADLS `bronze/kna1/`
7. ✅ Run Debug
8. ✅ Check Data Lake for output file

### Exercise 2: Add Transformation

1. ✅ Add Data Flow activity after Copy
2. ✅ Filter only active customers (`LOEVM != 'X'`)
3. ✅ Aggregate: Count by country
4. ✅ Write to `silver/customer_summary/`

### Exercise 3: Schedule It

1. ✅ Create a Schedule Trigger for 2 AM daily
2. ✅ Publish the pipeline
3. ✅ Monitor the first run

---

## Troubleshooting Common Issues

### Issue 1: "Failed to connect to SAP server"
**Solution**: Check Self-Hosted IR can reach SAP on port 3300/8000

```powershell
# Test from IR machine
Test-NetConnection -ComputerName sap-server.company.com -Port 3300
```

### Issue 2: "Table does not exist or user has no authorization"
**Solution**: Grant SAP user S_TABU_DIS authorization object

```abap
* In SAP: Transaction SU01 → Select user → Change → Authorizations
* Add authorization object: S_TABU_DIS
* Table Name: KNA1 (or * for all)
```

### Issue 3: "Self-Hosted IR is offline"
**Solution**: Restart Integration Runtime service

```powershell
Restart-Service -Name "DIAHostService"
```

---

## Next Steps

Once you've mastered this, move on to:
1. **Incremental Loading** (only new/changed records)
2. **Parameterization** (reuse pipeline for multiple tables)
3. **Error Handling** (retry logic, alerts)
4. **Performance Tuning** (partitioning, parallelism)

---

**Practice these steps in your Azure portal to gain hands-on experience!**
