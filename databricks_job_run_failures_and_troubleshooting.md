# Databricks Job Run Failures & Troubleshooting Guide

> **Overview:** In Apache Spark and Databricks Workflows, job failures and performance degradation generally fall into 7 main categories: **Memory/OOM**, **Data Skew**, **Shuffle & Disk I/O**, **Infrastructure & Cloud Limits**, **Delta Lake Concurrency**, **Code/Serialization**, and **Orchestration/Auth**.

---

## Quick Reference: Top Databricks Failure Matrix

| Failure Category | Common Error / Exception | Primary Root Cause | Instant Fix / Solution |
|---|---|---|---|
| **Driver OOM** | `java.lang.OutOfMemoryError: Java heap space` | `.collect()`, `.toPandas()`, or huge broadcast join | Increase Driver size, use `.take()` or PySpark Pandas API (`pyspark.pandas`) |
| **Executor OOM** | `Container killed by YARN/K8s for exceeding memory limits` | Unbalanced memory distribution, memory leak in Python UDF | Increase `spark.executor.memoryOverhead` or worker instance RAM |
| **Data Skew** | Job stuck at 99% for hours ("straggler tasks") | Non-uniform join/group key distribution (e.g. `NULL`s, default keys) | Salting, AQE Skew Join (`spark.sql.adaptive.skewJoin.enabled`), filter NULLs |
| **Shuffle Failure** | `FetchFailedException: Failed to connect to worker` | Worker node lost/preempted or shuffle payload too large | Enable AQE, increase `spark.shuffle.service.enabled` / `spark.redaction.regex` |
| **Disk Exhaustion** | `No space left on device` (Local SSD full) | Massive shuffle spill or un-optimized temp files | Increase local EBS/SSD storage, enable auto-scaling storage |
| **Delta Concurrency** | `ConcurrentAppendException` | Concurrent writes to same Delta table partition | Use partitioning, optimize write strategy, or enable Row-Level Concurrency |
| **Missing Delta Files** | `java.io.FileNotFoundException` | `VACUUM` deleted files being read by long-running query | Increase `spark.databricks.delta.vacuum.parallelDelete.enabled` & retention hours |
| **Spot Eviction** | `The executor was removed...` | Cloud provider reclaimed Spot instance | Use On-Demand for Driver, set Hybrid/Fallback Spot-to-On-Demand workers |
| **PySpark UDF Error** | `PicklingError` / `Python worker exited unexpectedly` | Serialization failure or non-vectorized Python code | Convert to Native PySpark functions, Spark SQL, or Pandas UDFs (Arrow) |

---

## 1. Memory & Out-of-Memory (OOM) Issues

### Problem 1.1: Driver Out of Memory (`java.lang.OutOfMemoryError`)

#### Symptom & Error Log
```text
Py4JJavaError: An error occurred while calling o123.collectToPython.
java.lang.OutOfMemoryError: Java heap space
    at java.io.ByteArrayOutputStream.grow(ByteArrayOutputStream.java:118)
```

#### Root Cause
The Driver node coordinates the cluster, holds the SparkContext, builds query plans, and aggregates results. Driver OOM occurs when data is pulled from distributed executors onto the single Driver node beyond its JVM heap size.

#### Code Trigger Example
```python
# ❌ BAD: Pulling millions of rows from worker nodes to the Driver
df_huge = spark.table("telemetry_logs_100M_rows")
pdf = df_huge.toPandas()  # Tries to fit 100M rows in Driver RAM
data = df_huge.collect()   # Brings all partitions to Driver heap
```

#### How to Debug
1. Open **Spark UI** → **Executors Tab**. Check **Driver** memory usage.
2. Look at **Storage Tab** to check if large dataframes/RBMs are cached in memory on the Driver.

#### Mitigation Strategy
```python
# ✅ GOOD: Sample or write directly to storage without pulling to Driver
df_sample = df_huge.sample(fraction=0.01).toPandas()

# ✅ GOOD: Save directly from distributed workers to S3/ADLS/Delta
df_huge.write.format("delta").saveAsTable("output_table")

# ✅ GOOD: Increase Driver node size in Databricks Cluster configuration (e.g. from 16GB to 64GB RAM)
```

---

### Problem 1.2: Executor Out of Memory (Container Killed)

