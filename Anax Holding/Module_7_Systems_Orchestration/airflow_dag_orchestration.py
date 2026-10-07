from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import time

# Global settings for the workflow (Retries, Alerts, etc.)
default_args = {
    'owner': 'anax_data_engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2)
}

# 1. Define the DAG
dag = DAG(
    'anax_client_onboarding_pipeline',
    default_args=default_args,
    description='Orchestrates KYC check, MT5 account creation, and Marketing emails',
    schedule_interval=None, # Triggered via API when a new client signs up
    start_date=datetime(2026, 4, 12),
    catchup=False
)

# --- Python Functions representing API calls to different systems ---

def check_kyc_status(**kwargs):
    client_id = kwargs['dag_run'].conf.get('client_id', 'Unknown')
    print(f"Pinging Jumio API for KYC Status on {client_id}...")
    time.sleep(2)
    print("Response: VERIFIED")
    return "VERIFIED"

def create_mt5_account(**kwargs):
    # Airflow 'XCom' pulls data returned by previous tasks
    kyc_result = kwargs['ti'].xcom_pull(task_ids='check_kyc_task')
    
    if kyc_result != "VERIFIED":
        raise ValueError("CRITICAL ERROR: Cannot provision MT5 account. KYC failed.")
    
    print("Calling MT5 Manager API to create trading account...")
    mt5_login_id = "MT5-889922"
    print(f"Created MT5 Account: {mt5_login_id}")
    return mt5_login_id

def send_welcome_email(**kwargs):
    mt5_login = kwargs['ti'].xcom_pull(task_ids='create_mt5_task')
    print(f"Connecting to Salesforce/Marketing API...")
    print(f"Dispatching welcome email securely injecting Account ID: {mt5_login}...")

# 2. Define the Airflow Tasks
task_1_check_kyc = PythonOperator(
    task_id='check_kyc_task',
    python_callable=check_kyc_status,
    provide_context=True,
    dag=dag
)

task_2_create_mt5 = PythonOperator(
    task_id='create_mt5_task',
    python_callable=create_mt5_account,
    provide_context=True,
    dag=dag
)

task_3_welcome_email = PythonOperator(
    task_id='send_welcome_email_task',
    python_callable=send_welcome_email,
    provide_context=True,
    dag=dag
)

# 3. Define the Directional Flow (The Directed Acyclic Graph)
task_1_check_kyc >> task_2_create_mt5 >> task_3_welcome_email
