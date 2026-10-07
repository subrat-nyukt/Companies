import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# Create directory for SAP source system
os.makedirs("sap_system_source", exist_ok=True)

def generate_sap_data():
    print("Generating Virtual SAP S/4HANA Data...")
    
    # 1. KNA1 (Customer Master)
    # Fields: KUNNR (Customer Number), NAME1 (Name), LAND1 (Country), REGIO (Region)
    kna1_data = {
        'KUNNR': range(1000, 1050),
        'NAME1': [f'Customer_{i}' for i in range(50)],
        'LAND1': np.random.choice(['US', 'DE', 'FR', 'GB'], 50),
        'REGIO': np.random.choice(['NY', 'BY', 'IDF', 'LDN'], 50)
    }
    df_kna1 = pd.DataFrame(kna1_data)
    
    # Simulate some dirty data for ETL to clean later
    df_kna1.loc[5, 'NAME1'] = None 
    
    kna1_path = "sap_system_source/KNA1.csv"
    df_kna1.to_csv(kna1_path, index=False)
    print(f"Created table KNA1 at {kna1_path}")

    # 2. VBAK (Sales Document: Header Data)
    # Fields: VBELN (Sales Doc), KUNNR (Customer), AUDAT (Doc Date), NETWR (Net Value)
    vbak_data = {
        'VBELN': range(5000, 5200),
        'KUNNR': np.random.choice(range(1000, 1050), 200),
        'AUDAT': [datetime.now() - timedelta(days=x) for x in range(200)],
        'NETWR': np.random.uniform(100.0, 5000.0, 200).round(2),
        'WAERK': 'USD'
    }
    df_vbak = pd.DataFrame(vbak_data)
    
    # Introducing a duplicate for ETL to handle
    df_vbak = pd.concat([df_vbak, df_vbak.iloc[0:1]], ignore_index=True)

    vbak_path = "sap_system_source/VBAK.csv"
    df_vbak.to_csv(vbak_path, index=False)
    print(f"Created table VBAK at {vbak_path}")

if __name__ == "__main__":
    generate_sap_data()
