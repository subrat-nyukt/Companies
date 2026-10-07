"""
Hands-On Time Series Practice: ARIMA Modeling
=============================================
Scenario: We are forecasting Monthly Sales for a growing business.
This script walks through the entire Time Series workflow:
  1. Generate synthetic sales data (with a trend)
  2. Test for Stationarity (ADF Test)
  3. Difference the data to make it flat
  4. Fit an ARIMA model
  5. Forecast future sales and plot the results
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# --- IMPORTANT: Ensure statsmodels is installed ---
try:
    from statsmodels.tsa.stattools import adfuller
    from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
    from statsmodels.tsa.arima.model import ARIMA
except ImportError:
    print("[ERROR] You need to install statsmodels to run this script.")
    print("Run this in your terminal: pip install statsmodels")
    exit(1)

print("="*60)
print("1. Generating Business Sales Data")
print("="*60)
np.random.seed(42)
months = pd.date_range(start='2020-01-01', periods=60, freq='M')

# We build a time series that has a clear upward trend (Non-Stationary)
base_sales = 5000
trend = np.linspace(0, 3000, 60)
noise = np.random.normal(0, 300, 60)
sales = base_sales + trend + noise

df = pd.DataFrame({'Date': months, 'Sales': sales})
df.set_index('Date', inplace=True)

print(df.head())
print("\n[Notice] The data clearly has an upward trend. It is NOT stationary.")


print("\n" + "="*60)
print("2. Testing for Stationarity (Augmented Dickey-Fuller Test)")
print("="*60)
def print_adf_test(series):
    result = adfuller(series.dropna())
    print(f"ADF Statistic: {result[0]:.4f}")
    print(f"p-value:       {result[1]:.4f}")
    if result[1] < 0.05:
        print("Verdict:       Data is STATIONARY (p < 0.05).")
    else:
        print("Verdict:       Data is NOT STATIONARY (p > 0.05).")

print("Running ADF on Original Data:")
print_adf_test(df['Sales'])


print("\n" + "="*60)
print("3. Differencing the Data (The 'd' in ARIMA)")
print("="*60)
# Subtracting the previous month's sales from the current month
df['Sales_Diff'] = df['Sales'].diff()

print("Running ADF on Differenced Data (d=1):")
print_adf_test(df['Sales_Diff'])
print("\n[Success] The data is now stationary. We will use d=1 for our ARIMA model.")


print("\n" + "="*60)
print("4. Fitting the ARIMA Model")
print("="*60)
# We choose:
# p=1 (Auto-Regressive: look at 1 past lag)
# d=1 (Integrated: difference the data 1 time)
# q=1 (Moving Average: look at 1 past error)
model = ARIMA(df['Sales'], order=(1, 1, 1))
fitted_model = model.fit()

print(fitted_model.summary().tables[1])
print("\n[Notice] We have successfully fit the ARIMA(1,1,1) model.")


print("\n" + "="*60)
print("5. Forecasting the Future (Next 12 Months)")
print("="*60)
# Forecast 12 steps (months) ahead
forecast_steps = 12
forecast = fitted_model.get_forecast(steps=forecast_steps)
forecast_mean = forecast.predicted_mean
forecast_ci = forecast.conf_int(alpha=0.05) # 95% Confidence Interval

# Create future dates
future_dates = pd.date_range(start=df.index[-1] + pd.Timedelta(days=1), periods=forecast_steps, freq='M')

# ============================================================
# Plotting the Master Dashboard
# ============================================================
fig = plt.figure(figsize=(16, 12))
fig.patch.set_facecolor('#0d1117')
gs = gridspec.GridSpec(2, 2, figure=fig, height_ratios=[1, 1.5])

# Plot 1: ACF
ax1 = fig.add_subplot(gs[0, 0])
ax1.set_facecolor('#161b22')
plot_acf(df['Sales_Diff'].dropna(), ax=ax1, lags=20, color='white', title="")
ax1.set_title("ACF Plot (Finds 'q')", color='white', pad=10)
ax1.tick_params(colors='#8b949e')

# Plot 2: PACF
ax2 = fig.add_subplot(gs[0, 1])
ax2.set_facecolor('#161b22')
plot_pacf(df['Sales_Diff'].dropna(), ax=ax2, lags=20, color='white', title="", method='ywm')
ax2.set_title("PACF Plot (Finds 'p')", color='white', pad=10)
ax2.tick_params(colors='#8b949e')

# Style updates for ACF/PACF
for ax in [ax1, ax2]:
    ax.spines['bottom'].set_color('#30363d')
    ax.spines['left'].set_color('#30363d')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for line in ax.lines:
        if line.get_color() == 'white':
            line.set_color('#58a6ff')

# Plot 3: The Forecast
ax3 = fig.add_subplot(gs[1, :])
ax3.set_facecolor('#161b22')

# Plot historical training data
ax3.plot(df.index, df['Sales'], color='#3fb950', lw=2.5, label='Historical Sales')

# Plot the forecast
ax3.plot(future_dates, forecast_mean, color='#f78166', lw=2.5, linestyle='--', label='ARIMA Forecast')

# Fill the Confidence Interval
ax3.fill_between(future_dates, 
                 forecast_ci.iloc[:, 0], 
                 forecast_ci.iloc[:, 1], 
                 color='#f78166', alpha=0.2, label='95% Confidence Interval')

ax3.set_title("ARIMA(1,1,1) Sales Forecast for Next 12 Months", color='white', fontsize=14, fontweight='bold', pad=15)
ax3.set_ylabel("Sales ($)", color='#8b949e', fontsize=12)
ax3.tick_params(colors='#8b949e')
ax3.spines['bottom'].set_color('#30363d')
ax3.spines['left'].set_color('#30363d')
ax3.spines['top'].set_visible(False)
ax3.spines['right'].set_visible(False)
ax3.grid(axis='y', color='#30363d', linestyle='--', alpha=0.7)
ax3.legend(facecolor='#1c2128', labelcolor='white')

plt.tight_layout()
plt.savefig(r"c:\Users\DELL\Downloads\Personal\Companies\Resume_prep\Stats\arima_forecast_dashboard.png", dpi=150, facecolor='#0d1117')
print("[DONE] Successfully generated and saved forecast chart to: arima_forecast_dashboard.png")
plt.show()
