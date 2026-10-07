# Data Ingestion Flow: How Raw Data Arrives

In a modern Azure Data Architecture, data does not "magically" appear in Databricks. It follows a specific path from your source systems to storage, and then to Databricks.

## The Standard Architecture: Medallion Architecture

The industry standard is to treat **Azure Data Lake Storage (ADLS Gen2)** as the "hard drive" and **Databricks** as the "processor".

```mermaid
graph LR
    A[Source Systems<br/>(App, SQL DB, APIs)] -->|Ingestion Tool<br/>(ADF / Kafka)| B[Azure Data Lake<br/>(ADLS Gen2)]
    B -->|Spark Read| C[Databricks<br/>(Bronze Tables)]
    C -->|Cleanse| D[Databricks<br/>(Silver Tables)]
    D -->|Aggregates| E[Databricks<br/>(Gold Tables)]
    E -->|Connector| F[Power BI<br/>(Dashboards)]
```

### 1. The Landing Zone (ADLS Gen2)
Your raw data (CSVs, JSONs, Parquet files) lands here first.
*   **Who puts it here?** 
    *   **Azure Data Factory (ADF)**: Scheduled jobs that copy data from your SQL databases or APIs every night.
    *   **Event Hubs / Kafka**: Streaming data (e.g., real-time transaction logs).
    *   **Manual Upload**: You uploading a CSV via Storage Explorer (for ad-hoc analysis).

### 2. Mounting to Databricks
Databricks doesn't store data inside itself; it "mounts" or connects to the Data Lake.
*   When you run `spark.read.csv("/mnt/datalake/raw/...")`, Databricks is reaching out to ADLS to read the file.
*   **Unity Catalog (New Standard)**: Instead of mounting, you define "External Locations". You tell Databricks, "Hey, this folder in ADLS is now a Table."

### 3. The Layers

*   **Bronze (Raw)**: This is an exact copy of the data in ADLS. If the ADLS file has a typo, the Bronze table has a typo.
    *   *Example*: `raw_instalment_plans`
*   **Silver (Cleaned)**: You run a Databricks job to remove duplicates, fix dates, and rename columns.
    *   *Example*: `cleaned_instalment_plans`
*   **Gold (Business)**: Aggregated data ready for Power BI or ML.
    *   *Example*: `gold_customer_risk_profile` (This is what we built earlier!)

## Summary for Your Project
1.  **Raw Data** arrives in **Azure Data Lake** (usually via ADF).
2.  **Databricks** reads it and registers it as **Bronze Tables**.
3.  Your **Feature Engineering Script** (SQL) turns Bronze -> Gold.
4.  Your **ML Model** reads Gold -> Predicts -> Writes Results.
5.  **Power BI** reads Results.
