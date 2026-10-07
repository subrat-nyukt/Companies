"""
Step 2: Simplify Adstock Transformation
"""
import pandas as pd
import numpy as np
import json

def apply_adstock(spend, decay_rate):
    """Calculates carryover effect of marketing spend."""
    adstocked = np.zeros(len(spend))
    adstocked[0] = spend[0]
    for t in range(1, len(spend)):
        adstocked[t] = spend[t] + decay_rate * adstocked[t - 1]
    return adstocked

# 1. Load Raw Dataset
df = pd.read_csv("trucker_fintech_mmm_dataset.csv", parse_dates=["week_start"])

# 2. Fetch Bayesian Decay Rates (Generated from Step 2b)
try:
    with open("optimal_decay_rates.json", "r") as f:
        DECAY_RATES = json.load(f)
    print("[SUCCESS] Loaded Optimal Rates.")
except FileNotFoundError:
    print("[WARNING] JSON not found. Using Defaults.")
    DECAY_RATES = {"billboard_spend": 0.60, "radio_spend": 0.40, "digital_spend": 0.20, "referral_budget_spend": 0.80}

# 3. Apply the Adstock Math
for channel, alpha in DECAY_RATES.items():
    df[f"{channel}_adstock"] = apply_adstock(df[channel].values, alpha)

# 4. Save final adstocked numbers for Regression Mode!
df.to_csv("trucker_fintech_mmm_adstocked.csv", index=False)
print("Data adstocked & mathematically transformed successfully!")
