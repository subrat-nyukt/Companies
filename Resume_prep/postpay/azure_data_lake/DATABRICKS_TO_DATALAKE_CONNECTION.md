# How to Connect Data Lake to Azure Databricks

## Quick Answer: **Configure the Connection IN Databricks** 🔗

The connection from Databricks to Data Lake is configured **inside Databricks** using authentication credentials. Data Lake is just storage - it doesn't initiate connections!

---

## Overview: The Connection Flow

```
Azure Data Lake Storage Gen2 (adlspostpaydev)
    ├── bronze/sap/kna1/
    ├── silver/customers/
    └── gold/analytics/
           ↓
    [Connection configured IN Databricks]
           ↓
Azure Databricks Cluster
    └── Read/Write data using Spark
```

---

## 3 Ways to Connect Databricks to Data Lake

### Method 1: **Access Keys** (Simple, NOT recommended for production)
### Method 2: **Service Principal** (Good for production)
### Method 3: **Managed Identity** (BEST for production)

We'll cover all three, but focus on Service Principal (most common).

---

## METHOD 1: Access Keys (Quick Setup)

### ⚠️ WARNING: NOT SECURE FOR PRODUCTION!
Access keys are like passwords - anyone with the key has full access.

### Step 1: Get Access Key from Data Lake

```
Azure Portal → Storage Accounts → adlspostpaydev → Access keys

You'll see:
key1: [Show] [Copy]  ← Click Show, then Copy
key2: [Show] [Copy]
```

### Step 2: Configure in Databricks Notebook

```python
# Set configuration for this session
spark.conf.set(
    "fs.azure.account.key.adlspostpaydev.dfs.core.windows.net",
    "YOUR_ACCESS_KEY_HERE"
)

# Now you can read from Data Lake
df = spark.read.parquet("abfss://bronze@adlspostpaydev.dfs.core.windows.net/sap/kna1/")
df.show()
```

### URL Format Explained:
```
abfss://CONTAINER@STORAGE_ACCOUNT.dfs.core.windows.net/PATH

Example:
abfss://bronze@adlspostpaydev.dfs.core.windows.net/sap/kna1/
  │      │       │                                    │
  │      │       └─ Storage account name              └─ Folder path
  │      └─ Container name
  └─ Protocol (Azure Blob File System Secure)
```

### ❌ Problems with Access Keys:
- Hard to rotate (need to update everywhere)
- Hard to track who's using them
- If leaked, anyone can access your data
- Not recommended by Microsoft

---

## METHOD 2: Service Principal (RECOMMENDED) ⭐

### What is a Service Principal?
Think of it as a "service account" - an identity for your application (Databricks) to authenticate with Azure.

### Step-by-Step Setup:

### **STEP 1: Create Service Principal (App Registration)**

```
Azure Portal → Azure Active Directory → App registrations → + New registration

Name: databricks-datalake-sp
Supported account types: Single tenant
Redirect URI: Leave blank

Click [Register]
```

**After creation, note these 3 values:**
1. **Application (client) ID**: `12345678-1234-1234-1234-123456789abc`
2. **Directory (tenant) ID**: `87654321-4321-4321-4321-cba987654321`
3. **Client Secret**: (create in next step)

---

### **STEP 2: Create Client Secret**

```
Your App → Certificates & secrets → + New client secret

Description: databricks-access
Expires: 24 months (or custom)

Click [Add]

⚠️ IMPORTANT: Copy the secret VALUE immediately!
It won't be shown again!

Example: AbC123_~xYz789-pQr456
```

---

### **STEP 3: Grant Permissions to Data Lake**

```
Azure Portal → Storage Accounts → adlspostpaydev → Access Control (IAM)

Click [+ Add role assignment]

Role: Storage Blob Data Contributor
Assign access to: User, group, or service principal
Select: databricks-datalake-sp

Click [Save]
```

**What this does:** Gives your service principal read/write access to the Data Lake.

---

### **STEP 4: Store Secrets in Databricks Secret Scope**

**Why?** Never hardcode credentials in notebooks!

#### Create Secret Scope (One-time setup):

```
Method 1: Using Databricks CLI
databricks secrets create-scope --scope data-lake-scope

Method 2: Using Databricks UI
Navigate to: https://<databricks-instance>#secrets/createScope
Scope name: data-lake-scope
Manage Principal: All Users

Click [Create]
```

