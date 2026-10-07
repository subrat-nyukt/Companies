# SAP S/4HANA to Azure Databricks: The Data Flow

This is how data moves from your ERP (SAP) to your analytics platform (Databricks).

## The Architecture Diagram

```mermaid
graph TD
    subgraph "On-Premises / Private Cloud"
        SAP[SAP S/4HANA<br/>(Source System)]
        SHIR[Self-Hosted Integration Runtime<br/>(Security Gateway)]
    end

    subgraph "Azure Cloud"
        ADF[Azure Data Factory<br/>(The mover)]
        ADLS[Azure Data Lake Gen2<br/>(The Storage / Landing Zone)]
        DB[Azure Databricks<br/>(The Brain / Processing)]
    end

    SAP -->|1. Extraction (ODP/CDS Views)| SHIR
    SHIR -->|2. Secure Transfer| ADF
    ADF -->|3. Writes Parquet Files| ADLS
    ADLS -->|4. Reads/Mounts| DB
```

## Detailed Steps

### 1. The Source: SAP S/4HANA
*   Your data (Customer Master, Sales Orders, FI-GL) sits here.
*   We don't query SAP directly from Databricks because it would slow down the ERP system.

### 2. The Bridge: Azure Data Factory (ADF)
*   **Role**: The "Truck" that moves data.
*   **Connector**: ADF has a specialized **SAP CDC Connector** or **SAP Table Connector**.
*   **Frequency**: You set up a "Pipeline" to run every night (Batch) or every hour.
*   **Security**: If your SAP is private, ADF uses a **Self-Hosted Integration Runtime (SHIR)** installed on a VM near SAP to safely tunnel the data out.

### 3. The Destination: Azure Data Lake (ADLS Gen2)
*   **Role**: The "Warehouse" where the truck unloads.
*   **This is where raw data sits.**
*   ADF saves the SAP data here as **Parquet files** or **Appended CSVs**.
    *   *Path example*: `abfss://raw-data@datalake.dfs.core.windows.net/sap/sales_orders/2026/02/14/file.parquet`

### 4. The Processor: Databricks
*   **Role**: The "Factory" that turns raw materials into products.
*   Databricks **mounts** the Data Lake.
*   It looks at the new files in ADLS and runs your logical transformations (SQL/Python).
*   It saves the clean result as **Delta Tables** (the ones you query in Power BI).

## Why this way?
*   **Performance**: SAP is optimized for *writing* transactions, not *reading* millions of rows for analysis. Copying it to ADLS creates a read-optimized copy.
*   **Cost**: Storing massive history in ADLS is cheap. Storing it in SAP HANA memory is expensive.