#### Symptom & Error Log
```text
ERROR TaskSetManager: Task 14 in stage 3.0 failed 4 times; aborting job
ExecutorLostFailure (executor 5 exited caused by one of the running tasks) 
Reason: Container killed by YARN for exceeding memory limits. 10.4 GB of 10.0 GB physical memory used.
```

#### Root Cause
Spark Executors perform actual data processing tasks. An executor crashes when JVM heap memory or off-heap (overhead) memory exceeds the instance limits due to:
- Large in-memory aggregations or joins.
- High memory consumption in Python worker processes (when using standard Python UDFs).

#### Mitigation Strategy
1. **Increase Memory Overhead:**
   ```sql
   SET spark.executor.memoryOverhead = 2048m; -- Increases off-heap RAM for Python UDFs/C-libraries
   ```
2. **Repartition Data:** Reduce partition size so each task processes smaller chunks (target partition size: **100MB–200MB**).
3. **Use Pandas UDFs (PyArrow):** Vectorized operations consume significantly less memory than raw Python `map`/`apply`.

---

## 2. Data Skew & Partitioning Issues

### Problem 2.1: Data Skew (The 99% Job Hang)

#### Symptom
A Spark stage completes 999 out of 1000 tasks quickly, but the last 1 task takes hours or eventually fails with an OOM error.

```
[===================================================>     ] 999/1000 tasks complete (Stage 4)
```

#### Root Cause
Data is unevenly distributed across partitions based on the join or group key. For instance, if 80% of log entries have `user_id = NULL` or a dummy value like `"N/A"`, all those rows end up on a single executor task during a shuffle.

#### Code Trigger Example
```python
# ❌ BAD: Joining on a column containing millions of NULLs or default values
df_orders.join(df_users, on="user_id", how="inner")
```

#### How to Debug
1. Go to **Spark UI** → **Stages** → Click active stage.
2. Check the **Summary Metrics** table:
   - Compare **Min**, **Median**, and **Max** task durations.
   - If **Max task duration** is 45 minutes while **Median** is 2 seconds, you have severe **Data Skew**.

#### Mitigation Strategy

##### Solution A: Enable Adaptive Query Execution (AQE) Skew Join (Databricks Default)
```python
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionFactor", "5")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes", "256mb")
```

##### Solution B: Salting Strategy (Manual Fix for Extremes)
```python
import pyspark.sql.functions as F

# Add a random salt (0-9) to the left table for skewed key
df_skewed = df_orders.withColumn(
    "salted_key",
    F.concat(F.col("user_id"), F.lit("_"), F.floor(F.rand() * 10))
)

# Explode the right table to match all possible salt keys
df_users_exploded = df_users.withColumn("salt_array", F.array([F.lit(i) for i in range(10)])) \
                            .withColumn("exploded_salt", F.explode("salt_array")) \
                            .withColumn("salted_key", F.concat(F.col("user_id"), F.lit("_"), F.col("exploded_salt")))

# Perform join on salted key
df_joined = df_skewed.join(df_users_exploded, on="salted_key")
```

---

### Problem 2.2: Small File Problem (Fragmented Datasets)

#### Symptom
Job execution becomes extremely slow during file reading or metadata operations. Delta Lake operations like `MERGE` or `UPDATE` take hours on small datasets.

#### Root Cause
Continuous streaming writes or frequent micro-batch jobs create thousands of tiny files (e.g. 1KB to 2MB each). Spark spends more time handling file metadata and open/close I/O handles than reading actual data.

#### Mitigation Strategy
```sql
-- Run Delta Auto-Optimize and Compact on the table
OPTIMIZE my_delta_table ZORDER BY (transaction_date);

-- Enable Auto-Optimize settings at session or table level
ALTER TABLE my_delta_table SET TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);
```

---

## 3. Infrastructure & Cloud Level Issues

### Problem 3.1: Spot Instance Preemption (Cloud Worker Losses)

#### Symptom
```text
WARN TaskSetManager: Lost task 42.0 in stage 2.0 (TID 123, ip-10-0-1-45.ec2.internal, executor 3): 
ExecutorLostFailure (executor 3 exited caused by one of the running tasks) Reason: Slave lost
```

#### Root Cause
Using 100% Spot instances for worker nodes in AWS/Azure/GCP allows cloud providers to reclaim VMs with a 2-minute notification when capacity is needed elsewhere.

