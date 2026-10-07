import pandas as pd

def analyze_kpis(csv_path="crm_conversion_data.csv"):
    print("Loading CRM data...")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: Could not find {csv_path}. Run generate_mock_data.py first.")
        return

    # Convert date strings to datetime objects for calculations
    df['lead_date'] = pd.to_datetime(df['lead_date'])
    df['first_deposit_date'] = pd.to_datetime(df['first_deposit_date'])
    df['first_trade_date'] = pd.to_datetime(df['first_trade_date'])

    print("-" * 50)
    print("ANAX CAPITAL - MARKETING & SALES KPI SCORECARD")
    print("-" * 50)

    # General KPIs
    total_leads = len(df)
    total_depositors = df['first_deposit_date'].notna().sum()
    total_traders = df['first_trade_date'].notna().sum()
    
    print(f"Total Leads: {total_leads}")
    print(f"Total Depositors: {total_depositors} ({(total_depositors/total_leads)*100:.2f}% conversion)")
    print(f"Total Active Traders: {total_traders} ({(total_traders/total_depositors)*100:.2f}% of depositors)")
    print("-" * 50)

    # Time to Conversion Analysis
    df['days_to_deposit'] = (df['first_deposit_date'] - df['lead_date']).dt.days
    df['days_to_trade'] = (df['first_trade_date'] - df['first_deposit_date']).dt.days
    df['day_1_retention'] = df['days_to_trade'] <= 1

    # Campaign Performance Analysis
    print("CAMPAIGN PERFORMANCE (Lead -> Deposit -> Trade):")
    
    # Aggregate data by campaign
    campaign_kpis = df.groupby('marketing_campaign').agg(
        total_leads=('user_id', 'count'),
        depositors=('first_deposit_date', 'count'),
        avg_days_to_deposit=('days_to_deposit', 'mean'),
        traders=('first_trade_date', 'count'),
        avg_days_deposit_to_trade=('days_to_trade', 'mean'),
        total_volume=('total_volume_traded_30_days', 'sum')
    ).reset_index()

    day_1_trades = df[df['day_1_retention'] == True].groupby('marketing_campaign').size().reset_index(name='day_1_trade_count')
    campaign_kpis = pd.merge(campaign_kpis, day_1_trades, on='marketing_campaign', how='left')
    
    # Calculate Derived Metrics
    campaign_kpis['lead_to_dep_conversion(%)'] = (campaign_kpis['depositors'] / campaign_kpis['total_leads']) * 100
    campaign_kpis['Day_1_trade_activation(%)'] = (campaign_kpis['day_1_trade_count'] / campaign_kpis['depositors']) * 100
    # Fill NAs
    campaign_kpis['Day_1_trade_activation(%)'] = campaign_kpis['Day_1_trade_activation(%)'].fillna(0)

    # Format the numeric outputs for a clean terminal presentation
    pd.options.display.float_format = '{:.2f}'.format
    display_cols = [
        'marketing_campaign', 'total_leads', 'lead_to_dep_conversion(%)', 
        'avg_days_to_deposit', 'avg_days_deposit_to_trade', 
        'Day_1_trade_activation(%)', 'total_volume'
    ]
    
    print(campaign_kpis[display_cols].to_string(index=False))
    print("-" * 50)

if __name__ == "__main__":
    analyze_kpis()
