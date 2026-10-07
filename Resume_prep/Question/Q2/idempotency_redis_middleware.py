"""
Production-Grade Idempotency Middleware using FastAPI and Redis
================================================================
Prevents duplicate LLM API executions, duplicate charges, and race conditions.

How it Works:
1. Extracts or generates a unique `idempotency_key` (SHA256 of user + payload).
2. Checks Redis distributed lock:
   - If 'COMPLETED': Return cached response instantly (0 compute / 0 LLM tokens).
   - If 'PROCESSING': Reject duplicate concurrent request (HTTP 409 Conflict).
   - If NOT FOUND: Set lock to 'PROCESSING', execute task, store result, set status to 'COMPLETED'.
"""

import hashlib
import json
import time
from typing import Callable, Optional
from fastapi import FastAPI, Request, Response, HTTPException, Header
import redis.asyncio as aioredis

app = FastAPI(title="Idempotent LLM Serving Gateway")

# Connect to Redis
redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=True)

# Key configuration
IDEMPOTENCY_TTL_SECONDS = 86400  # Cache idempotency state for 24 hours


def generate_idempotency_key(user_id: str, payload: dict) -> str:
    """
    Generates a deterministic SHA-256 Hash if client didn't supply an Idempotency-Key header.
    Hash = SHA256(user_id + canonical_json_payload)
    """
    canonical_payload = json.dumps(payload, sort_keys=True)
    raw_string = f"{user_id}:{canonical_payload}"
    return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()


async def execute_idempotent_request(
    idempotency_key: str,
    handler_func: Callable,
    *args,
    **kwargs
) -> dict:
    """
    Core Idempotency Engine wrapped around any expensive LLM / Payment function.
    """
    redis_key = f"idempotency:{idempotency_key}"

    # 1. Check if Idempotency Key exists in Redis
    cached_data = await redis_client.get(redis_key)

    if cached_data:
        record = json.loads(cached_data)
        status = record.get("status")

        if status == "COMPLETED":
            print(f"⚡ IDEMPOTENCY HIT! Returning cached result for key: {idempotency_key}")
            return record.get("response")
        
        elif status == "PROCESSING":
            print(f"⚠️ CONCURRENT DUPLICATE DETECTED! Key {idempotency_key} is currently processing.")
            raise HTTPException(
                status_code=409, 
                detail="Duplicate request currently in progress. Please wait for completion."
            )

    # 2. Acquire Redis Lock: Set state to 'PROCESSING' atomically
    # SETNX (Set if Not Exists) with a 60-second processing timeout
    lock_acquired = await redis_client.set(
        redis_key,
        json.dumps({"status": "PROCESSING", "created_at": time.time()}),
        nx=True,
        ex=60  # Lock expires in 60 seconds if worker crashes
    )

    if not lock_acquired:
        # Race condition: Another worker grabbed the lock a millisecond ago!
        raise HTTPException(
            status_code=409,
            detail="Concurrent request detected. Work already in progress."
        )

    # 3. Execute the actual expensive operation (e.g. LLM call or Payment transaction)
    try:
        print(f"⚙️ EXECUTING HEAVY LLM TASK for key: {idempotency_key}...")
        result = await handler_func(*args, **kwargs)

        # 4. Save final result in Redis with status 'COMPLETED' (24-hour TTL)
        await redis_client.set(
            redis_key,
            json.dumps({"status": "COMPLETED", "response": result}),
            ex=IDEMPOTENCY_TTL_SECONDS
        )

        return result

    except Exception as e:
        # If execution fails, delete the lock so retries can try again!
        await redis_client.delete(redis_key)
        raise e


# =========================================================
# Practical API Endpoint Example: Expensive LLM Chat
# =========================================================

async def mock_expensive_llm_call(prompt: str) -> dict:
    """Simulates an expensive 3-second vLLM / OpenAI API call."""
    await asyncio.sleep(3.0)  # Simulating LLM generation latency
    return {
        "text": f"Response generated for prompt: '{prompt}'",
        "tokens_used": 150,
        "cost_usd": 0.0025
    }


@app.post("/v1/chat/completions")
async def chat_endpoint(
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    body = await request.json()
    user_id = body.get("user_id", "anonymous_user")
    prompt = body.get("prompt", "")

    # If client didn't supply an explicit header, generate deterministic hash from payload
    if not idempotency_key:
        idempotency_key = generate_idempotency_key(user_id, body)

    # Execute request idempotently
    result = await execute_idempotent_request(
        idempotency_key=idempotency_key,
        handler_func=mock_expensive_llm_call,
        prompt=prompt
    )

    return {"idempotency_key": idempotency_key, "result": result}
