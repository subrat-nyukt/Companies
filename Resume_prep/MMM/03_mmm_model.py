import pandas as pd
import numpy as np
import statsmodels.api as sm
from sklearn.metrics import r2_score, mean_absolute_percentage_error
import warnings
warnings.filterwarnings("ignore")

# 1. Load Adstocked Dataset (output of Step 2)
try:
    df = pd.read_csv("trucker_fintech_mmm_adstocked.csv", parse_dates=["week_start"])
except FileNotFoundError:
    print("Run 02_adstock_transformation.py first.")
    exit()

# 2. Feature Engineering (Time Trend + Seasonality)
df["time_trend"] = np.arange(len(df))
weeks = df["week_start"].dt.isocalendar().week.astype(int)
df["season_sin"] = np.sin(2 * np.pi * weeks / 52)
df["season_cos"] = np.cos(2 * np.pi * weeks / 52)

# 3. Define Features (X) and Target (y)
channels = ["billboard_spend_adstock", "radio_spend_adstock", "digital_spend_adstock", "referral_budget_spend_adstock"]
controls = ["diesel_price_usd", "freight_volume_index", "time_trend", "season_sin", "season_cos"]

y = df["new_card_signups"]
X = sm.add_constant(df[channels + controls])

# 4. Fit OLS Regression Model
model = sm.OLS(y, X).fit()
print(model.summary())

# 5. Performance Metrics
y_pred = model.predict(X)
print(f"\nR-Squared : {r2_score(y, y_pred):.4f}")
print(f"MAPE      : {mean_absolute_percentage_error(y, y_pred)*100:.2f}%")

# 6. ROAS Calculation (Revenue per $1 Spent per Channel)
AVG_CLV = 350  # $350 Lifetime Value per acquired trucker

raw_map = {
    "billboard_spend_adstock"       : ("billboard_spend",       "Billboards"),
    "radio_spend_adstock"           : ("radio_spend",           "Satellite Radio"),
    "digital_spend_adstock"         : ("digital_spend",         "Digital Ads"),
    "referral_budget_spend_adstock" : ("referral_budget_spend", "Driver Referrals"),
}

roas_data = []
for adstock_col, (raw_col, name) in raw_map.items():
    signups  = model.params[adstock_col] * df[adstock_col].sum()
    revenue  = signups * AVG_CLV
    spend    = df[raw_col].sum()
    roas_data.append({"Channel": name, "Spend ($)": round(spend), "Signups": round(signups), "Revenue ($)": round(revenue), "ROAS": round(revenue / spend, 2)})

roas_df = pd.DataFrame(roas_data).sort_values("ROAS", ascending=False)
print("\nROAS by Channel:")
print(roas_df.to_string(index=False))

roas_df.to_csv("roas_results.csv", index=False)
print("\nSaved: roas_results.csv | Run 04_decomposition_and_insights.py next.")
