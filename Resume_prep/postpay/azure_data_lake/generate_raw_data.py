import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_raw_tables(n_customers=100, n_orders=500):
    np.random.seed(42)
    fake = pd.DataFrame() # Just a placeholder
    
    print("Generating Raw Data for Azure Databricks upload...")

    # ==========================================
    # 1. Customers Table
    # ==========================================
    customer_ids = [f"CUST_{i:04d}" for i in range(n_customers)]
    
    customers_data = []
    for cid in customer_ids:
        # random join date in last 2 years
        days_ago = np.random.randint(1, 730)
        join_date = datetime.now() - timedelta(days=days_ago)
        
        # ID number starting with 784 (UAE) + random birth year logic for age
        birth_year = np.random.randint(1970, 2005)
        id_number = f"784-{birth_year}-1234567-1"
        
        customers_data.append({
            'customer_id': cid,
            'created': join_date.strftime("%Y-%m-%d %H:%M:%S"),
            'id_number': id_number
        })
    
    df_customers = pd.DataFrame(customers_data)
    df_customers.to_csv('raw_customers.csv', index=False)
    print(f"1. raw_customers.csv created ({len(df_customers)} rows)")

    # ==========================================
    # 2. Orders Table
    # ==========================================
    orders_data = []
    
    # Merchant definitions
    merchants = ['Amazon', 'Noon', 'Namshi', 'Carrefour', 'IKEA']
    banks = ['Emirates NBD', 'ADCB', 'Mashreq', 'HSBC', 'Citi Bank']
    
    for i in range(n_orders):
        order_id = f"ORD_{i:05d}"
        cust_id = np.random.choice(customer_ids)
        
        # Date logic: recently or old
        days_ago = np.random.randint(0, 365)
        order_date = datetime.now() - timedelta(days=days_ago)
        
        amount = round(np.random.uniform(100, 5000), 2)
        
        # Payment details
        payment_method = np.random.choice(['debit', 'credit'], p=[0.6, 0.4])
        card_brand = np.random.choice(['visa', 'mastercard', 'amex'], p=[0.5, 0.4, 0.1])
        bank = np.random.choice(banks)
        is_apple_pay = np.random.choice(['true', 'false'], p=[0.3, 0.7])
        
        orders_data.append({
            'customer_id': cust_id,
            'order_id': order_id,
            'created': order_date.strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'captured', # Mostly successful
            'total_amount': amount,
            'currency': 'AED',
            'num_instalments': 3,
            'card_first_six_digits': '123456',
            'card_last_four_digits': '7890',
            'is_apple_pay': is_apple_pay,
            'payment_method_type': payment_method,
            'payment_method_brand': card_brand,
            'payment_method_bank': bank,
            'payment_method_expires': (order_date + timedelta(days=700)).strftime("%Y-%m-%d"),
            'user_agent': np.random.choice(['iPhone', 'Android', 'Windows'], p=[0.5, 0.4, 0.1]),
            'merchant_id': np.random.choice(merchants)
        })
        
    df_orders = pd.DataFrame(orders_data)
    df_orders.to_csv('raw_orders.csv', index=False)
    print(f"2. raw_orders.csv created ({len(df_orders)} rows)")

    # ==========================================
    # 3. Instalment Plans Table (Linked to Orders)
    # ==========================================
    plans_data = []
    
    for idx, row in df_orders.iterrows():
        plan_id = f"PLAN_{idx:05d}"
        
        # Default logic
        # 10% chance of being 'unpaid' or 'due' if the customer is "risky" (randomly assigned here)
        status = np.random.choice(['paid', 'unpaid', 'due'], p=[0.85, 0.10, 0.05])
        
        unpaid_amt = 0
        if status == 'unpaid':
            unpaid_amt = row['total_amount'] / 3 # one installment unpaid
            
        plans_data.append({
            'customer_id': row['customer_id'],
            'instalment_plan_id': plan_id,
            'order_id': row['order_id'],
            'created': row['created'],
            'instalment_plan_status': status,
            'status': 'captured',
            'num_instalments': 3,
            'currency': 'AED',
            'downpayment_refunded_amount': 0,
            'total_amount': row['total_amount'],
            'total_downpayment': row['total_amount'] / 3,
            'total_amount_unpaid': unpaid_amt,
            'total_amount_due': 0 if status == 'paid' else (row['total_amount'] / 3)
        })

    df_plans = pd.DataFrame(plans_data)
    df_plans.to_csv('raw_instalment_plans.csv', index=False)
    print(f"3. raw_instalment_plans.csv created ({len(df_plans)} rows)")
    
    print("\nSUCCESS! You can now upload these 3 files to Azure Data Lake.")

if __name__ == "__main__":
    generate_raw_tables()
