# Azure Cloud Setup Guide: Real Implementation

This guide will walk you through setting up the real Azure infrastructure to run the SAP simulation end-to-end.

## Prerequisites
- Azure Account (Free tier works)
- Azure Databricks Workspace (You already have this)
- Azure CLI or Azure Portal access

---

## Step 1: Create Azure Data Lake Storage Gen2

### Option A: Using Azure Portal (GUI)
1. Go to [Azure Portal](https://portal.azure.com)
2. Click **"Create a resource"** → Search for **"Storage account"**
3. Click **Create**

**Configuration:**
- **Resource Group**: Create new → `rg-postpay-demo`
- **Storage account name**: `adlspostpaydev` (must be globally unique, lowercase, no spaces)
- **Region**: Same as your Databricks (e.g., `East US`)
- **Performance**: Standard
- **Redundancy**: LRS (Locally Redundant - cheapest)

**Advanced Tab:**
- **Enable hierarchical namespace**: ✅ **YES** (This makes it Data Lake Gen2)

Click **Review + Create** → **Create**

4. **After creation**, go to the Storage Account
5. Click **Containers** (left menu)
6. Create three containers:
   - `bronze` (for raw data)
   - `silver` (for cleaned data)
   - `gold` (for business data)

### Option B: Using Azure CLI
```bash
# Login
az login

# Create Resource Group
az group create --name rg-postpay-demo --location eastus

# Create Storage Account with Hierarchical Namespace (Data Lake)
az storage account create \
  --name adlspostpaydev \
  --resource-group rg-postpay-demo \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2 \
  --enable-hierarchical-namespace true

# Create Containers
az storage container create --name bronze --account-name adlspostpaydev
az storage container create --name silver --account-name adlspostpaydev
az storage container create --name gold --account-name adlspostpaydev
```

---

## Step 2: Upload Simulated SAP Data to Data Lake

### Get the Storage Account Key
1. Go to your Storage Account → **Access keys** (left menu)
2. Click **Show keys**
3. Copy **key1** value

### Upload Files using Azure Storage Explorer (Recommended)
1. Download [Azure Storage Explorer](https://azure.microsoft.com/en-us/products/storage/storage-explorer/)
2. Install and open it
3. Click **"Add an account"** → Sign in with Azure
4. Navigate to: **Storage Accounts** → `adlspostpaydev` → **Blob Containers** → `bronze`
5. Click **Upload** → **Upload Files**
6. Select the files from your local `sap_system_source` folder:
   - `KNA1.csv`
   - `VBAK.csv`

### OR Upload via Python Script
I can create a script that uploads the simulated data directly to Azure ADLS.

---

## Step 3: Create Azure Data Factory

### Using Azure Portal
1. Go to [Azure Portal](https://portal.azure.com)
2. Click **"Create a resource"** → Search for **"Data Factory"**
3. Click **Create**

**Configuration:**
- **Resource Group**: `rg-postpay-demo` (same as storage)
- **Name**: `adf-postpay-pipeline`
- **Region**: Same region as your storage
- **Version**: V2

Click **Review + Create** → **Create**

4. After creation, click **"Launch Studio"** to open the ADF interface

---

## Step 4: Create ADF Pipeline (Copy Activity)

This pipeline will simulate the "SAP → Data Lake" ingestion.

### In ADF Studio:
1. Click **Author** (pencil icon on left)
2. Click **+** → **Pipeline** → Name it: `Copy_SAP_to_Bronze`

3. **Add Copy Data Activity**:
   - Drag **"Copy data"** from Activities → Move & transform
   - Name it: `Copy_KNA1`

4. **Configure Source**:
   - Click on the Copy activity → **Source** tab
   - Click **+ New** next to Dataset
   - Select **Azure Data Lake Storage Gen2** → **DelimitedText** → Continue
   - **Linked service**: Click **+ New**
     - Name: `LS_ADLS_PostPay`
     - Account selection method: **From Azure subscription**
     - Storage account name: `adlspostpaydev`
     - Test connection → **Create**
   - **File path**: `bronze` / `KNA1.csv`
   - **First row as header**: ✅ Yes

5. **Configure Sink (Destination)**:
   - Click **Sink** tab
   - Click **+ New** next to Dataset
   - Select **Azure Data Lake Storage Gen2** → **Parquet** → Continue
   - Use the same Linked Service: `LS_ADLS_PostPay`
   - **File path**: `silver` / `clean_kna1.parquet`

6. Click **Validate** (top toolbar) → **Publish all** → **Debug** to test

---

## Step 5: Connect Databricks to Data Lake

### Get Storage Account Credentials
1. Go to Storage Account → **Access keys**
2. Copy **key1**

### In Databricks:
1. Create a new **Python Notebook**
2. Run this cell to mount the Data Lake:

```python
# Configuration
storage_account_name = "adlspostpaydev"
storage_account_key = "YOUR_KEY_HERE"  # Paste key1 value
container_name = "bronze"

# Mount Bronze
dbutils.fs.mount(
  source = f"wasbs://{container_name}@{storage_account_name}.blob.core.windows.net",
  mount_point = "/mnt/bronze",
  extra_configs = {f"fs.azure.account.key.{storage_account_name}.blob.core.windows.net": storage_account_key}
)

# Repeat for silver and gold
```

3. **Verify the mount**:
```python
display(dbutils.fs.ls("/mnt/bronze"))
```

You should see `KNA1.csv` and `VBAK.csv`!

---

## Step 6: Run the ETL in Databricks

Create a new **SQL Notebook** and run the same transformation logic:

```sql
-- Read from Bronze
CREATE OR REPLACE TEMP VIEW bronze_customers AS
SELECT * FROM csv.`/mnt/bronze/KNA1.csv`;

-- Clean to Silver
CREATE OR REPLACE TABLE silver.customers AS
SELECT 
  KUNNR,
  UPPER(NAME1) as customer_name,
  LAND1 as country,
  REGIO as region
FROM bronze_customers
WHERE NAME1 IS NOT NULL;

-- Aggregate to Gold
CREATE OR REPLACE TABLE gold.country_sales AS
SELECT 
  country,
  COUNT(*) as customer_count
FROM silver.customers
GROUP BY country;
```

---

## Step 7: Connect Power BI

Use the connection details from your Databricks SQL Warehouse (we covered this earlier).

Point it to the `gold.country_sales` table.

---

## Cost Estimate (Free Tier)
- **ADLS Gen2**: First 5GB free, then ~$0.02/GB
- **ADF**: First 1M executions free
- **Databricks**: You already have this

Total monthly cost for this demo: **< $1** 

---

**Next Steps**: Run `virtual_s4_hana.py` locally, then follow Steps 1-7 to deploy to real Azure cloud!
