# How to Connect ADF to Data Lake

## Quick Answer: **Create a Linked Service in ADF** 🔗

The connection from Azure Data Factory to Data Lake is configured **inside ADF** using a **Linked Service**.

---

## What is a Linked Service?

A **Linked Service** is like a "saved connection" in ADF. It stores:
- Where to connect (Data Lake URL)
- How to authenticate (Account Key, Managed Identity, etc.)
- Which Integration Runtime to use

Think of it like saving Wi-Fi credentials - once saved, all your pipelines can use it!

---

## Step-by-Step: Create Data Lake Linked Service

### Step 1: Open ADF Studio
```
Azure Portal → Data Factory → adf-postpay-dev → Author & Monitor
```

### Step 2: Go to Manage Section
```
Left Sidebar:
- Author (pencil icon)
- Monitor (chart icon)
- Manage (gear icon) ← Click this!
```

### Step 3: Click "Linked Services"
```
Manage Section:
├── Linked services ← Click here!
├── Integration runtimes
├── Triggers
└── Parameters
```

### Step 4: Click "+ New"
```
Click the "+ New" button at the top
```

### Step 5: Search for "Azure Data Lake Storage Gen2"
```
In the connector search box, type:
"Data Lake Gen2"

Select: "Azure Data Lake Storage Gen2"
```

### Step 6: Configure the Connection

#### **Name:**
```
DataLake_Gen2
```
(or any descriptive name like "adlspostpaydev_connection")

#### **Authentication Method:** (Choose one)

**Option A: Account Key (Simple, but less secure)**
```
Account selection method: Enter manually
URL: https://adlspostpaydev.dfs.core.windows.net/
Authentication type: Account key

Account key: [Get from Data Lake → Access Keys]
```

**Option B: System Assigned Managed Identity (Recommended!)**
```
Account selection method: From Azure subscription
Subscription: [Your subscription]
Storage account: adlspostpaydev
Authentication type: System Assigned Managed Identity

✅ No password needed!
✅ More secure
✅ Automatically managed by Azure
```

#### **Integration Runtime:**
```
Select: AutoResolveIntegrationRuntime
(Use Azure IR for Azure-to-Azure connections)
```

### Step 7: Test Connection
```
Click "Test connection" at the bottom

Expected result: "Connection successful" ✓
```

### Step 8: Create
```
Click "Create" button
```

---

## The Two Connections in Your Architecture

### Connection 1: **ADF → SAP** (via Self-Hosted IR)
```json
{
  "name": "SAP_S4HANA_Production",
  "type": "SapTable",
  "properties": {
    "server": "sap-prod.company.com",
    "systemNumber": "00",
    "clientId": "100",
    "userName": "technical_user",
    "password": {
      "type": "AzureKeyVaultSecret",
      "store": "AzureKeyVault",
      "secretName": "SAPPassword"
    },
    "connectVia": {
      "referenceName": "SelfHostedIR-SAP",
      "type": "IntegrationRuntimeReference"
    }
  }
}
```

### Connection 2: **ADF → Data Lake** (via Azure IR)
```json
{
  "name": "DataLake_Gen2",
  "type": "AzureBlobFS",
  "properties": {
    "url": "https://adlspostpaydev.dfs.core.windows.net/",
    "authenticationType": "ManagedIdentity",
    "connectVia": {
      "referenceName": "AutoResolveIntegrationRuntime",
      "type": "IntegrationRuntimeReference"
    }
  }
}
```

---

## Visual Flow

```
┌──────────────────────────────────────────────────────────┐
│         Your ADF has 2 Linked Services                   │
└──────────────────────────────────────────────────────────┘

ADF Studio
│
├─ Linked Service 1: "SAP_S4HANA_Production"
│  ├─ Type: SAP Table
│  ├─ Server: sap-prod.company.com
│  ├─ Auth: Username/Password (from Key Vault)
│  └─ IR: SelfHostedIR-SAP ← On-premise gateway
│
└─ Linked Service 2: "DataLake_Gen2"
   ├─ Type: Azure Data Lake Gen2
   ├─ URL: https://adlspostpaydev.dfs.core.windows.net/
   ├─ Auth: Managed Identity (automatic)
   └─ IR: AutoResolveIntegrationRuntime ← Cloud IR

When you create a pipeline:
1. Source Dataset uses: SAP_S4HANA_Production ←┐
2. Sink Dataset uses: DataLake_Gen2           ←┘ Both configured in ADF!
```

---

## Where is This Configured?

### ✅ Configured IN ADF:
- ✅ Data Lake connection (Linked Service)
- ✅ SAP connection (Linked Service)
- ✅ Integration Runtimes
- ✅ Pipelines
- ✅ Triggers

### ❌ NOT Configured in Data Lake:
- ❌ Data Lake CANNOT initiate connections
- ❌ Data Lake CANNOT run pipelines
- ❌ Data Lake just receives data

---

## Authentication Options Comparison

| Method | Security | Setup Difficulty | Use When |
|--------|----------|------------------|----------|
| **Account Key** | ⚠️ Low | Easy | Testing, demos |
| **Managed Identity** | ✅ High | Medium | **Production (recommended!)** |
| **Service Principal** | ✅ High | Medium | Cross-tenant access |
| **SAS Token** | ⚠️ Medium | Easy | Time-limited access |

---

## Getting the Data Lake URL