#### Add Secrets to Scope:

```bash
# Add client ID
databricks secrets put --scope data-lake-scope --key client-id
# Paste: 12345678-1234-1234-1234-123456789abc

# Add tenant ID
databricks secrets put --scope data-lake-scope --key tenant-id
# Paste: 87654321-4321-4321-4321-cba987654321

# Add client secret
databricks secrets put --scope data-lake-scope --key client-secret
# Paste: AbC123_~xYz789-pQr456
```

---

### **STEP 5: Configure Connection in Databricks Notebook**

```python
# Get secrets from scope (secure!)
client_id = dbutils.secrets.get(scope="data-lake-scope", key="client-id")
tenant_id = dbutils.secrets.get(scope="data-lake-scope", key="tenant-id")
client_secret = dbutils.secrets.get(scope="data-lake-scope", key="client-secret")

# Configure Spark to use Service Principal
spark.conf.set("fs.azure.account.auth.type.adlspostpaydev.dfs.core.windows.net", "OAuth")
spark.conf.set("fs.azure.account.oauth.provider.type.adlspostpaydev.dfs.core.windows.net", 
               "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
spark.conf.set("fs.azure.account.oauth2.client.id.adlspostpaydev.dfs.core.windows.net", client_id)
spark.conf.set("fs.azure.account.oauth2.client.secret.adlspostpaydev.dfs.core.windows.net", client_secret)
spark.conf.set("fs.azure.account.oauth2.client.endpoint.adlspostpaydev.dfs.core.windows.net", 
               f"https://login.microsoftonline.com/{tenant_id}/oauth2/token")

print("✅ Connected to Data Lake using Service Principal!")
```

---

### **STEP 6: Read Data from Data Lake**

```python
# Read from Bronze layer
bronze_path = "abfss://bronze@adlspostpaydev.dfs.core.windows.net/sap/kna1/"
df_bronze = spark.read.parquet(bronze_path)

print(f"✅ Loaded {df_bronze.count()} rows from Bronze layer")
df_bronze.show(5)
```

---

### **STEP 7: Write Data to Data Lake**

```python
# Clean data (example transformation)
df_silver = df_bronze.dropna().dropDuplicates()

# Write to Silver layer
silver_path = "abfss://silver@adlspostpaydev.dfs.core.windows.net/customers/"
df_silver.write.mode("overwrite").parquet(silver_path)

print(f"✅ Wrote {df_silver.count()} rows to Silver layer")
```

---

## METHOD 3: Managed Identity (BEST for Production)

### What is Managed Identity?
Azure automatically manages credentials - no passwords to store!

### Requirements:
- Databricks Premium tier
- Workspace must have Azure AD integration enabled

### Step-by-Step:

### **STEP 1: Enable Managed Identity for Databricks Workspace**

```
Azure Portal → Databricks Workspace → Identity

System assigned managed identity: On

Click [Save]

Note the Object (principal) ID
```

---

### **STEP 2: Grant Permissions to Data Lake**

```
Azure Portal → Storage Accounts → adlspostpaydev → Access Control (IAM)

Click [+ Add role assignment]

Role: Storage Blob Data Contributor
Assign access to: Managed Identity
Select: Your Databricks workspace

Click [Save]
```

---

### **STEP 3: Use in Databricks Notebook**

```python
# Configure Spark to use Managed Identity
spark.conf.set("fs.azure.account.auth.type.adlspostpaydev.dfs.core.windows.net", "OAuth")
spark.conf.set("fs.azure.account.oauth.provider.type.adlspostpaydev.dfs.core.windows.net", 
               "org.apache.hadoop.fs.azurebfs.oauth2.MsiTokenProvider")
spark.conf.set("fs.azure.account.oauth2.client.endpoint.adlspostpaydev.dfs.core.windows.net",
               "https://login.microsoftonline.com/<tenant-id>/oauth2/token")

# Read data - No credentials needed!
df = spark.read.parquet("abfss://bronze@adlspostpaydev.dfs.core.windows.net/sap/kna1/")
df.show()

print("✅ Connected using Managed Identity - No passwords!")
```

---

## Alternative: Mount Data Lake (Easier for Repeated Access)

