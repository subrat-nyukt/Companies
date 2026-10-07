# Where is Pipeline Scheduling Configured? (ADF vs Data Lake)

## Quick Answer: **Azure Data Factory (ADF)** ✅

The schedule you saw (e.g., "Daily at 2:00 AM") is configured in **Azure Data Factory**, NOT in Data Lake.

---

## Why ADF, Not Data Lake?

### Data Lake = Storage Only 🗄️
```
Azure Data Lake Gen2 is like a hard drive:
- Stores files
- Organizes folders (bronze, silver, gold)
- Provides access control
- NO EXECUTION CAPABILITY

Think: Your external hard drive doesn't "run" anything,
      it just stores files!
```

### Azure Data Factory = Execution Engine ⚙️
```
Azure Data Factory is like a robot:
- Executes tasks (copy data, transform)
- Runs on schedule
- Monitors success/failure
- Sends alerts

Think: A robot that wakes up at 2 AM every night,
      grabs data from SAP, and puts it in Data Lake!
```

---

## The Roles Explained

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────┘

SAP S/4HANA              Azure Data Factory         Data Lake Gen2
(Source)                 (The Scheduler!)           (Destination)
    │                           │                         │
    │                           │                         │
    │                    ┌──────┴──────┐                 │
    │                    │  ⏰ TRIGGER  │                 │
    │                    │  Daily 2 AM  │                 │
    │                    └──────┬──────┘                 │
    │                           │                         │
    │   "Get data from SAP"     │                         │
    │<──────────────────────────┤                         │
    │                           │                         │
    │   Returns data            │                         │
    ├──────────────────────────>│                         │
    │                           │                         │
    │                           │  "Store in bronze/"     │
    │                           ├────────────────────────>│
    │                           │                         │
    │                           │      Stored ✓           │
    │                           │<────────────────────────┤
    
    Does nothing              RUNS THE                 Just receives
    automatically            SCHEDULE!                 and stores data
```

---

## Where Exactly in ADF?

### Step 1: Open Azure Data Factory Studio
```
Azure Portal → Data Factory → adf-postpay-dev → Author & Monitor
```

### Step 2: Go to "Manage" Section
```
Left sidebar:
- ✏️ Author    ← Design pipelines here
- 🔧 Manage    ← ⭐ SCHEDULE IS HERE!
- 📊 Monitor   ← View run history
```

### Step 3: Click "Triggers"
```
Manage Section:
├── Linked Services
├── Integration Runtimes
├── 🕐 Triggers  ← ⭐ SCHEDULE YOUR PIPELINE HERE!
└── Parameters
```

### Step 4: Create a Schedule Trigger
```
Triggers → + New → Trigger Schedule

Name: Daily-SAP-Extract
Type: Schedule
Recurrence: Daily
Time: 02:00 AM
Time Zone: (UTC+04:00) Abu Dhabi
Start: 2026-02-15
End: None (run forever)

✅ Save
```

---

## The Complete ADF Scheduling Interface

```
┌─────────────────────────────────────────────────────────────┐
│ Azure Data Factory Studio                                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Manage > Triggers                                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Trigger Name: Daily-SAP-Extract                      │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ Type:         ○ Event    ● Schedule    ○ Tumbling   │  │
│  │                                                       │  │
│  │ Recurrence:   ○ Once     ● Daily       ○ Weekly     │  │
│  │               ○ Monthly  ○ Hourly                    │  │
│  │                                                       │  │
│  │ Time:         [02:00] AM                             │  │
│  │                                                       │  │
│  │ Time Zone:    [(UTC+04:00) Abu Dhabi, Muscat]       │  │
│  │                                                       │  │
│  │ Start Date:   [2026-02-15]                           │  │
│  │ End Date:     [No end date - run forever]           │  │
│  │                                                       │  │
│  │ Pipelines to Run:                                    │  │
│  │   ✓ SAP_to_DataLake_KNA1                            │  │
│  │   ✓ SAP_to_DataLake_VBAK                            │  │
│  │                                                       │  │
│  │           [Test]  [Save]  [Activate]                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Types of Triggers in ADF

### 1. **Schedule Trigger** (Most Common)
```
When: Time-based
Example: "Every day at 2 AM"

Use Case:
- Daily SAP data extraction
- Nightly reports
- Weekly aggregations
```

### 2. **Event Trigger**
```
When: File arrives in storage
Example: "When a new CSV file appears in bronze/incoming/"

Use Case:
- Process files as they arrive
- Real-time data ingestion
- File-driven workflows
```

### 3. **Tumbling Window Trigger**
```
When: Fixed-size time windows
Example: "Every 6 hours, process the last 6 hours of data"

Use Case:
- Incremental loads
- CDC (Change Data Capture)
- Time-series processing
```

---

## What Each System Does

