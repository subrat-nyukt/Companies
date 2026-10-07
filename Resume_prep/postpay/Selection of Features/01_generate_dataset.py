"""
============================================================
STEP 0 — Generate Synthetic Dataset (111 Moove Features)
============================================================
Creates a realistic, credit-risk dataset with:
  • 111 features across 8 business domains
  • 5,000 driver records
  • Binary target: bad_debt (1 = defaulted, 0 = repaid)

Run this first before running the feature-selection pipeline.
Output: synthetic_driver_dataset.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)
N = 5_000

# ── Helper ────────────────────────────────────────────────
def clip(arr, lo, hi):
    return np.clip(arr, lo, hi)

# ── Latent risk score (drives correlations to target) ─────
risk_score = np.random.normal(0, 1, N)          # high → high risk

# =============================================================
# DOMAIN 1 – Customer Details  (22 features)
# =============================================================
age            = clip(np.random.normal(32, 7, N), 18, 65).astype(int)
reg_days       = clip(np.random.exponential(400, N), 30, 2000).astype(int)
reg_months     = (reg_days / 30).astype(int)
driving_exp    = clip(np.random.normal(6, 4, N), 0, 40).astype(int)
gender         = np.random.binomial(1, 0.85, N)
marital        = np.random.choice([0, 1, 2, 3], N, p=[0.35, 0.45, 0.1, 0.1])
dependents     = clip(np.random.poisson(np.clip(1.5 + 0.5 * risk_score, 0, None), N), 0, 8).astype(int)
education      = np.random.choice([0, 1, 2, 3], N, p=[0.1, 0.3, 0.4, 0.2])
addr_tenure    = clip(np.random.exponential(24, N), 1, 120).astype(int)
city           = np.random.choice([0, 1, 2, 3, 4], N, p=[0.3, 0.25, 0.2, 0.15, 0.1])
dist_hub       = clip(np.random.exponential(12, N), 0.5, 80)
nationality    = np.random.choice([0, 1, 2, 3], N, p=[0.55, 0.25, 0.12, 0.08])
expat_local    = np.random.binomial(1, 0.35, N)
id_expiry_days = clip(np.random.normal(300, 120, N), 0, 730).astype(int)
dl_expiry_days = clip(np.random.normal(500, 200, N), 0, 1800).astype(int)
prev_occ       = np.random.choice([0, 1, 2, 3, 4], N)
guarantor_avail = np.random.binomial(1, 0.55 - 0.15 * (risk_score > 0), N)
guarantor_rel  = np.random.choice([0, 1, 2, 3, 4], N, p=[0.3, 0.25, 0.2, 0.15, 0.1])
guarantor_fin  = clip(np.random.normal(55 - 8 * risk_score, 15, N), 10, 100)
social_media   = np.random.binomial(1, 0.65, N)
residential    = np.random.choice([0, 1, 2], N, p=[0.5, 0.3, 0.2])
# duplicate intentionally added for Pearson pruning test
reg_days_dup   = reg_days + np.random.randint(-2, 3, N)   # near-duplicate

# =============================================================
# DOMAIN 2 – Platform Earnings  (27 features)
# =============================================================
platform_tenure = clip(np.random.exponential(18, N), 1, 60).astype(int)
trips_lifetime  = clip(np.random.poisson(3000 - 400 * risk_score, N), 50, 15000)
daily_trips_1m  = clip(np.random.normal(12 - 2 * risk_score, 4, N), 0, 30)
daily_trips_3m  = daily_trips_1m * np.random.uniform(0.85, 1.05, N)
daily_trips_6m  = daily_trips_3m * np.random.uniform(0.85, 1.05, N)
wk_earn_1m      = clip(daily_trips_1m * np.random.normal(200, 30, N), 0, 8000)
wk_earn_3m      = wk_earn_1m * np.random.uniform(0.9, 1.05, N)
wk_earn_6m      = wk_earn_3m * np.random.uniform(0.9, 1.05, N)
earn_vol_3m     = clip(np.random.exponential(np.clip(300 + 100 * risk_score, 10, None), N), 50, 2000)
accept_1m       = clip(np.random.normal(0.82 - 0.05 * risk_score, 0.12, N), 0.2, 1.0)
accept_3m       = accept_1m * np.random.uniform(0.95, 1.03, N)
cancel_1m       = clip(np.random.normal(0.08 + 0.04 * risk_score, 0.05, N), 0, 0.5)
cancel_3m       = cancel_1m * np.random.uniform(0.95, 1.05, N)
rating          = clip(np.random.normal(4.3 - 0.3 * risk_score, 0.4, N), 1, 5)
low_ratings_3m  = clip(np.random.poisson(np.clip(1 + 2 * risk_score.clip(0), 0, None), N), 0, 20).astype(int)
hrs_online_1m   = clip(np.random.normal(180 - 20 * risk_score, 40, N), 20, 400)
hrs_online_3m   = hrs_online_1m * np.random.uniform(0.9, 1.05, N)
avg_hrs_day     = hrs_online_1m / 30
peak_ratio      = clip(np.random.normal(0.45 - 0.04 * risk_score, 0.1, N), 0, 1)
weekend_ratio   = clip(np.random.normal(0.35, 0.1, N), 0, 1)
night_ratio     = clip(np.random.normal(0.2 + 0.03 * risk_score, 0.07, N), 0, 1)
airport_ratio   = clip(np.random.normal(0.15, 0.07, N), 0, 1)
complaints_6m   = clip(np.random.poisson(np.clip(0.3 + 0.8 * risk_score.clip(0), 0, None), N), 0, 15).astype(int)
platform_tier   = clip(np.random.choice([0, 1, 2, 3], N, p=[0.4, 0.35, 0.15, 0.1]) - risk_score.clip(0, 2).astype(int), 0, 3)
multi_platform  = np.random.binomial(1, 0.4, N)
cash_ratio      = clip(np.random.normal(0.3 + 0.1 * risk_score, 0.15, N), 0, 1)

# =============================================================
# DOMAIN 3 – Telematics Behavior  (21 features)
# =============================================================
daily_mi_1m     = clip(np.random.normal(180, 40, N), 30, 500)
daily_mi_3m     = daily_mi_1m * np.random.uniform(0.92, 1.05, N)
hard_brake_1m   = clip(np.random.poisson(np.clip(5 + 4 * risk_score.clip(0), 0, None), N), 0, 40).astype(int)
hard_brake_3m   = hard_brake_1m * np.random.uniform(0.9, 1.1, N)
harsh_acc_1m    = clip(np.random.poisson(np.clip(4 + 3 * risk_score.clip(0), 0, None), N), 0, 35).astype(int)
harsh_acc_3m    = harsh_acc_1m * np.random.uniform(0.9, 1.1, N)
speed_viol_1m   = clip(np.random.poisson(np.clip(2 + 3 * risk_score.clip(0), 0, None), N), 0, 30).astype(int)
speed_viol_3m   = speed_viol_1m * np.random.uniform(0.9, 1.1, N)
avg_spd_over    = clip(np.random.normal(8 + 5 * risk_score.clip(0), 5, N), 0, 50)
sharp_corn_1m   = clip(np.random.poisson(np.clip(3 + 2 * risk_score.clip(0), 0, None), N), 0, 25).astype(int)
tailgating_1m   = clip(np.random.poisson(np.clip(1 + 2 * risk_score.clip(0), 0, None), N), 0, 15).astype(int)
latenight_hrs   = clip(np.random.normal(10 + 5 * risk_score.clip(0), 5, N), 0, 60)
geofence_viol   = clip(np.random.poisson(np.clip(0.5 + risk_score.clip(0), 0, None), N), 0, 10).astype(int)
idle_ratio      = clip(np.random.normal(0.15 + 0.05 * risk_score, 0.07, N), 0, 1)
fuel_score      = clip(np.random.normal(70 - 10 * risk_score, 15, N), 10, 100)
battery_drain   = clip(np.random.poisson(np.clip(0.5 + risk_score.clip(0), 0, None), N), 0, 8).astype(int)
maint_ignored   = clip(np.random.poisson(np.clip(0.8 + risk_score.clip(0), 0, None), N), 0, 10).astype(int)
avg_trip_km     = clip(np.random.normal(12, 4, N), 2, 50)
long_dist_ratio = clip(np.random.normal(0.2, 0.1, N), 0, 1)
tampering_alerts= clip(np.random.poisson(np.clip(0.1 + 0.3 * risk_score.clip(0), 0, None), N), 0, 5).astype(int)
accident_events = clip(np.random.poisson(np.clip(0.2 + 0.4 * risk_score.clip(0), 0, None), N), 0, 5).astype(int)

# =============================================================
# DOMAIN 4 – Financial History  (16 features)
# =============================================================
bureau_score    = clip(np.random.normal(580 - 60 * risk_score, 80, N), 300, 850).astype(int)
active_credit   = clip(np.random.poisson(2 + risk_score.clip(0), N), 0, 10).astype(int)
total_debt      = clip(np.random.exponential(15000 + 5000 * risk_score.clip(0), N), 0, 200000)
defaults_count  = clip(np.random.poisson(np.clip(0.3 + risk_score.clip(0), 0, None), N), 0, 8).astype(int)
late_pay_12m    = clip(np.random.poisson(np.clip(1 + 2 * risk_score.clip(0), 0, None), N), 0, 12).astype(int)
avg_bank_3m     = clip(np.random.exponential(np.clip(3000 - 500 * risk_score.clip(0, 4), 50, None), N), 0, 30000)
min_bank_3m     = avg_bank_3m * np.random.uniform(0.1, 0.6, N)
bank_inflow_3m  = clip(avg_bank_3m * 4 * np.random.uniform(0.8, 1.2, N), 0, 200000)
mobile_tx_3m    = clip(np.random.exponential(2000, N), 0, 50000)
bounced_tx      = clip(np.random.poisson(np.clip(0.4 + 1.5 * risk_score.clip(0), 0, None), N), 0, 10).astype(int)
debt_to_income  = clip(np.random.normal(0.35 + 0.15 * risk_score, 0.15, N), 0, 2.0)
auto_loan_flag  = np.random.binomial(1, 0.3 + 0.15 * (risk_score > 0), N)
savings_freq    = clip(np.random.poisson(np.clip(3 - risk_score.clip(0, 2), 0, None), N), 0, 15).astype(int)
utility_reg     = clip(np.random.normal(0.75 - 0.15 * risk_score, 0.2, N), 0, 1)
overdraft_util  = clip(np.random.normal(0.2 + 0.15 * risk_score, 0.15, N), 0, 1)
gambling_ratio  = clip(np.random.exponential(0.02 + 0.03 * risk_score.clip(0), N), 0, 0.5)

# =============================================================
# DOMAIN 5 – Loan Origination  (15 features)
# =============================================================
loan_principal  = clip(np.random.normal(25000, 8000, N), 8000, 80000)
vehicle_make    = np.random.choice([0, 1, 2, 3, 4], N, p=[0.35, 0.25, 0.2, 0.12, 0.08])
vehicle_model   = np.random.choice(range(10), N)
vehicle_year    = clip(np.random.normal(2019, 2, N), 2010, 2024).astype(int)
vehicle_body    = np.random.choice([0, 1, 2, 3], N, p=[0.5, 0.25, 0.15, 0.1])
energy_type     = np.random.choice([0, 1, 2, 3], N, p=[0.7, 0.15, 0.1, 0.05])
downpay_amt     = clip(loan_principal * np.random.uniform(0.1, 0.4, N), 1000, 30000)
downpay_pct     = downpay_amt / loan_principal
loan_term_wks   = np.random.choice([52, 78, 104, 156], N, p=[0.2, 0.4, 0.3, 0.1])
weekly_remit    = loan_principal / loan_term_wks
implied_int     = clip(np.random.normal(0.18 + 0.04 * risk_score, 0.04, N), 0.08, 0.45)
pay_interval    = np.random.choice([0, 1], N, p=[0.15, 0.85])
insurance_tier  = np.random.choice([0, 1, 2], N, p=[0.6, 0.3, 0.1])
depr_class      = np.random.choice([0, 1, 2, 3], N, p=[0.3, 0.4, 0.2, 0.1])
ltv_ratio       = loan_principal / clip(loan_principal + downpay_amt, 1, None)

# =============================================================
# DOMAIN 6 – App Usage  (11 features)
# =============================================================
device_os       = np.random.choice([0, 1], N, p=[0.75, 0.25])
device_age_mo   = clip(np.random.exponential(18, N), 1, 72).astype(int)
app_login_freq_wk = clip(np.random.normal(14 - 2 * risk_score, 5, N), 0, 35)
days_installed  = clip(np.random.exponential(300, N), 30, 1500).astype(int)
support_tix_3m  = clip(np.random.poisson(np.clip(1 + 2 * risk_score.clip(0), 0, None), N), 0, 15).astype(int)
tix_res_time    = clip(np.random.exponential(np.clip(24 + 12 * risk_score.clip(0), 1, None), N), 2, 200)
loc_services    = np.random.binomial(1, 0.8, N)
notif_enabled   = np.random.binomial(1, 0.7, N)
avg_battery_lvl = clip(np.random.normal(55 - 5 * risk_score, 15, N), 5, 100)
network_prov    = np.random.choice([0, 1, 2, 3], N, p=[0.4, 0.3, 0.2, 0.1])
app_updated     = np.random.binomial(1, 0.65, N)

# =============================================================
# DOMAIN 7 – Location Risk  (5 features)
# =============================================================
zone_risk_score  = clip(np.random.normal(50 + 15 * risk_score, 15, N), 0, 100)
home_risk_score  = clip(np.random.normal(45 + 12 * risk_score, 12, N), 0, 100)
high_risk_ratio  = clip(np.random.normal(0.2 + 0.1 * risk_score, 0.1, N), 0, 1)
cross_border_flag= np.random.binomial(1, 0.08 + 0.05 * (risk_score > 0.5), N)
home_work_dist   = clip(np.random.exponential(15, N), 1, 100)

# =============================================================
# DOMAIN 8 – Previous Interactions  (9 features)
# =============================================================
days_first_loan  = clip(np.random.exponential(400, N), 0, 2000).astype(int)
prev_loan_count  = clip(np.random.poisson(np.clip(1.5, 0, None), N), 0, 8).astype(int)
hist_delay_days  = clip(np.random.exponential(np.clip(3 + 5 * risk_score.clip(0), 0.1, None), N), 0, 60)
missed_remit_pct = clip(np.random.normal(0.05 + 0.15 * risk_score, 0.07, N), 0, 1)
early_payout_flag= np.random.binomial(1, 0.2 - 0.1 * (risk_score > 0), N)
prev_repo_flag   = np.random.binomial(1, 0.05 + 0.1 * (risk_score > 0.8), N)
loyalty_tier     = clip(np.random.choice([0, 1, 2, 3], N, p=[0.4, 0.3, 0.2, 0.1]) - risk_score.clip(0, 2).astype(int), 0, 3)
hist_revenue     = clip(np.random.exponential(8000, N), 0, 100000)
accident_claims  = clip(np.random.poisson(np.clip(0.3 + 0.5 * risk_score.clip(0), 0, None), N), 0, 8).astype(int)

# =============================================================
# TARGET – bad_debt (logistic probability)
# =============================================================
log_odds = (
    -2.0
    + 0.8  * risk_score
    + 0.4  * (defaults_count > 0).astype(float)
    + 0.3  * (missed_remit_pct > 0.1).astype(float)
    + 0.25 * (late_pay_12m > 2).astype(float)
    + 0.2  * (debt_to_income > 0.5).astype(float)
    - 0.3  * (bureau_score > 650).astype(float)
    - 0.25 * (avg_bank_3m > 3000).astype(float)
    + 0.2  * (gambling_ratio > 0.05).astype(float)
    + 0.15 * (hard_brake_1m > 10).astype(float)
    - 0.15 * (downpay_pct > 0.25).astype(float)
)
prob = 1 / (1 + np.exp(-log_odds))
bad_debt = np.random.binomial(1, prob, N)

print(f"Bad debt rate: {bad_debt.mean():.2%}")

# =============================================================
# Assemble DataFrame  (111 features + 1 target)
# =============================================================
df = pd.DataFrame({
    # Domain 1 – Customer Details
    "age": age, "reg_days": reg_days, "reg_months": reg_months,
    "driving_exp": driving_exp, "gender": gender, "marital_status": marital,
    "dependents": dependents, "education": education, "addr_tenure_mo": addr_tenure,
    "city": city, "dist_hub_km": dist_hub, "nationality": nationality,
    "expat_local": expat_local, "id_expiry_days": id_expiry_days,
    "dl_expiry_days": dl_expiry_days, "prev_occupation": prev_occ,
    "guarantor_avail": guarantor_avail, "guarantor_rel": guarantor_rel,
    "guarantor_fin_score": guarantor_fin, "social_media_flag": social_media,
    "residential_status": residential, "reg_days_dup": reg_days_dup,
    # Domain 2 – Platform Earnings
    "platform_tenure_mo": platform_tenure, "trips_lifetime": trips_lifetime,
    "daily_trips_1m": daily_trips_1m, "daily_trips_3m": daily_trips_3m,
    "daily_trips_6m": daily_trips_6m, "wk_earn_1m": wk_earn_1m,
    "wk_earn_3m": wk_earn_3m, "wk_earn_6m": wk_earn_6m,
    "earn_vol_3m": earn_vol_3m, "accept_rate_1m": accept_1m,
    "accept_rate_3m": accept_3m, "cancel_rate_1m": cancel_1m,
    "cancel_rate_3m": cancel_3m, "passenger_rating": rating,
    "low_ratings_3m": low_ratings_3m, "hrs_online_1m": hrs_online_1m,
    "hrs_online_3m": hrs_online_3m, "avg_hrs_day": avg_hrs_day,
    "peak_hour_ratio": peak_ratio, "weekend_ratio": weekend_ratio,
    "night_ratio": night_ratio, "airport_ratio": airport_ratio,
    "complaints_6m": complaints_6m, "platform_tier": platform_tier,
    "multi_platform": multi_platform, "cash_trip_ratio": cash_ratio,
    # Domain 3 – Telematics
    "daily_mi_1m": daily_mi_1m, "daily_mi_3m": daily_mi_3m,
    "hard_brake_1m": hard_brake_1m, "hard_brake_3m": hard_brake_3m,
    "harsh_acc_1m": harsh_acc_1m, "harsh_acc_3m": harsh_acc_3m,
    "speed_viol_1m": speed_viol_1m, "speed_viol_3m": speed_viol_3m,
    "avg_spd_over_pct": avg_spd_over, "sharp_corn_1m": sharp_corn_1m,
    "tailgating_1m": tailgating_1m, "latenight_hrs_1m": latenight_hrs,
    "geofence_viol_1m": geofence_viol, "idle_ratio": idle_ratio,
    "fuel_score": fuel_score, "battery_drain_incidents": battery_drain,
    "maint_alerts_ignored": maint_ignored, "avg_trip_km": avg_trip_km,
    "long_dist_ratio": long_dist_ratio, "tampering_alerts": tampering_alerts,
    "accident_detection": accident_events,
    # Domain 4 – Financial History
    "bureau_score": bureau_score, "active_credit": active_credit,
    "total_outstanding_debt": total_debt, "past_defaults_count": defaults_count,
    "late_payments_12m": late_pay_12m, "avg_bank_bal_3m": avg_bank_3m,
    "min_bank_bal_3m": min_bank_3m, "bank_inflow_3m": bank_inflow_3m,
    "mobile_tx_vol_3m": mobile_tx_3m, "bounced_tx": bounced_tx,
    "debt_to_income": debt_to_income, "auto_loan_flag": auto_loan_flag,
    "savings_freq": savings_freq, "utility_regularity": utility_reg,
    "overdraft_util_rate": overdraft_util, "gambling_tx_ratio": gambling_ratio,
    # Domain 5 – Loan Origination
    "loan_principal": loan_principal, "vehicle_make": vehicle_make,
    "vehicle_model": vehicle_model, "vehicle_year": vehicle_year,
    "vehicle_body": vehicle_body, "energy_type": energy_type,
    "downpayment_amt": downpay_amt, "downpayment_pct": downpay_pct,
    "loan_term_wks": loan_term_wks, "weekly_remittance": weekly_remit,
    "implied_int_rate": implied_int, "pay_interval": pay_interval,
    "insurance_tier": insurance_tier, "asset_depr_class": depr_class,
    "ltv_ratio": ltv_ratio,
    # Domain 6 – App Usage
    "device_os": device_os, "device_age_mo": device_age_mo,
    "app_login_freq_wk": app_login_freq_wk, "days_since_app_install": days_installed,
    "support_tickets_3m": support_tix_3m, "avg_ticket_res_time": tix_res_time,
    "location_services": loc_services, "notif_enabled": notif_enabled,
    "avg_battery_lvl": avg_battery_lvl, "network_provider": network_prov,
    "app_version_updated": app_updated,
    # Domain 7 – Location Risk
    "zone_risk_score": zone_risk_score, "home_risk_score": home_risk_score,
    "high_risk_trip_ratio": high_risk_ratio, "cross_border_flag": cross_border_flag,
    "home_work_dist_km": home_work_dist,
    # Domain 8 – Previous Interactions
    "days_since_first_loan": days_first_loan, "prev_moove_loan_count": prev_loan_count,
    "hist_avg_delay_days": hist_delay_days, "missed_remit_pct": missed_remit_pct,
    "early_payout_flag": early_payout_flag, "prev_repo_flag": prev_repo_flag,
    "loyalty_tier": loyalty_tier, "total_hist_revenue": hist_revenue,
    "accident_claims_hist": accident_claims,
    # Target
    "bad_debt": bad_debt,
})

out_path = Path(__file__).parent / "synthetic_driver_dataset.csv"
df.to_csv(out_path, index=False)

print(f"\n[OK] Dataset saved -> {out_path}")
print(f"   Shape : {df.shape[0]:,} rows x {df.shape[1]} columns")
print(f"   Features: {df.shape[1] - 1}  |  Target: bad_debt")
print(f"   Bad-debt rate: {df['bad_debt'].mean():.2%}")