Instead of typing the full path every time, you can "mount" the Data Lake.

### One-Time Mount Configuration:

```python
# Configuration for Service Principal
configs = {
  "fs.azure.account.auth.type": "OAuth",
  "fs.azure.account.oauth.provider.type": "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
  "fs.azure.account.oauth2.client.id": dbutils.secrets.get(scope="data-lake-scope", key="client-id"),
  "fs.azure.account.oauth2.client.secret": dbutils.secrets.get(scope="data-lake-scope", key="client-secret"),
  "fs.azure.account.oauth2.client.endpoint": f"https://login.microsoftonline.com/{dbutils.secrets.get(scope='data-lake-scope', key='tenant-id')}/oauth2/token"
}

# Mount Bronze container
dbutils.fs.mount(
  source = "abfss://bronze@adlspostpaydev.dfs.core.windows.net/",
  mount_point = "/mnt/bronze",
  extra_configs = configs
)

# Mount Silver container
dbutils.fs.mount(
  source = "abfss://silver@adlspostpaydev.dfs.core.windows.net/",
  mount_point = "/mnt/silver",
  extra_configs = configs
)

# Mount Gold container
dbutils.fs.mount(
  source = "abfss://gold@adlspostpaydev.dfs.core.windows.net/",
  mount_point = "/mnt/gold",
  extra_configs = configs
)

print("✅ All containers mounted!")
```

---

### After Mounting, Read/Write is Simple:

```python
# Read from Bronze (mounted path)
df = spark.read.parquet("/mnt/bronze/sap/kna1/")

# Transform data
df_cleaned = df.dropna().dropDuplicates()

# Write to Silver (mounted path)
df_cleaned.write.mode("overwrite").parquet("/mnt/silver/customers/")

# Much simpler than full abfss:// paths!
```

---

### Check What's Mounted:

```python
# List all mounts
dbutils.fs.mounts()

# Output:
# [MountInfo(mountPoint='/mnt/bronze', source='abfss://bronze@adlspostpaydev...', encryptionType=''),
#  MountInfo(mountPoint='/mnt/silver', source='abfss://silver@adlspostpaydev...', encryptionType=''),
#  MountInfo(mountPoint='/mnt/gold', source='abfss://gold@adlspostpaydev...', encryptionType='')]
```

---

### Unmount (if needed):

```python
dbutils.fs.unmount("/mnt/bronze")
dbutils.fs.unmount("/mnt/silver")
dbutils.fs.unmount("/mnt/gold")
```

---

## Complete Example: Bronze → Silver → Gold Pipeline

```python
# ====================================
# 1. CONFIGURE CONNECTION
# ====================================
client_id = dbutils.secrets.get(scope="data-lake-scope", key="client-id")
tenant_id = dbutils.secrets.get(scope="data-lake-scope", key="tenant-id")
client_secret = dbutils.secrets.get(scope="data-lake-scope", key="client-secret")

spark.conf.set("fs.azure.account.auth.type.adlspostpaydev.dfs.core.windows.net", "OAuth")
spark.conf.set("fs.azure.account.oauth.provider.type.adlspostpaydev.dfs.core.windows.net", 
               "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
spark.conf.set("fs.azure.account.oauth2.client.id.adlspostpaydev.dfs.core.windows.net", client_id)
spark.conf.set("fs.azure.account.oauth2.client.secret.adlspostpaydev.dfs.core.windows.net", client_secret)
spark.conf.set("fs.azure.account.oauth2.client.endpoint.adlspostpaydev.dfs.core.windows.net", 
               f"https://login.microsoftonline.com/{tenant_id}/oauth2/token")

print("✅ Connected to Data Lake")

# ====================================
# 2. READ FROM BRONZE (RAW SAP DATA)
# ====================================
bronze_path = "abfss://bronze@adlspostpaydev.dfs.core.windows.net/sap/kna1/"
df_bronze = spark.read.parquet(bronze_path)

print(f"📥 Bronze: Loaded {df_bronze.count()} rows")
df_bronze.printSchema()

# ====================================
# 3. TRANSFORM TO SILVER (CLEANED)
# ====================================
from pyspark.sql.functions import col, trim, upper

df_silver = (df_bronze
    .dropna()  # Remove null rows
    .dropDuplicates(["KUNNR"])  # Remove duplicates by customer ID
    .withColumn("customer_id", col("KUNNR"))  # Rename columns
    .withColumn("customer_name", trim(col("NAME1")))
    .withColumn("country_code", upper(col("LAND1")))
    .select("customer_id", "customer_name", "country_code")  # Select columns
)

# Write to Silver layer
silver_path = "abfss://silver@adlspostpaydev.dfs.core.windows.net/customers/"
df_silver.write.mode("overwrite").parquet(silver_path)

print(f"✅ Silver: Wrote {df_silver.count()} clean rows")

# ====================================
# 4. AGGREGATE TO GOLD (ANALYTICS)
# ====================================
df_gold = (df_silver
    .groupBy("country_code")
    .count()
    .withColumnRenamed("count", "customer_count")
    .orderBy(col("customer_count").desc())
)

# Write to Gold layer
gold_path = "abfss://gold@adlspostpaydev.dfs.core.windows.net/customer_by_country/"
df_gold.write.mode("overwrite").parquet(gold_path)

print(f"✅ Gold: Wrote {df_gold.count()} aggregated rows")
df_gold.show()

# ====================================
# OUTPUT:
# ====================================
# +------------+--------------+
# |country_code|customer_count|
# +------------+--------------+
# |AE          |150           |
# |SA          |120           |
# |US          |90            |
# +------------+--------------+
```

