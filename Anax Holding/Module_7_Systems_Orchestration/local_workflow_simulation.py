import time

def check_kyc(client_id):
    print(f"[TASK 1: KYC] Pinging external verification vendor for Client: {client_id}...")
    time.sleep(1.5)
    
    # Change this variable to "REJECTED" to see how orchestration protects your pipeline!
    status = "VERIFIED" 
    
    print(f"[TASK 1: KYC] Result: {status}")
    if status != "VERIFIED":
        raise Exception("Workflow Halted: KYC checks failed.")
    return status

def create_mt5_account(client_id):
    print(f"\n[TASK 2: MT5] Calling MetaTrader API to provision live account...")
    time.sleep(1.5)
    mt5_login = "88991122"
    print(f"[TASK 2: MT5] Success! Generated Login ID: {mt5_login}")
    return mt5_login

def notify_marketing(client_id, mt5_login):
    print(f"\n[TASK 3: MARKETING] Triggering Salesforce webhook...")
    time.sleep(1.5)
    print(f"[TASK 3: MARKETING] Welcome email dispatched! Body: 'Welcome to Anax Capital. Your login is {mt5_login}'.")

def run_pipeline(client_id):
    print("=====================================================")
    print(f"[START] INITIATING ORCHESTRATION PIPELINE FOR {client_id} [START]")
    print("=====================================================\n")
    try:
        # The explicit execution order (The DAG logic)
        kyc_status = check_kyc(client_id)
        
        # We only pass to MT5 if KYC didn't crash the script
        mt5_login = create_mt5_account(client_id)
        
        # We only send an email if MT5 successfully returned a login
        notify_marketing(client_id, mt5_login)
        
        print("\n[SUCCESS] PIPELINE COMPLETED SUCCESSFULLY [SUCCESS]")
    except Exception as e:
        print(f"\n[ERROR] PIPELINE FAILED: {e} [ERROR]")
        print("Subsequent tasks were instantly aborted to prevent non-compliant trading.")
        print("Alerting Risk & Compliance team.")

if __name__ == "__main__":
    test_client = "ANX-001"
    run_pipeline(test_client)
