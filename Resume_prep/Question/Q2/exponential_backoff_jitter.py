"""
Production-Grade Exponential Backoff with Random Jitter
======================================================
Solves transient API errors (HTTP 429 / 503) and prevents the 'Thundering Herd' problem.

Math Formula:
Wait Time = min(Max_Cap, (Base_Rate * 2 ^ attempt) + Full_Jitter)
"""

import asyncio
import random
import time
import httpx
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type


# =========================================================================
# Approach 1: Custom Python Implementation from Scratch (To Understand Math)
# =========================================================================

async def execute_with_backoff_and_jitter(
    func,
    *args,
    max_retries: int = 5,
    base_rate: float = 1.0,
    max_backoff: float = 32.0,
    **kwargs
):
    """
    Executes an async function with Exponential Backoff and Full Jitter.
    """
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            # Check if error is transient (429 Rate Limit or 5xx Server Error)
            status_code = getattr(exc.response, "status_code", None)
            is_transient = status_code in [429, 500, 502, 503, 504] or status_code is None

            if not is_transient or attempt == max_retries - 1:
                print(f"❌ Non-transient error or retries exhausted (Attempt {attempt + 1}). Re-raising exception.")
                raise exc

            # 1. Calculate Pure Exponential Backoff: Base * 2^attempt
            raw_backoff = base_rate * (2 ** attempt)

            # 2. Cap backoff to maximum threshold (e.g. 32s)
            capped_backoff = min(max_backoff, raw_backoff)

            # 3. Add Full Jitter: Uniform random float between 0 and capped_backoff
            # Full Jitter = random.uniform(0, capped_backoff)
            sleep_time = random.uniform(0.5 * capped_backoff, capped_backoff)

            print(
                f"⚠️ Transient Error (HTTP {status_code}). "
                f"Attempt {attempt + 1}/{max_retries} failed. "
                f"Backoff math: raw={raw_backoff:.1f}s, capped={capped_backoff:.1f}s -> "
                f"Sleeping for {sleep_time:.2f}s with random jitter..."
            )

            await asyncio.sleep(sleep_time)


# =========================================================================
# Approach 2: Production Standard Using 'tenacity' Library (Recommended)
# =========================================================================

# Decorator automatically handles Exponential Backoff + Jitter for OpenAI / vLLM calls
@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(min=1, max=32), # Exponential + Jitter automatically!
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError))
)
async def call_llm_api_tenacity(prompt: str):
    """
    Production decorated function for reliable API invocation.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json={"model": "llama-3", "messages": [{"role": "user", "content": prompt}]},
            timeout=5.0
        )
        response.raise_for_status()
        return response.json()


# =========================================================================
# Demonstration / Simulation Script
# =========================================================================

# Mock unreliable API function to simulate 429 throttling
attempt_counter = 0

async def mock_unreliable_api():
    global attempt_counter
    attempt_counter += 1
    if attempt_counter < 4:
        # Simulate HTTP 429 Rate Limit error for first 3 attempts
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        response = httpx.Response(429, request=request)
        raise httpx.HTTPStatusError("Rate Limit Exceeded", request=request, response=response)
    
    return {"status": "SUCCESS", "message": "API call succeeded on attempt 4!"}


async def main():
    print("🚀 Demonstrating Exponential Backoff with Random Jitter...\n")
    result = await execute_with_backoff_and_jitter(mock_unreliable_api, max_retries=5)
    print("\n✅ Final Result:", result)

if __name__ == "__main__":
    asyncio.run(main())
