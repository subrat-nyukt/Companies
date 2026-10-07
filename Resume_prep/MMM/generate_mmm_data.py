import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_truck_driver_mmm_data(start_date='2023-01-01', weeks=104):
    """
    Generates a synthetic dataset for Marketing Mix Modeling (MMM)
    Targeting: Truck Drivers 
    Product: Fintech Prepaid Cards (Fuel discounts, instant settlement)
    """
    np.random.seed(42)
    
    # Generate weekly dates
    dates = [datetime.strptime(start_date, '%Y-%m-%d') + timedelta(weeks=i) for i in range(weeks)]
    
    # 1. Base Demand/Trend (Organic signups with slight upward trend over 2 years)
    base_demand = np.linspace(50, 150, weeks)
    
    # 2. Seasonality (Trucking has peaks in late Q3/Q4 for holiday freight)
    # Sinusoidal wave to simulate yearly seasonality, peaking around November
    t = np.arange(weeks)
    seasonality = 30 * np.sin(2 * np.pi * (t - 30) / 52) 
    
    # 3. Macro / Control Variables
    # Diesel Prices (High prices might drive demand for a card that offers fuel cash-back)
    diesel_price = np.random.normal(loc=4.0, scale=0.5, size=weeks) + np.linspace(0, 0.5, weeks)
    
    # Freight Volume Index (e.g., DAT load board index - higher volume = more drivers working)
    freight_index = np.random.normal(loc=100, scale=10, size=weeks) + seasonality * 0.5
    
    # 4. Marketing Spend Channels (Weekly Spend in USD)
    # Billboards at major truck stops (Pilot, Flying J, Love's) - steady spend
    billboard_spend = np.random.normal(loc=15000, scale=2000, size=weeks).clip(min=5000)
    
    # AM/Satellite Radio Ads (SiriusXM Road Dog Trucking) - burst campaigns
    radio_spend = np.zeros(weeks)
    radio_spend[::4] = np.random.normal(loc=10000, scale=1500, size=len(radio_spend[::4])) # Ad bursts every 4 weeks
    
    # Digital Ads (Facebook/Instagram targeting CDL/Logistics interests)
    digital_spend = np.random.normal(loc=8000, scale=1000, size=weeks)
    # Increase digital in second year
    digital_spend[52:] += 4000
    
    # Referral Program (Driver-to-Driver "Get $50" Promos)
    referral_spend = np.linspace(2000, 8000, weeks) + np.random.normal(0, 500, weeks)
    
    # 5. Effects and Adstock (Delayed impact of marketing)
    def apply_adstock(spend, retain_rate):
        adstocked = np.zeros(len(spend))
        adstocked[0] = spend[0]
        for i in range(1, len(spend)):
            adstocked[i] = spend[i] + adstocked[i-1] * retain_rate
        return adstocked

    # Truckers take time to switch cards. Billboards and Radio have high adstock (decay slowly). Digital is faster.
    billboard_adstock = apply_adstock(billboard_spend, 0.6)
    radio_adstock = apply_adstock(radio_spend, 0.4)
    digital_adstock = apply_adstock(digital_spend, 0.2)
    referral_adstock = apply_adstock(referral_spend, 0.8) # Word of mouth builds slowly
    
    # 6. Target Variable: New Prepaid Card Setups (Acquisitions)
    # ROAS (Return on Ad Spend) multipliers (Signups per dollar spent)
    # Billboards: Low direct conversion, Radio: Med, Digital: High direct, Referral: Highest
    
    acquisitions = (
        base_demand + 
        seasonality + 
        (diesel_price * 15) + # Higher diesel drives them to seek fuel-discount cards
        (freight_index * 0.5) +
        (billboard_adstock * 0.002) + 
        (radio_adstock * 0.004) + 
        (digital_adstock * 0.008) + 
        (referral_adstock * 0.015) + 
        np.random.normal(0, 20, weeks) # Noise
    ).astype(int)
    
    # Prevent negative signups
    acquisitions = np.clip(acquisitions, a_min=10, a_max=None)

    # 7. Retention & CLV Metrics (To tie into the resume bullet point)
    # Calculate an average CAC and simulated 90-day retention rate based on acquisition channel mix
    # Higher referral mix = better retention. Higher digital = slightly worse retention.
    monthly_retention_rate = 0.65 + (referral_spend / (billboard_spend + radio_spend + digital_spend + referral_spend)) * 0.5
    monthly_retention_rate = np.clip(monthly_retention_rate, 0.60, 0.85)
    
    # Create DataFrame
    df = pd.DataFrame({
        'week_start': dates,
        'new_card_signups': acquisitions,
        'avg_90d_retention_rate': np.round(monthly_retention_rate, 3),
        'billboard_spend': np.round(billboard_spend, 2),
        'radio_spend': np.round(radio_spend, 2),
        'digital_spend': np.round(digital_spend, 2),
        'referral_budget_spend': np.round(referral_spend, 2),
        'diesel_price_usd': np.round(diesel_price, 2),
        'freight_volume_index': np.round(freight_index, 2)
    })
    
    return df

if __name__ == "__main__":
    print("Generating Trucking Fintech MMM Dataset...")
    df = generate_truck_driver_mmm_data()
    file_path = "trucker_fintech_mmm_dataset.csv"
    df.to_csv(file_path, index=False)
    print(f"Dataset generated successfully and saved to: {file_path}")
    print("\nSample Data:")
    print(df.head())
