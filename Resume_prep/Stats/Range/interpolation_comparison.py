"""
Interpolation Comparison: Linear vs Polynomial vs Cubic Spline
==============================================================
Dataset: Monthly Revenue (accelerating growth curve to mimic real business data)
Method:
  1. Create "True" revenue data with known values (ground truth)
  2. Artificially remove (mask) some values to simulate missing data
  3. Apply each interpolation method to fill the gaps
  4. Compare estimates vs the true values using MAE and RMSE
  5. Plot all 3 methods side by side
"""

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ============================================================
# STEP 1: Create a realistic revenue dataset (ground truth)
# We simulate 30 days of revenue following exponential-ish growth
# to make linear interpolation imperfect and show the difference.
# ============================================================
np.random.seed(42)

days = np.arange(1, 31)  # Day 1 to Day 30

# True underlying revenue: quadratic growth + small noise
# Formula: Revenue = 50*day^2 + 200*day + 1000 + noise
true_revenue = 50 * days**2 + 200 * days + 1000 + np.random.normal(0, 500, size=len(days))
true_revenue = np.clip(true_revenue, 0, None)  # Revenue can't be negative

df = pd.DataFrame({"day": days, "revenue": true_revenue})

print("=" * 60)
print("GROUND TRUTH DATASET (first 10 rows)")
print("=" * 60)
print(df.head(10).to_string(index=False))

# ============================================================
# STEP 2: Artificially remove (mask) certain days to simulate
# missing data. These are the "gaps" we will interpolate.
# ============================================================
# We will remove Day 4, 5, 6, 13, 14, 20, 21, 22 (8 missing points)
missing_days = [4, 5, 6, 13, 14, 20, 21, 22]

# "known" data = everything except missing days
known_mask = ~np.isin(days, missing_days)
known_days    = days[known_mask]
known_revenue = true_revenue[known_mask]

print(f"\n[OK] Known data points: {len(known_days)}")
print(f"[--] Missing/masked days: {missing_days}")

# ============================================================
# STEP 3: Apply each interpolation method
# ============================================================

# --- Method 1: Linear Interpolation ---
linear_fn    = interp1d(known_days, known_revenue, kind="linear", fill_value="extrapolate")
linear_pred  = linear_fn(days)

# --- Method 2: Polynomial Interpolation (degree 4) ---
# Using numpy.polyfit to fit a polynomial of degree 4 across ALL known points
poly_coeffs  = np.polyfit(known_days, known_revenue, deg=4)
poly_fn      = np.poly1d(poly_coeffs)
poly_pred    = poly_fn(days)

# --- Method 3: Cubic Spline Interpolation ---
cubic_fn     = CubicSpline(known_days, known_revenue)
cubic_pred   = cubic_fn(days)

# ============================================================
# STEP 4: Measure Efficacy on ONLY the missing days
# (We already know the true answer — this is how we grade accuracy)
# ============================================================
missing_mask = np.isin(days, missing_days)
true_missing  = true_revenue[missing_mask]

linear_est  = linear_pred[missing_mask]
poly_est    = poly_pred[missing_mask]
cubic_est   = cubic_pred[missing_mask]

def mae(true, pred):
    return np.mean(np.abs(true - pred))

def rmse(true, pred):
    return np.sqrt(np.mean((true - pred) ** 2))

results = {
    "Method":   ["Linear", "Polynomial (deg 4)", "Cubic Spline"],
    "MAE ($)":  [mae(true_missing, linear_est),
                 mae(true_missing, poly_est),
                 mae(true_missing, cubic_est)],
    "RMSE ($)": [rmse(true_missing, linear_est),
                 rmse(true_missing, poly_est),
                 rmse(true_missing, cubic_est)],
}

results_df = pd.DataFrame(results)
results_df["MAE ($)"]  = results_df["MAE ($)"].round(2)
results_df["RMSE ($)"] = results_df["RMSE ($)"].round(2)

print("\n" + "=" * 60)
print("EFFICACY COMPARISON (lower = better accuracy)")
print("=" * 60)
print(results_df.to_string(index=False))

# Find the winner
best_method = results_df.loc[results_df["RMSE ($)"].idxmin(), "Method"]
print(f"\n[WINNER] Lowest RMSE: {best_method}")

