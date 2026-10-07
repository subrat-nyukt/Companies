"""
=============================================================
E03 — Data Drift Monitoring: Population Stability Index (PSI)
=============================================================
What This Tests:
  Can you implement production-grade monitoring for ML models?
  - Calculate PSI (Population Stability Index) to detect distribution shifts.
  - Understand the difference between feature drift and target drift.
  - Implement a monitoring script that flags 'out-of-stability' features.

Why it matters (Postpay Context):
  "At Postpay, if the profile of drivers applying for loans changed 
  (e.g., more new drivers vs veterans), the model's performance 
  would decay. We used PSI to detect this shift early."

Thresholds:
  PSI < 0.1  : No significant shift (Stable)
  PSI < 0.25 : Moderate shift (Monitor)
  PSI >= 0.25: Significant shift (Action/Retrain)

Run: python e03_data_drift_monitor.py
=============================================================
"""

import numpy as np
import pandas as pd

def calculate_psi(expected, actual, buckets=10):
    """
    Calculate the Population Stability Index (PSI) between two distributions.
    
    expected: Reference distribution (e.g., Training data)
    actual:   Current distribution (e.g., Production data)
    """
    
    def get_probabilities(data, breakpoints):
        """Calculate the percentage of data points in each bucket."""
        counts = np.histogram(data, bins=breakpoints)[0]
        return counts / len(data)

    # 1. Define breakpoints based on the EXPECTED distribution (quantiles)
    # Using quantiles ensures roughly equal distribution in the baseline
    breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))
    
    # 2. Add small epsilon to handle edge cases where min/max are same
    breakpoints[0] -= 0.0001
    breakpoints[-1] += 0.0001
    
    # 3. Get proportions for each bucket
    expected_percents = get_probabilities(expected, breakpoints)
    actual_percents = get_probabilities(actual, breakpoints)
    
    # 4. Handle zeros to avoid infinity in log (Smoothing)
    expected_percents = np.where(expected_percents == 0, 0.0001, expected_percents)
    actual_percents = np.where(actual_percents == 0, 0.0001, actual_percents)
    
    # 5. Calculate PSI component: (Actual% - Expected%) * ln(Actual% / Expected%)
    psi_values = (actual_percents - expected_percents) * np.log(actual_percents / expected_percents)
    
    return np.sum(psi_values)

# ──────────────────────────────────────────────────────────────
# Simulation: Monitoring Driver Earnings Drift
# ──────────────────────────────────────────────────────────────

def monitor_drift_simulation():
    print("="*60)
    print("  E03 — DATA DRIFT MONITORING (PSI)")
    print("="*60)
    
    # Simulate Training Data (Baseline)
    # Most drivers earn around 1200
    np.random.seed(42)
    training_earnings = np.random.normal(1200, 300, 1000)
    
    # Scenario 1: Stable Production Data (Similar to training)
    stable_prod_earnings = np.random.normal(1210, 310, 1000)
    
    # Scenario 2: Moderate Drift (Slightly higher earnings)
    moderate_drift_earnings = np.random.normal(1350, 300, 1000)
    
    # Scenario 3: Significant Drift (Economic shift - much lower earnings)
    significant_drift_earnings = np.random.normal(800, 200, 1000)
    
    scenarios = [
        ("Stable Production", stable_prod_earnings),
        ("Moderate Drift", moderate_drift_earnings),
        ("Significant Drift", significant_drift_earnings)
    ]
    
    print(f"\nBaseline Median Earnings: {np.median(training_earnings):.2f}")
    print("-" * 60)
    
    for label, data in scenarios:
        psi = calculate_psi(training_earnings, data)
        
        status = "[OK] STABLE"
        if 0.1 <= psi < 0.25:
            status = "[!] MONITOR"
        elif psi >= 0.25:
            status = "[!!] ACTION REQUIRED"
            
        print(f"Scenario: {label:<20} | PSI: {psi:.4f} | Status: {status}")
        print(f"  New Median: {np.median(data):.2f}")
    
    print("\n" + "="*60)
    print("Summary for Interview:")
    print("1. PSI is the industry standard for detecting population shift.")
    print("2. I monitor PSI for key features (Earnings, Bureau Score) weekly.")
    print("3. PSI > 0.25 is my hard trigger for model retraining or feature investigation.")

if __name__ == "__main__":
    monitor_drift_simulation()