### Method 1: From Azure Portal
```
Azure Portal → Storage Accounts → adlspostpaydev → Properties

Look for:
Primary endpoint (Data Lake Storage):
https://adlspostpaydev.dfs.core.windows.net/
                    ↑
              Copy this URL!
```

### Method 2: Pattern
```
https://<storage-account-name>.dfs.core.windows.net/

Example:
https://adlspostpaydev.dfs.core.windows.net/
```

---

## Getting the Account Key (if using Account Key auth)

```
Azure Portal → Storage Accounts → adlspostpaydev → Access keys

You'll see:
- key1: [Show] [Copy]
- key2: [Show] [Copy]

Click [Show] then [Copy], paste into ADF Linked Service
```

**⚠️ Warning:** Don't hardcode keys! Use Azure Key Vault instead.

---

## Using Managed Identity (Recommended)

### Step 1: Enable Managed Identity on ADF
```
ADF is created with System Assigned Managed Identity by default
✅ No extra setup needed!
```

### Step 2: Grant ADF Access to Data Lake
```
Azure Portal → Storage Account (adlspostpaydev) → Access Control (IAM)

Click "+ Add role assignment"

Role: Storage Blob Data Contributor
Assign access to: Managed Identity
Select: adf-postpay-dev

Click "Save"
```

### Step 3: Use Managed Identity in Linked Service
```
In ADF Linked Service:
Authentication type: System Assigned Managed Identity

✅ No password needed!
✅ Azure handles authentication automatically
```

---

## Testing the Connection

### In ADF Linked Service:
```
1. Fill in all fields
2. Click "Test connection" at bottom
3. Wait for result...

✅ Success: "Connection successful"
   → Ready to use!

❌ Failed: "Test connection failed"
   → Check error message
   → Common issues:
      - Wrong URL
      - Missing permissions
      - Integration Runtime not running
```

---

## Using the Linked Service in a Pipeline

Once created, use it in your datasets:

### Example: Source Dataset (SAP)
```
Dataset name: SAP_KNA1_Table
Linked service: SAP_S4HANA_Production ← Use here!
Table: KNA1
```

### Example: Sink Dataset (Data Lake)
```
Dataset name: DataLake_Bronze_Parquet
Linked service: DataLake_Gen2 ← Use here!
Container: bronze
Folder path: sap/kna1/
Format: Parquet
```

---

## The Full Connection Chain

```
Pipeline Activity
    ↓
Uses Dataset
    ↓
Dataset uses Linked Service
    ↓
Linked Service connects to Data Lake
    ↓
Data Lake receives the data
```

**Example:**
```
Copy Activity: "Copy_SAP_to_Lake"
    ↓
Sink Dataset: "DataLake_Bronze_Parquet"
    ↓
Linked Service: "DataLake_Gen2"
    ↓
Connects to: adlspostpaydev.dfs.core.windows.net
    ↓
Writes to: bronze/sap/kna1/
```

---

## Common Connection Issues

### Issue 1: "Test connection failed: The remote server returned an error: (403) Forbidden"

**Cause:** ADF doesn't have permission to access Data Lake

**Fix:**
```
Go to Data Lake → Access Control (IAM)
Add role: Storage Blob Data Contributor
Assign to: adf-postpay-dev (Managed Identity)
```

---

### Issue 2: "Test connection failed: The remote name could not be resolved"

**Cause:** Wrong URL

**Fix:**
```
Check URL format:
✅ Correct: https://adlspostpaydev.dfs.core.windows.net/
❌ Wrong: https://adlspostpaydev.blob.core.windows.net/
          (blob, not dfs!)
```

---

### Issue 3: "Account key is invalid"

**Cause:** Key was rotated or copied incorrectly

**Fix:**
```
Get fresh key from:
Data Lake → Access Keys → key1 → Show → Copy
Paste into ADF Linked Service
```

---

## Security Best Practices

### ✅ DO:
- Use Managed Identity for authentication
- Store Account Keys in Azure Key Vault (if you must use them)
- Use separate Linked Services for dev/test/prod
- Regularly rotate account keys

### ❌ DON'T:
- Hardcode account keys in pipelines
- Share account keys via email/chat
- Use the same credentials for all environments
- Give ADF Owner role (use Contributor instead)

---

## Summary

### How to Connect ADF to Data Lake?

**Answer:** Create a **Linked Service** in ADF

**Where?** 
```
ADF Studio → Manage → Linked Services → + New
→ Select "Azure Data Lake Storage Gen2"
→ Configure connection
→ Test → Create
```

**Authentication:** 
- **Best:** Managed Identity (no password!)
- **Alternative:** Account Key (from Data Lake → Access Keys)

**Then use it:**
```
Pipeline → Dataset → Linked Service → Data Lake
All configured in ADF, not in Data Lake!
```

---

## Quick Reference

| What | Where to Configure | Tool |
|------|-------------------|------|
| **Data Lake connection** | ADF → Manage → Linked Services | ✅ ADF |
| **SAP connection** | ADF → Manage → Linked Services | ✅ ADF |
| **Pipeline** | ADF → Author → Pipelines | ✅ ADF |
| **Schedule** | ADF → Manage → Triggers | ✅ ADF |
| **Storage containers** | Storage Account → Containers | Data Lake |
| **Access permissions** | Storage Account → IAM | Data Lake |

**Bottom Line:** The connection FROM ADF TO Data Lake is configured IN ADF using Linked Services! 🎯