#### Mitigation Strategy
1. **Never use Spot instances for Driver nodes:** Always use **On-Demand** for Driver. If the Driver dies, the whole job dies.
2. **Use Hybrid Driver/Worker Configuration:**
   - Driver: On-Demand
   - Workers: 30% On-Demand, 70% Spot (or Fallback to On-Demand enabled in cluster config).

---

### Problem 3.2: Cluster IP / VNet Address Exhaustion

#### Symptom
Job fails during cluster launch phase before executing any code:
```text
ClusterFailedException: Cloud provider launch failure: SubnetHasNoFreeIPs - The subnet 'subnet-xyz' has no free IP addresses.
```

#### Root Cause
Auto-scaling clusters configured to spawn dozens of worker nodes exhaust available private IP addresses in the assigned cloud Subnet / Virtual Network (VNet).

#### Mitigation Strategy
- Expand CIDR block size of Databricks Subnets in AWS VPC / Azure VNet.
- Implement Databricks **Single Node** or limit `max_workers` in Auto-scaling limits.

---

## 4. Shuffle & Disk I/O Bottlenecks

### Problem 4.1: `FetchFailedException` & Shuffle Corruption

#### Symptom
```text
org.apache.spark.shuffle.FetchFailedException: Failed to connect to worker-node-12/10.0.2.14:7337
    at org.apache.spark.storage.ShuffleBlockFetcherIterator.throwFetchFailed(ShuffleBlockFetcherIterator.scala:752)
```

#### Root Cause
During wide-transformation queries (`JOIN`, `GROUP BY`, `DISTINCT`), Executors write intermediate shuffle files to local disk and exchange them over the network. If a worker node crashes, experiences high network latency, or runs out of local disk space, fetching task partitions fails.

#### Mitigation Strategy
```sql
-- Increase network timeout parameters
SET spark.core.connection.ack.wait.timeout = 1200s;
SET spark.network.timeout = 800s;

-- Enable Adaptive Query Execution to reduce shuffle partitions dynamically
SET spark.sql.adaptive.enabled = true;
SET spark.sql.adaptive.coalescePartitions.enabled = true;
```

---

### Problem 4.2: Local SSD Disk Exhaustion (`No space left on device`)

#### Symptom
```text
java.io.IOException: No space left on device
    at java.io.FileOutputStream.writeBytes(Native Method)
    at org.apache.spark.storage.DiskBlockObjectWriter.write(DiskBlockObjectWriter.scala:240)
```

#### Root Cause
Large shuffle operations or temporary cache operations spill heavily to local disk storage (`/local_disk0`). If the node's local EBS/Managed Disk storage is small (e.g. default 30GB), it fills up quickly.

#### Mitigation Strategy
- Enable **EBS Autoscaling** / **Auto-attaching SSD Storage** in cluster config.
- Avoid unnecessary `.cache()` or `.persist()` calls without clearing them (`.unpersist()`).

---

## 5. Delta Lake & Concurrency Failures

### Problem 5.1: `ConcurrentAppendException` / Optimistic Concurrency Failure

#### Symptom
```text
io.delta.exceptions.ConcurrentAppendException: Files were added to partition [year=2024, month=08] by a concurrent update. Please try the operation again.
```

#### Root Cause
Delta Lake uses **Optimistic Concurrency Control (OCC)**. If Job A and Job B write/update the same target table or partition simultaneously, one transaction wins and commits, while the other fails to prevent data corruption.

#### Mitigation Strategy
1. **Partition Writes:** Ensure concurrent jobs write to strictly mutually exclusive partitions.
2. **Enable Row-Level Concurrency** (Databricks Runtime 13.3+ / Liquid Clustering):
   ```sql
   ALTER TABLE my_table SET TBLPROPERTIES ('delta.enableRowLevelConcurrency' = 'true');
   ```
3. **Add Retries in Databricks Job Workflows:** Configure Task level `Retries = 3` with backoff.

---

### Problem 5.2: `java.io.FileNotFoundException` (Stale Metadata / Vacuum Issue)

#### Symptom
```text
java.io.FileNotFoundException: s3://my-bucket/delta/table/_delta_log/00000000000000000100.json 
File does not exist.
```

#### Root Cause
A long-running query (Job A) reads from a Delta table version. Meanwhile, Job B runs `VACUUM my_table RETAIN 0 HOURS`, removing old underlying Parquet data files that Job A is still trying to scan.

