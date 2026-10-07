import time
import random

def extract_identity_info(image_path: str) -> dict:
    """
    Mock function representing OCR/Data Extraction from an ID.
    In production, this would call AWS Textract, Azure Document Intelligence, or similar.
    """
    time.sleep(1) # Simulate processing
    return {
        "status": "success",
        "doc_type": "passport",
        "first_name": "JOHN",
        "last_name": "DOE",
        "dob": "1990-01-01",
        "nationality": "US",
        "document_number": "A12345678"
    }

def run_sanction_screening(name: str) -> dict:
    """
    Mock function representing AML/PEP checks against a database or external API.
    """
    time.sleep(1)
    
    # Simulate a hit for demo purposes if exact name matched
    if name.upper() == "OSAMA":
        return {
            "status": "flagged",
            "reason": "Match found on OFAC sanctions list",
            "score": 0.99
        }
    
    return {
        "status": "clear",
        "reason": "No matches found on PEP/Sanctions list",
        "score": 0.01
    }

def verify_liveness(video_path: str) -> dict:
    """
    Mock function representing facial liveness checks.
    """
    time.sleep(1)
    score = random.uniform(0.85, 0.99)
    return {
        "status": "passed" if score > 0.9 else "failed",
        "liveness_score": round(score, 3),
        "message": "User is a live person" if score > 0.9 else "Liveness check failed."
    }
