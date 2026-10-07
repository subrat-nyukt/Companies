"""
Step 1: Simplify Exploratory Data Analysis (EDA)
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Load Data
df = pd.read_csv("trucker_fintech_mmm_dataset.csv", parse_dates=["week_start"])
print("Data Shape:", df.shape)
print("\nSummary Statistics:\n", df.describe().round(2))

CHANNELS = ["billboard_spend", "radio_spend", "digital_spend", "referral_budget_spend"]

# 2. Plot 1: Target Variable Over Time
df.plot(x="week_start", y="new_card_signups", title="Weekly New Signups", figsize=(10, 4))
plt.savefig("plot_01_signups_over_time.png")

# 3. Plot 2: Stacked Spend
df.plot.area(x="week_start", y=CHANNELS, title="Spend by Channel", figsize=(10, 4))
plt.savefig("plot_02_spend_by_channel.png")

# 4. Plot 3: Budget Composition
total_spend = df[CHANNELS].sum()
total_spend.plot.pie(autopct="%1.1f%%", title="Budget Allocation", figsize=(6, 6))
plt.savefig("plot_03_budget_allocation.png")

# 5. Plot 4: Correlation Heatmap
corr_cols = ["new_card_signups"] + CHANNELS + ["diesel_price_usd", "freight_volume_index"]
plt.figure(figsize=(8, 6))
sns.heatmap(df[corr_cols].corr(), annot=True, cmap="coolwarm", fmt=".2f")
plt.savefig("plot_04_correlation_heatmap.png")

# 6. Summary Stats
total_budget = total_spend.sum()
print("\nTotal Budget :", f"${total_budget:,.0f}")
print("Total Signups:", f"{df['new_card_signups'].sum():,}")
print("Blended CAC  :", f"${total_budget / df['new_card_signups'].sum():.2f}")
