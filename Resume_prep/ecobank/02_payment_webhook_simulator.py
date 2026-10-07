import json
import logging
import hashlib
import time

# Configure simple logging to represent standard backend logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - Webhook Simulator - %(levelname)s - %(message)s')

def verify_webhook_signature(payload, signature):
    """
    Simulates checking a security signature from a telecom provider.
    In real life, this ensures the webhook actually came from MTN/Airtel/etc.
    """
    # Dummy secret key for demonstration
    secret = "ecobank_super_secret_key_2024"
    expected_hash = hashlib.sha256(f"{payload}{secret}".encode()).hexdigest()
    
    # In a real scenario, we'd compare expected_hash with the incoming signature
    return True # Simplifying for the simulation

def process_webhook(request_body):
    """
    Simulates the backend endpoint that receives POST requests from mobile money providers.
    """
    try:
        data = json.loads(request_body)
        
        # 1. Validation
        if not all(k in data for k in ('transaction_id', 'status', 'amount')):
            logging.error("Invalid Webhook: Missing required fields")
            return {"status": 400, "message": "Bad Request"}
            
        # 2. Security Check
        # Assuming 'X-Signature' is passed in headers in real life
        if not verify_webhook_signature(request_body, "dummy_sig"):
             logging.warning("Unauthorized Webhook attempt!")
             return {"status": 401, "message": "Unauthorized"}
        
        # 3. Processing
        txn_id = data['transaction_id']
        status = data['status']
        
        logging.info(f"Received update for TXN: {txn_id}. Status: {status}. Source: {data.get('provider', 'Unknown')}")
        
        # Here you would typically write to a database:
        # db.execute("UPDATE transactions SET status = %s WHERE id = %s", (status, txn_id))
        
        return {"status": 200, "message": "Webhook processed successfully"}

    except json.JSONDecodeError:
        logging.error("Invalid JSON payload")
        return {"status": 400, "message": "Invalid JSON"}

if __name__ == "__main__":
    print("--- Starting Webhook Processing Simulation ---")
    
    # Simulating an incoming webhook payload from a Telecom
    mock_payload_1 = json.dumps({
        "transaction_id": "TXN_774829",
        "merchant_id": "MERCH_0012",
        "amount": 250.00,
        "provider": "MTN_MOMO",
        "status": "SUCCESS",
        "timestamp": "2024-05-15T14:32:00Z"
    })
    
    process_webhook(mock_payload_1)
    time.sleep(1)
    
    # Simulating a failed transaction webhook
    mock_payload_2 = json.dumps({
        "transaction_id": "TXN_991122",
        "amount": 1000.00,
        "provider": "AIRTEL_MONEY",
        "status": "FAILED",
        "reason": "Insufficient Funds"
    })
    
    process_webhook(mock_payload_2)
    
    print("--- Simulation Complete ---")