#### Mitigation Strategy
- Never run `VACUUM` with 0 hours retention in production. Keep the default retention period (**7 days** / 168 hours).
- Avoid running aggressive `VACUUM` jobs concurrently with heavy analytics reading workloads.

---

## 6. Code, UDF & Dependency Issues

### Problem 6.1: Serialization Failures (`PicklingError` / `NotSerializableException`)

#### Symptom
```text
org.apache.spark.SparkException: Task not serializable
Caused by: java.io.NotSerializableException: org.apache.hadoop.fs.Path
```

#### Root Cause
When executing PySpark code, functions passed to executors (like standard Python functions or UDFs) reference objects instantiated outside the function scope that cannot be serialized (pickled) and shipped across the network to workers (e.g., database connection objects, open file handles, thread locks).

#### Code Trigger Example
```python
# ❌ BAD: Referencing un-serializable connection object inside PySpark transformation
db_connection = create_sql_connection()  # Connection object cannot be pickled

def enrich_row(row):
    return db_connection.query(row.id)   # Fails with NotSerializableException!

df.rdd.map(enrich_row).collect()
```

#### Mitigation Strategy
```python
# ✅ GOOD: Instantiate connections inside worker partitions using mapPartitions
def enrich_partition(partition):
    db_connection = create_sql_connection()  # Created locally on executor
    for row in partition:
        yield db_connection.query(row.id)
    db_connection.close()

df.rdd.mapPartitions(enrich_partition)
```

---

### Problem 6.2: Python Library Dependency Mismatches

#### Symptom
```text
ModuleNotFoundError: No module named 'scikit-learn'
    at org.apache.spark.api.python.PythonRunner.scalasimple(PythonRunner.scala:108)
```

#### Root Cause
A Python package is installed on the Driver node (via `%pip install` in a single notebook cell) but is missing on worker nodes, or different worker nodes have conflicting version dependencies.

#### Mitigation Strategy
- Install libraries at the **Cluster Level** via Databricks Libraries UI or init scripts.
- Declare dependencies directly in **Databricks Workflows / Job Configuration**:
  ```json
  "dependent_libraries": [
    { "pypi": { "package": "scikit-learn==1.3.0" } }
  ]
  ```

---

## 7. Databricks Workflows & Orchestration Failures

### Problem 7.1: Service Principal / Secret Token Expiration

#### Symptom
A scheduled job that ran fine for 90 days suddenly fails:
```text
com.databricks.backend.common.customexception.DatabricksServiceException: 
Invalid Access Token / Unauthorized (401)
```

#### Root Cause
The OAuth token, Personal Access Token (PAT), or Azure Service Principal secret configured in the Databricks Secret Scope or job owner account has expired.

#### Mitigation Strategy
- Use **Managed Identities** (Azure) or **AWS IAM Roles for Service Accounts (IRSA)** instead of hardcoded PAT tokens.
- Assign Job Ownership to a **Service Principal**, not an individual user account (which fails if the employee leaves the company).

---

### Problem 7.2: Maximum Concurrent Runs Exceeded

#### Symptom
```text
JobRunSkippedException: Job run skipped because maximum concurrent runs limit (1) reached.
```

#### Root Cause
The previous instance of a scheduled job ran longer than its schedule interval (e.g. scheduled every 10 mins, but the previous run took 15 mins). By default, Databricks prevents concurrent runs of the same job.

#### Mitigation Strategy
- Set **Concurrency Limit** to appropriate value or increase alert thresholds.
- Optimize job query execution time using Delta Lake Z-Ordering/Liquid Clustering.
- Configure **Timeout limits** on the Job level so hanging runs terminate automatically.

---

## Summary Checklist for Databricks Production Jobs

```
[ ] Driver sizing: Use at least 4 cores / 16GB RAM for production Driver nodes.
[ ] Spot Instance Strategy: On-Demand for Driver, Spot with Fallback for Workers.
[ ] Enable AQE: Ensure spark.sql.adaptive.enabled = true is active.
[ ] Delta Lake Maintenance: Run OPTIMIZE and Auto-Compact regularly.
[ ] Avoid .collect() / .toPandas() on un-sampled large DataFrames.
[ ] Set Job Timeouts & Retries in Databricks Workflow task settings.
[ ] Use Service Principal ownership for production Workflows.
```
