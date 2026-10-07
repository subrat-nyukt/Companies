"""
Production Back-Pressure Architecture using FastAPI, asyncio Queue & Worker Pools
==================================================================================
Prevents traffic spikes from overwhelming downstream LLM & Database resources.

Key Mechanics:
1. Ingress API accepts request, pushes to Redis/Async Queue, and returns HTTP 202 Accepted instantly.
2. Controlled Worker Pool fetches tasks at a fixed, safe rate (Rate-Limited Consumer).
3. Downstream vLLM / Database runs smoothly without CUDA OOM or DB connection exhaustion.
"""

import asyncio
import uuid
import time
from typing import Dict
from fastapi import FastAPI, HTTPException, BackgroundTasks

app = FastAPI(title="Back-Pressure Decoupled LLM Gateway")

# 1. In-Memory Job Storage & Task Queue (Use Redis Streams / Celery / Azure Service Bus in Production)
task_queue: asyncio.Queue = asyncio.Queue(maxsize=1000) # Buffer capacity
jobs_db: Dict[str, Dict] = {}                            # Database tracking job status

# 2. Back-Pressure Controls: Fixed Concurrency & Rate Limit
MAX_CONCURRENT_WORKERS = 4          # Only 4 workers allowed to touch GPU at once
RATE_LIMIT_DELAY_SECONDS = 0.5      # Minimum delay between worker processing steps


async def vllm_gpu_worker(worker_id: int):
    """
    Background Worker executing tasks at a controlled, safe rate.
    Acts as the 'neck of the funnel' protecting downstream LLM GPU infrastructure.
    """
    print(f"⚙️ Worker-{worker_id} started and waiting for queue tasks...")
    
    while True:
        # Fetch next job from queue
        job_id, prompt = await task_queue.get()
        
        try:
            print(f"🟢 [Worker-{worker_id}] Processing Job: {job_id} (Queue size remaining: {task_queue.qsize()})")
            
            # Update status to PROCESSING
            jobs_db[job_id]["status"] = "PROCESSING"
            jobs_db[job_id]["started_at"] = time.time()

            # SIMULATION: Execute Heavy Downstream LLM GPU Call
            await asyncio.sleep(2.0) # Simulates vLLM GPU inference time
            
            # Rate-limiting back-pressure delay
            await asyncio.sleep(RATE_LIMIT_DELAY_SECONDS)

            # Update status to COMPLETED
            jobs_db[job_id]["status"] = "COMPLETED"
            jobs_db[job_id]["completed_at"] = time.time()
            jobs_db[job_id]["result"] = f"Generated response for: '{prompt}'"
            print(f"✅ [Worker-{worker_id}] Completed Job: {job_id}")

        except Exception as e:
            jobs_db[job_id]["status"] = "FAILED"
            jobs_db[job_id]["error"] = str(e)
        
        finally:
            task_queue.task_done()


@app.on_event("startup")
async def startup_event():
    """Start the fixed worker pool on server startup."""
    for worker_id in range(1, MAX_CONCURRENT_WORKERS + 1):
        asyncio.create_task(vllm_gpu_worker(worker_id))


@app.post("/v1/jobs/submit", status_code=202)
async def submit_job(prompt: str):
    """
    Decoupled Async Endpoint:
    Accepts job instantly (sub-5ms), pushes to Queue, and returns HTTP 202 Accepted.
    Protects downstream infrastructure during 5,000-request bursts!
    """
    # Check if queue buffer is completely full (Queue Overflow Protection)
    if task_queue.full():
        raise HTTPException(
            status_code=503,
            detail="Server queue buffer is at maximum capacity. Please try again later."
        )

    job_id = f"job-{uuid.uuid4().hex[:8]}"
    
    # Store initial job state
    jobs_db[job_id] = {
        "job_id": job_id,
        "prompt": prompt,
        "status": "QUEUED",
        "created_at": time.time()
    }

    # Push to queue (Does NOT execute synchronously!)
    await task_queue.put((job_id, prompt))

    return {
        "job_id": job_id,
        "status": "QUEUED",
        "message": "Job accepted and queued for processing.",
        "poll_url": f"/v1/jobs/{job_id}"
    }


@app.get("/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Client polls this endpoint to check if their background task has completed."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    
    return jobs_db[job_id]
