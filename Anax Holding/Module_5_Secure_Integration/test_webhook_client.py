import requests

url = "http://127.0.0.1:8000/api/v1/forward_to_vendor"

# This is the extremely sensitive, cleartext data coming out of your highly-secure internal CRM.
mock_crm_payload = {
    "client_id": "ANX-78891",
    "full_name": "Hamza Al Maktoum",
    "email": "hamza.trading@anaxcapital.com",
    "emirates_id": "784-1990-1234567-8",
    "passport_number": "AE123456789X",
    "balance": 150500.00
}

print(f"Firing CLEARTEXT CRM Webhook to Middleware API at {url}...")
print("Waiting for processing...\n")

try:
    response = requests.post(url, json=mock_crm_payload)
    print("=== FINAL VENDOR RECEIPT ===")
    
    import json
    print(json.dumps(response.json(), indent=4))
    
except requests.exceptions.ConnectionError:
    print("[ERROR] Connection failed. Did you start the FastAPI server in terminal 1?")
    print("Run `python secure_webhook_api.py` first!")
