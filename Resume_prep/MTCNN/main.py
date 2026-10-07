from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from src.services.verification import VerificationService
from src.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Real-time Face Detection and Identity Verification using MTCNN & FaceNet"
)

# Initialize Core Service
verification_service = VerificationService()

@app.post("/api/v1/register")
async def register(user_id: str = Form(...), file: UploadFile = File(...)):
    """
    Onboard a new user by generating and storing their facial embedding.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    
    image_bytes = await file.read()
    result = verification_service.register_user(user_id, image_bytes)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
        
    return JSONResponse(content=result)

@app.post("/api/v1/verify")
async def verify(user_id: str = Form(...), file: UploadFile = File(...)):
    """
    Verify an existing user in real-time by comparing their live image against the stored embedding.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
        
    image_bytes = await file.read()
    result = verification_service.verify_user(user_id, image_bytes)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
        
    return JSONResponse(content=result)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
