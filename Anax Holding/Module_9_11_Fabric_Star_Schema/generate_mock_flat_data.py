import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

dir_path = os.path.dirname(os.path.abspath(__file__))

print("[SETUP] Generating massive Flat Golden Record table...")
num_records = 500

dates = [datetime(2026, 4, 1) + timedelta(days=int(np.random.randint(0, 30))) for _ in range(num_records)]
client_ids = [f"ANX-{np.random.randint(100, 150)}" for _ in range(num_records)]
countries = ["UAE", "UK", "USA", "Germany", "France"]
instruments = [("EURUSD", "Forex"), ("XAUUSD", "Commodity"), ("BTCUSD", "Crypto"), ("AAPL", "Stock")]

data = []
for i in range(num_records):
    inst, itype = instruments[np.random.randint(0, len(instruments))]
    
    # This represents a "Denormalized" flat table (bad for Power BI performance)
    data.append({
        "trade_id": f"TRD-{10000+i}",
        "execution_date": dates[i].strftime("%Y-%m-%d"),
        "client_id": client_ids[i],
        "client_country": np.random.choice(countries),
        "kyc_status": np.random.choice(["VERIFIED", "PENDING"]),
        "instrument_symbol": inst,
        "instrument_type": itype,
        "trade_volume": round(np.random.uniform(0.1, 5.0), 2),
        "trade_profit": round(np.random.normal(50, 200), 2),
        "broker_commission": 3.00
    })

df = pd.DataFrame(data)
output_path = os.path.join(dir_path, "flat_enterprise_lakehouse_export.csv")
df.to_csv(output_path, index=False)
print(f"[SUCCESS] Wrote flat table to: {output_path}")
