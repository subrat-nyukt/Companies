import pandas as pd
import numpy as np
import statsmodels.api as sm
import optuna
import warnings
import json

warnings.filterwarnings("ignore")

def apply_adstock(spend, decay):
    res = np.zeros(len(spend))
    res[0] = spend[0]
    for i in range(1, len(spend)): 
        res[i] = spend[i] + decay * res[i-1]
    return res

# 1. Load Data
df = pd.read_csv("trucker_fintech_mmm_dataset.csv")
y = df["new_card_signups"].astype(float)

weeks = pd.to_datetime(df["week_start"]).dt.isocalendar().week
df["time_trend"] = np.arange(len(df))
df["season_sin"] = np.sin(2 * np.pi * weeks / 52)
df["season_cos"] = np.cos(2 * np.pi * weeks / 52)

controls = ["diesel_price_usd", "freight_volume_index", "time_trend", "season_sin", "season_cos"]
channels = ["billboard_spend", "radio_spend", "digital_spend", "referral_budget_spend"]

# 2. Bayesian Objective Function
def objective(trial):
    X = df[controls].copy().astype(float)
    
    # Let Optuna randomly try decay rates (0.1 to 0.9) for each channel
    for col in channels:
        decay_rate = trial.suggest_float(col, 0.1, 0.9)
        X[col] = apply_adstock(df[col].values, decay_rate)
        
    # Fit the model and return R-Squared to be maximized
    return sm.OLS(y, sm.add_constant(X)).fit().rsquared

# 3. Run Optimization
print("Running Bayesian Optimizer...")
optuna.logging.set_verbosity(optuna.logging.WARNING)
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=200)

# 4. Results
print(f"\nMax R-Squared: {study.best_value:.4f}")
print("Best Decay Rates:")
for ch, rate in study.best_params.items():
    print(f"  {ch}: {rate:.2f}")

# 5. Export for downstream pipelines
with open("optimal_decay_rates.json", "w") as f:
    json.dump(study.best_params, f, indent=4)
print("\n[SUCCESS] Automatically saved to 'optimal_decay_rates.json'")
