# End-to-End Data Architecture: SAP S/4HANA to Power BI

This document details the complete Enterprise-grade data architecture from SAP S/4HANA to Power BI using the Azure ecosystem.

## High-Level Architecture Diagram

```mermaid
graph LR
    subgraph "On-Premises / Private Cloud"
        SAP[SAP S/4HANA<br/>(ERP Source)]
        SHIR[Self-Hosted Integration Runtime<br/>(Secure Gateway)]
    end

    subgraph "Azure Data Platform"
        KV[Azure Key Vault<br/>(Stores Credentials)]
        
        subgraph "Ingestion & Orchestration"
            ADF[Azure Data Factory<br/>(Pipelines)]
        end

        subgraph "Storage (ADLS Gen2)"
            Bronze[(Bronze Layer<br/>Raw Parquet)]
            Silver[(Silver Layer<br/>Clean Delta)]
            Gold[(Gold Layer<br/>Aggregated Delta)]
        end

        subgraph "Processing (Databricks)"
            DB_Eng[Databricks Engineering<br/>(Spark Jobs)]
            DB_SQL[Databricks SQL<br/>(Serverless Warehouse)]
        end
    end

    subgraph "Consumption"
        PBI[Power BI Service<br/>(Dashboards)]
        User((End User))
    end

    %% Data Flow Connections
    SAP -->|OData / CDC| SHIR
    SHIR -->|Encrypted Tunnel| ADF
    ADF -->|Copy Activity| Bronze
    
    %% Key Vault Access
    ADF -.->|Get Secrets| KV
    DB_Eng -.->|Get Secrets| KV

    %% Processing Flow
    Bronze -->|Read/Process| DB_Eng
    DB_Eng -->|Write| Silver
    Silver -->|Refine| DB_Eng
    DB_Eng -->|Write| Gold
    
    %% Consumption Flow
    Gold -->|Serve| DB_SQL
    DB_SQL -->|DirectQuery / Import| PBI
    PBI -->|View| User
```

## detailed Component Breakdown

### 1. Source System: SAP S/4HANA
*   **What it is**: The system of record for your business transactions (Sales, Finance, Inventory).
*   **Connection Method**: 
    *   **SAP CDC Connector (Change Data Capture)**: Recommended. Only pulls *changed* records (Deltas) instead of the full table every night.
    *   **SAP Table Connector**: Pulls full tables. Good for small tables.

### 2. The Gateway: Self-Hosted Integration Runtime (SHIR)
*   **Why needed?**: SAP is usually behind a firewall. Azure Data Factory (ADF) is in the public cloud. They can't talk directly.
*   **Function**: You install SHIR on a Windows VM inside your network. It acts as a bridge, initiating an outbound connection to Azure to transfer data securely.

### 3. Ingestion: Azure Data Factory (ADF)
*   **Role**: Orchestrator and Mover.
*   **Action**: Runs valid pipelines (e.g., at 2:00 AM) to copy data from SAP via SHIR to the Data Lake.
*   **Security**: Uses **Azure Key Vault** to retrieve SAP passwords safely. It never hardcodes passwords.

### 4. Storage: Azure Data Lake Gen2 (ADLS)
*   **Role**: The "filesystems" for your data.
*   **Structure (Medallion Architecture)**:
    *   **Bronze Container**: Raw files (Parquet/JSON) exactly as they came from SAP. Historic archive.
    *   **Silver Container**: Cleaned data (Duplicates removed, dates standardized, nulls handled). Stored as **Delta Lake** format.
    *   **Gold Container**: Business-level aggregates (KPIs, Star Schemas) ready for reporting. Stored as **Delta Lake** format.

### 5. Processing: Azure Databricks
*   **Role**: The "Brain" that transforms data.
*   **Activity**:
    *   Mounts ADLS Gen2.
    *   Runs Python/SQL notebooks to read Bronze -> Create Silver.
    *   Runs SQL transformations to read Silver -> Create Gold.
    *   **Unity Catalog**: Manages permissions (who can see which table).

### 6. Serving: Databricks SQL & Power BI
*   **Databricks SQL Warehouse**: A specialized compute engine optimized for SQL queries (faster than normal clusters).
*   **Power BI**: 
    *   Connects to Databricks SQL Warehouse.
    *   **Import Mode**: Caches data in Power BI for speed (Good for < 1GB).
    *   **DirectQuery**: Queries Databricks in real-time (Good for massive data).
    *   **Single Sign-On (SSO)**: Uses Azure AD (Entra ID) so users only see data they are allowed to see.

## Summary Checklist for Implementation
1.  [ ] Install **SHIR** on a VM near SAP.
2.  [ ] Create **Azure Key Vault** and store SAP credentials.
3.  [ ] Create **ADF Pipeline** using SAP CDC connector.
4.  [ ] Mount **ADLS Gen2** in Databricks.
5.  [ ] Write **Spark Structured Streaming** or SQL jobs for Bronze -> Silver -> Gold.
6.  [ ] Connect **Power BI** to the Gold tables using the "Azure Databricks" connector.
