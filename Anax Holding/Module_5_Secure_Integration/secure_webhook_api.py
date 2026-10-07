from fastapi import FastAPI, Request
from pydantic import BaseModel
import hmac
import hashlib
import json

app = FastAPI(title="Anax Capital - Secure Vendor Middleware")

# 🔐 Security keys (In a real Azure deployment, this is pulled securely from Azure Key Vault)
SECRET_HMAC_KEY = b"anax_super_secret_vendor_key_2026"

# Pydantic model representing the incoming raw CRM payload
class ClientRecord(BaseModel):
    client_id: str
    full_name: str
    email: str
    emirates_id: str
    passport_number: str
    balance: float

# --- Security Functions ---
""""
def mask_email(email:str):

    try:
        name, mail=email.split("@")
        masked_name=name[0]+"*"*(len(name)-1)
        return f'{masked_name}@{mail}'
    except ValueError:
        return email    

def masked_Id(identity_str:str):

    try:
        if len(identity_str)<=4:
            return "****"
        return "*"*(len(identity_str)-4)+identity_str[-4:]
    except ValueError:
        return "****"


"""

def mask_email(email: str) -> str:
    """Mask email left of @ but keep the first letter (e.g., h***@gmail.com)"""
    try:
        name, domain = email.split('@')
        masked_name = name[0] + "*" * (len(name) - 1)
        return f"{masked_name}@{domain}"
    except ValueError:
        return email

def mask_id(identity_str: str) -> str:
    """Mask Identity/Passport IDs, keeping only the last 4 digits safe for logs"""
    if len(identity_str) <= 4:
        return "****"
    return "*" * (len(identity_str) - 4) + identity_str[-4:]

def generate_hmac_signature(payload: dict) -> str:
    """Generate SHA-256 HMAC hash to guarantee data integrity in transit"""
    # Sort keys to ensure the JSON string is identical computationally
    payload_str = json.dumps(payload, sort_keys=True).encode('utf-8')
    signature = hmac.new(SECRET_HMAC_KEY, payload_str, hashlib.sha256).hexdigest()
    return signature

# --- API Endpoints ---

@app.post("/api/v1/forward_to_vendor")
async def secure_vendor_integration(client: ClientRecord):
    print("\n" + "="*60)
    print("[INBOUND] 1. RECEIVED INBOUND WEBHOOK FROM INTERNAL CRM [INBOUND]")
    print(f"Original Cleartext Payload: {client.dict()}")

    # 1. Strip and Mask PII Data
    masked_payload = {
        "client_id": client.client_id,
        "full_name": client.full_name, # Retained for KYC checks usually
        "email": mask_email(client.email),
        "emirates_id": mask_id(client.emirates_id),
        "passport_number": mask_id(client.passport_number),
        "balance": client.balance
    }

    print("\n[MASKING] 2. PII DATA MASKED [MASKING]")
    print(f"Masked Payload: {masked_payload}")

    # 2. Generate Security HMAC Signature
    signature = generate_hmac_signature(masked_payload)
    print("\n[SECURITY] 3. GENERATED HMAC-SHA256 SIGNATURE [SECURITY]")
    print(f"X-Anax-Signature: {signature}")

    # 3. Simulate Forwarding to Vendor API
    headers = {
        "Content-Type": "application/json",
        "X-Anax-Signature": signature
    }

    # In production -> requests.post("https://api.vendor.com/verify", json=masked_payload, headers=headers)
    print("\n[OUTBOUND] 4. FORWARDING TO EXTERNAL VENDOR API [OUTBOUND]")
    print(f"Headers injected: {headers}")
    print("="*60 + "\n")

    return {
        "status": "success",
        "message": "Payload securely masked, signed, and transmitted.",
        "vendor_receipt": {
            "masked_data": masked_payload,
            "hmac_signature": signature
        }
    }

if __name__ == "__main__":
    import uvicorn
    # Ensure you run: pip install fastapi uvicorn
    print("Starting Anax Secure Middleware Server on port 8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