---

## Where is This Configured?

| What | Where | Tool |
|------|-------|------|
| **Service Principal creation** | Azure Active Directory | Azure Portal |
| **Data Lake permissions** | Storage Account → IAM | Azure Portal |
| **Secret storage** | Databricks Secret Scope | Databricks |
| **Connection code** | Databricks Notebook | Databricks |
| **Data reading/writing** | Databricks Notebook | Databricks |

**Bottom Line:** The connection is configured IN DATABRICKS, but permissions are granted IN AZURE PORTAL!

---

## Common Issues & Solutions

### Issue 1: "Forbidden" Error

**Cause:** Service Principal doesn't have permission

**Fix:**
```
Go to Data Lake → Access Control (IAM)
Ensure service principal has "Storage Blob Data Contributor" role
Wait 5-10 minutes for permissions to propagate
```

---

### Issue 2: "No FileSystem" Error

**Cause:** Container doesn't exist or wrong name

**Fix:**
```
Check container name in Azure Portal
Verify URL format: abfss://CONTAINER@ACCOUNT.dfs.core.windows.net/
Make sure using "dfs.core.windows.net" not "blob.core.windows.net"
```

---

### Issue 3: Secrets Not Found

**Cause:** Typo in scope or key name

**Fix:**
```python
# List all scopes
dbutils.secrets.listScopes()

# List keys in a scope
dbutils.secrets.list("data-lake-scope")
```

---

## Security Best Practices

### ✅ DO:
- Use Service Principal or Managed Identity (NOT access keys)
- Store credentials in Databricks Secret Scope
- Use different service principals for dev/test/prod
- Rotate secrets regularly
- Grant least privilege (Reader if read-only, Contributor if read/write)

### ❌ DON'T:
- Hardcode access keys in notebooks
- Share credentials via email/Slack
- Use the same credentials across all environments
- Grant "Owner" role (use "Contributor" instead)

---

## Quick Reference: Connection Methods Comparison

| Method | Security | Setup Difficulty | Production Ready | Cost |
|--------|----------|------------------|------------------|------|
| **Access Keys** | ⚠️ Low | Easy | ❌ NO | Free |
| **Service Principal** | ✅ High | Medium | ✅ YES | Free |
| **Managed Identity** | ✅ Highest | Medium | ✅ YES | Premium tier required |

**Recommendation:** Use Service Principal for most cases, Managed Identity if you have Premium tier.

---

## Summary: How Data Flows

```
1. ADF extracts SAP data
   ↓
2. ADF writes to Data Lake bronze/
   ↓
3. Databricks connects to Data Lake (configured as shown above)
   ↓
4. Databricks reads from bronze/
   ↓
5. Databricks transforms data (PySpark)
   ↓
6. Databricks writes to silver/ and gold/
   ↓
7. Power BI connects to gold/ for reporting
```

**The connection from Databricks to Data Lake is configured IN Databricks using Service Principal authentication!** 🎯
