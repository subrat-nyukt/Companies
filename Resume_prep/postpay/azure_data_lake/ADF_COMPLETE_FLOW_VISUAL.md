# Complete ADF Connection Flow - Visual Guide

## The Complete Journey: From Connector Selection to Integration Runtime

This document shows the **step-by-step screens** you see in Azure Data Factory when connecting to SAP S/4HANA.

---

## Screen 1: Connector Gallery (The Starting Point!)

![Connector Gallery](C:/Users/DELL/.gemini/antigravity/brain/81b93888-477b-44c3-954c-c77f39526cdd/adf_connector_gallery_1771058662478.png)

### What You See:
- **90+ connector options** displayed as cards
- Popular connectors shown first
- Search bar to find specific connectors
- Tabs to filter by category (Database, File, Generic, etc.)

### What platforms can you connect to?

**Databases:**
- Azure SQL Database
- SQL Server
- Oracle
- PostgreSQL
- MySQL
- MongoDB
- Cosmos DB

**SAP Systems:**
- **SAP S/4HANA** ← You click this!
- SAP BW
- SAP HANA

**Cloud Apps:**
- Salesforce
- Dynamics 365
- ServiceNow
- Workday

**Storage:**
- Azure Blob Storage
- Azure Data Lake Gen2
- Amazon S3
- Google Cloud Storage

**APIs:**
- REST API
- OData
- HTTP

**Analytics:**
- Snowflake
- Google BigQuery
- Amazon Redshift
- Databricks

### Action:
**Click on "SAP S/4HANA"** → Click **"Continue"**

---

## Screen 2: SAP Connector Type Selection

![SAP Connector Types](C:/Users/DELL/.gemini/antigravity/brain/81b93888-477b-44c3-954c-c77f39526cdd/sap_connector_types_1771058693958.png)

### What You See:
After selecting SAP, you must choose **which type of SAP connector** to use.

### 3 Options:

#### Option 1: **SAP Table** (Most Common)
- **What it does:** Extracts complete tables from SAP
- **Best for:** Batch loads, historical data
- **Example tables:** KNA1, VBAK, MARA, BSEG
- **Use when:** You need full table extracts daily/weekly

#### Option 2: **SAP CDC** (Change Data Capture)
- **What it does:** Only extracts changed/new records
- **Best for:** Real-time, incremental loads
- **Requires:** SAP ODP (Operational Data Provisioning) framework configured
- **Use when:** You need near-real-time updates

#### Option 3: **SAP OData**
- **What it does:** Access via REST APIs
- **Best for:** CDS views, custom OData services
- **Example:** Sales analytics, custom reports
- **Use when:** You have exposed OData services in SAP

### Action:
**Select "SAP Table"** → Click **"Continue"**

---

## Screen 3: Integration Runtime Setup (Your Current Screenshot!)

![Integration Runtime](C:/Users/DELL/.gemini/antigravity/brain/81b93888-477b-44c3-954c-c77f39526cdd/uploaded_media_1771058568822.png)

### What You See:
Now you configure the **bridge** between SAP (on-premise) and Azure (cloud).

### What is Integration Runtime?
A **Windows software** installed on a machine that can access both:
1. Your SAP server (on-premise/private network)
2. Azure cloud (via HTTPS)

### Fields to Fill:

| Field | Example Value | Purpose |
|-------|---------------|---------|
| **Integration Runtime Name** | `SelfHostedIR-SAP` | Identifier for this bridge |
| **Description** | `Integration Runtime for SAP S/4HANA connection` | Optional notes |
| **VM/Server Details** | `vm-sap-gateway.company.local` | Windows machine where IR installs |

### Action:
1. Fill in the details
2. Click **"Generate Authentication Key"**
3. Copy the key
4. Download Integration Runtime installer
5. Install on Windows machine
6. Paste the key during installation
7. Click **"Continue"**

---

## Screen 4: SAP Connection Details (Next Screen)

After Integration Runtime setup, you'll see:

```
┌─────────────────────────────────────────────┐
│  Configure SAP connection                   │
├─────────────────────────────────────────────┤
│                                             │
│  Server hostname:  [sap.company.com____]   │
│  System number:    [00__]                   │
│  Client ID:        [100_]                   │
│  Language:         [EN ▼]                   │
│                                             │
│  Username:         [RFC_USER___]            │
│  Password:         [••••••••••]             │
│                                             │
│  [🔒 Store in Azure Key Vault]             │
│                                             │
│            [Test Connection]                │
└─────────────────────────────────────────────┘
```

### What Each Field Means:

**Server hostname:** The network address of your SAP server
- Example: `sap-prod.company.com` or `192.168.1.100`

**System number:** SAP system number (2 digits)
- Usually `00`, `01`, or `10`

**Client ID:** SAP mandant/client
- Common values: `100`, `200`, `800`

**Language:** Logon language
- `EN` (English), `DE` (German), `AR` (Arabic)

**Username:** SAP user with table read permissions
- Typically an RFC user with S_TABU_DIS authorization

**Password:** Stored securely in Azure Key Vault

---

## Complete Flow Diagram

```
START → ADF Studio
    ↓
┌─────────────────────────────────────┐
│ Screen 1: New Linked Service        │
│                                     │
│ Connector Gallery (90+ options)    │
│ [Azure SQL] [SQL Server] [SAP]     │
│ [Oracle] [Snowflake] [Blob]        │
│                                     │
│ Click: SAP S/4HANA ─────────────────┤
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Screen 2: SAP Connector Type        │
│                                     │
│ ○ SAP Table (full extract)         │
│ ○ SAP CDC (deltas only)            │
│ ○ SAP OData (APIs)                 │
│                                     │
│ Select: SAP Table ──────────────────┤
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Screen 3: Integration Runtime       │  ← YOUR SCREENSHOT!
│                                     │
│ Name: SelfHostedIR-SAP             │
│ Description: ...                   │
│ VM: vm-sap-gateway.local           │
│                                     │
│ [Generate Auth Key] ────────────────┤
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Screen 4: SAP Connection Details    │
│                                     │
│ Server: sap.company.com            │
│ System: 00, Client: 100            │
│ Username/Password                  │
│                                     │
│ [Test Connection] ──────────────────┤
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Screen 5: Review & Create           │
│                                     │
│ ✅ Integration Runtime: Ready       │
│ ✅ SAP Connection: Verified         │
│                                     │
│ [Create Linked Service] ────────────┤
└─────────────────────────────────────┘
    ↓
  DONE! Now you can create pipelines
```

---

## Summary

**You asked for the page BEFORE Integration Runtime setup - here it is!**

### The Missing Pieces:

1. **Screen 1 (Connector Gallery):** Shows ALL 90+ platforms ADF can connect to
2. **Screen 2 (SAP Connector Types):** Choose between SAP Table, CDC, or OData
3. **Screen 3 (Your screenshot):** Integration Runtime setup
4. **Screen 4:** SAP connection details

Now you understand the complete flow from start to finish!

---

## Practice in the Simulator

The interactive simulator (`adf_studio_simulator.html`) follows this exact flow. Open it to practice:

1. See the connector gallery
2. Select SAP
3. Choose connector type
4. Configure Integration Runtime
5. Set up SAP connection
6. Test and deploy

This gives you hands-on experience with the actual ADF workflow!
