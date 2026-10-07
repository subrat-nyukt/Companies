import pandas as pd
import numpy as np
import os

# Set up local directory
dir_path = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(dir_path, "raw_mt5_deals.csv")

# Set seed for reproducibility
np.random.seed(42)
num_rows = 10000

# 1. 500 Unique Traders
logins = np.random.randint(10000, 10500, size=num_rows)  

# 2. Financial Instruments (Gold, Forex, Crypto, Indices)
symbols = np.random.choice(["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD", "US30"], size=num_rows, p=[0.4, 0.2, 0.2, 0.1, 0.1])

# 3. Trade Lots (Volume)
volumes = np.round(np.random.uniform(0.1, 10.0, size=num_rows), 2)

# 4. Broker Spread Markup (They make money on the gap between Buy/Sell cost)
spreads = np.round(volumes * np.random.uniform(2.0, 15.0, size=num_rows), 2)

# 5. Fixed Commission (Broker makes $3 per lot traded)
commissions = np.round(volumes * 3.0, 2)

# 6. Client Trading Profit (A mix of wins and massive losses)
client_profits = np.round(np.random.normal(loc=-10.0, scale=150.0, size=num_rows), 2)

# 7. A-Book vs B-Book (Broker keeps 80% of trades "In-House" to take the other side of the bet)
is_b_book = np.random.choice([True, False], size=num_rows, p=[0.8, 0.2])

print(f"[PROCESSING] Generating {num_rows} MT5 trades...")

df = pd.DataFrame({
    "ticket": range(1000000, 1000000 + num_rows),
    "login": logins,
    "symbol": symbols,
    "volume": volumes,
    "spread_revenue": spreads,
    "commission": commissions,
    "client_profit": client_profits,
    "is_b_book": is_b_book
})

df.to_csv(output_file, index=False)
print(f"[SUCCESS] Saved massive MT5 Deal Dump to: {output_file}")