| Component | Scheduling? | Execution? | Storage? |
|-----------|-------------|------------|----------|
| **SAP S/4HANA** | ❌ | ❌ (source only) | ✅ (transactional data) |
| **Azure Data Factory** | ✅ ⭐ **YES** | ✅ **YES** | ❌ |
| **Data Lake Gen2** | ❌ | ❌ | ✅ (analytical data) |
| **Databricks** | ✅ (has its own scheduler) | ✅ (processes data) | ❌ |
| **Power BI** | ✅ (has refresh schedules) | ❌ (reads only) | ❌ |

---

## Common Confusion

### ❌ WRONG: "Schedule in Data Lake"
```
"I want to schedule my Data Lake to pull data from SAP every night"

Data Lake CAN'T do this!
It's just storage - no brain!
```

### ✅ CORRECT: "Schedule in ADF, store in Data Lake"
```
"I want to schedule my ADF pipeline to pull data from SAP 
every night and store it in Data Lake"

ADF executes the schedule, Data Lake receives the data!
```

---

## Real-World Analogy

Think of it like **Amazon delivery**:

| Azure Service | Real World Equivalent |
|---------------|----------------------|
| **SAP** | Warehouse (has products) |
| **ADF + Schedule** | **Delivery truck with a schedule** (picks up at 2 AM) |
| **Data Lake** | Your home (receives packages) |

**Questions:**
- **Q:** Does your home (Data Lake) schedule the delivery truck?
- **A:** NO! The delivery company (ADF) has a schedule.

- **Q:** Does your home (Data Lake) drive to the warehouse?
- **A:** NO! The truck (ADF) does the work.

- **Q:** What does your home (Data Lake) do?
- **A:** It **receives and stores** packages!

**Same concept:**
- Data Lake doesn't schedule anything
- Data Lake doesn't execute anything
- Data Lake **receives and stores** data that ADF delivers

---

## Where to Configure Scheduling: Step-by-Step

### Azure Portal Workflow:

```
1. Go to Azure Portal
   ↓
2. Open your Data Factory: "adf-postpay-dev"
   ↓
3. Click "Author & Monitor" (opens ADF Studio)
   ↓
4. Click "Manage" tab (left sidebar)
   ↓
5. Click "Triggers" under Connections
   ↓
6. Click "+ New" to create a new trigger
   ↓
7. Configure:
   - Name: Daily-SAP-Extract
   - Type: Schedule
   - Recurrence: Daily at 02:00 AM
   ↓
8. Associate with your pipeline:
   - Select "SAP_to_DataLake_KNA1"
   ↓
9. Click "Activate" toggle to turn it ON
   ↓
10. ✅ DONE! Pipeline will run every night at 2 AM
```

---

## What About Databricks Scheduling?

**Databricks ALSO has its own scheduler!**

```
Your Complete Architecture:

1. ADF Schedule (2:00 AM)
   → Extract from SAP
   → Land in bronze/
   
2. Databricks Schedule (3:00 AM)  ← Separate scheduler!
   → Read from bronze/
   → Clean → Write to silver/
   → Aggregate → Write to gold/

3. Power BI Refresh (4:00 AM)  ← Another scheduler!
   → Read from gold/
   → Update dashboard
```

**Each tool has its own scheduler:**
- ADF schedules data **extraction**
- Databricks schedules data **transformation**
- Power BI schedules report **refresh**

---

## How to Check Active Schedules

### In ADF:
```
ADF Studio → Manage → Triggers

Active Triggers:
✅ Daily-SAP-Extract     | Schedule: Daily 02:00 | Status: Active
✅ Hourly-Incremental    | Schedule: Hourly      | Status: Active
❌ Weekly-Full-Load      | Schedule: Sunday 00:00| Status: Inactive
```

### In Databricks:
```
Databricks Workspace → Workflows → Jobs

Active Jobs:
✅ Bronze-to-Silver-ETL  | Schedule: Daily 03:00 | Status: Active
✅ Silver-to-Gold-Agg    | Schedule: Daily 03:30 | Status: Active
```

---

## Summary

### The Scheduling is in: **Azure Data Factory (ADF)** ⭐

| Question | Answer |
|----------|--------|
| Where do I set "Daily at 2 AM"? | **ADF → Manage → Triggers** |
| Does Data Lake have scheduling? | **NO** - it's just storage |
| What does Data Lake do? | Stores the files that ADF writes |
| Can I schedule in SAP? | NO - SAP is just the source |
| Who actually runs the pipeline? | **ADF** - the execution engine |

### Remember:
```
ADF = The Brain (schedules and executes)
Data Lake = The Storage (receives and stores)
SAP = The Source (provides data when asked)
```

The schedule configuration you saw in the demo is 100% happening in **Azure Data Factory**, not in Data Lake! 🎯