# Detailed breakdown per missing day
print("\n" + "=" * 60)
print("DETAILED ESTIMATES vs TRUE VALUES (Missing Days Only)")
print("=" * 60)
detail_df = pd.DataFrame({
    "Day":          np.array(missing_days),
    "True Revenue": true_missing.round(2),
    "Linear":       linear_est.round(2),
    "Polynomial":   poly_est.round(2),
    "Cubic Spline": cubic_est.round(2),
})
detail_df["Linear Error"]   = (detail_df["Linear"]       - detail_df["True Revenue"]).abs().round(2)
detail_df["Poly Error"]     = (detail_df["Polynomial"]   - detail_df["True Revenue"]).abs().round(2)
detail_df["Spline Error"]   = (detail_df["Cubic Spline"] - detail_df["True Revenue"]).abs().round(2)
print(detail_df.to_string(index=False))

# ============================================================
# STEP 5: Plotting
# ============================================================
fig = plt.figure(figsize=(18, 14))
fig.patch.set_facecolor("#0d1117")
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

colors = {
    "true":    "#58a6ff",
    "linear":  "#f78166",
    "poly":    "#ffa657",
    "cubic":   "#3fb950",
    "known":   "#ffffff",
    "missing": "#ff7b72",
}

ax_titles = [
    ("Linear Interpolation",       "linear",  colors["linear"]),
    ("Polynomial Interpolation",   "poly",    colors["poly"]),
    ("Cubic Spline Interpolation", "cubic",   colors["cubic"]),
]

# --- Subplot for each method ---
for idx, (title, key, color) in enumerate(ax_titles):
    row, col = divmod(idx, 2)
    ax = fig.add_subplot(gs[row, col])
    ax.set_facecolor("#161b22")

    pred_map = {"linear": linear_pred, "poly": poly_pred, "cubic": cubic_pred}
    est_map  = {"linear": linear_est,  "poly": poly_est,  "cubic": cubic_est}

    # True curve
    ax.plot(days, true_revenue, color=colors["true"], lw=2,
            label="True Revenue", zorder=3, linestyle="--", alpha=0.7)
    # Interpolated curve
    ax.plot(days, pred_map[key], color=color, lw=2.5, label=f"{title}", zorder=4)
    # Known data points (white dots)
    ax.scatter(known_days, known_revenue, color=colors["known"], s=60,
               zorder=5, label="Known Points")
    # Missing day estimates (colored markers)
    ax.scatter(missing_days, est_map[key], color=color, s=100,
               marker="X", zorder=6, label="Estimated (Missing)")
    # True values at missing days (red dots for comparison)
    ax.scatter(missing_days, true_missing, color=colors["missing"], s=60,
               marker="o", zorder=7, label="True (Missing)", alpha=0.8)

    ax.set_title(title, color="white", fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Day", color="#8b949e", fontsize=10)
    ax.set_ylabel("Revenue ($)", color="#8b949e", fontsize=10)
    ax.tick_params(colors="#8b949e")
    ax.spines["bottom"].set_color("#30363d")
    ax.spines["left"].set_color("#30363d")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=8, labelcolor="white", facecolor="#1c2128", framealpha=0.8)

    # Annotate RMSE on the plot
    err_val = rmse(true_missing, est_map[key])
    ax.text(0.02, 0.95, f"RMSE: ${err_val:,.0f}", transform=ax.transAxes,
            color=color, fontsize=10, fontweight="bold", va="top")

# --- Summary bar chart (RMSE comparison) ---
ax4 = fig.add_subplot(gs[1, 1])
ax4.set_facecolor("#161b22")

methods   = results_df["Method"].tolist()
rmse_vals = results_df["RMSE ($)"].tolist()
bar_colors = [colors["linear"], colors["poly"], colors["cubic"]]

bars = ax4.bar(methods, rmse_vals, color=bar_colors, width=0.5, zorder=3)
ax4.set_title("RMSE Comparison (Lower = Better)", color="white", fontsize=13,
              fontweight="bold", pad=10)
ax4.set_ylabel("RMSE ($)", color="#8b949e", fontsize=10)
ax4.tick_params(colors="#8b949e")
ax4.spines["bottom"].set_color("#30363d")
ax4.spines["left"].set_color("#30363d")
ax4.spines["top"].set_visible(False)
ax4.spines["right"].set_visible(False)
ax4.set_facecolor("#161b22")

for bar, val in zip(bars, rmse_vals):
    ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
             f"${val:,.0f}", ha="center", va="bottom", color="white",
             fontsize=10, fontweight="bold")

fig.suptitle("Interpolation Methods: Efficacy Comparison on Revenue Data",
             color="white", fontsize=16, fontweight="bold", y=0.98)

plt.savefig(
    r"c:\Users\DELL\Downloads\Personal\Companies\Resume_prep\Stats\interpolation_comparison.png",
    dpi=150, bbox_inches="tight", facecolor="#0d1117"
)
print("\n[DONE] Chart saved to Stats/interpolation_comparison.png")
plt.show()
