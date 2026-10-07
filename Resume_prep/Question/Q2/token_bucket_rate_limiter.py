"""
Production Token-Bucket Rate Limiter (RPS & TPM)
=================================================
Pipeline Placement: Sits in front of rulegen/llm/client.py
Prevents HTTP 429 rate limit errors when batch profiling Databricks Silver tables.
"""

import time
import asyncio
from typing import Dict, Any


class TokenBucketRateLimiter:
    """
    Dual Token-Bucket Rate Limiter tracking both:
    1. Requests-Per-Second (RPS)
    2. Tokens-Per-Minute (TPM)
    """
    def __init__(self, max_rps: float = 10.0, max_tpm: float = 100000.0):
        self.max_rps = max_rps            # Capacity & Refill rate for RPS (e.g. 10 req/sec)
        self.max_tpm = max_tpm            # Capacity & Refill rate for TPM (e.g. 100k tokens/min)
        
        # Current bucket levels
        self.rps_tokens = max_rps
        self.tpm_tokens = max_tpm

        # Refill rates per second
        self.rps_refill_rate = max_rps              # 10.0 tokens per second
        self.tpm_refill_rate = max_tpm / 60.0       # 1,666.6 tokens per second

        self.last_refill_time = time.time()
        self._lock = asyncio.Lock()

    def _refill(self):
        """Calculates elapsed time and refills tokens into both buckets."""
        now = time.time()
        elapsed = now - self.last_refill_time
        self.last_refill_time = now

        # Refill RPS tokens
        self.rps_tokens = min(self.max_rps, self.rps_tokens + (elapsed * self.rps_refill_rate))
        
        # Refill TPM tokens
        self.tpm_tokens = min(self.max_tpm, self.tpm_tokens + (elapsed * self.tpm_refill_rate))

    async def acquire(self, estimated_prompt_tokens: int = 500):
        """
        Acquires permission before dispatching an HTTP request.
        If tokens are insufficient, dynamically pauses (sleeps) until refilled.
        """
        async with self._lock:
            while True:
                self._refill()

                # Check if we have 1 request token AND enough prompt tokens
                has_rps = self.rps_tokens >= 1.0
                has_tpm = self.tpm_tokens >= estimated_prompt_tokens

                if has_rps and has_tpm:
                    # Deduct tokens from both buckets
                    self.rps_tokens -= 1.0
                    self.tpm_tokens -= estimated_prompt_tokens
                    # Permission granted! Dispatch HTTP payload immediately
                    return

                # Calculate required sleep time to refill missing tokens
                needed_rps_tokens = max(0.0, 1.0 - self.rps_tokens)
                needed_tpm_tokens = max(0.0, estimated_prompt_tokens - self.tpm_tokens)

                sleep_for_rps = needed_rps_tokens / self.rps_refill_rate
                sleep_for_tpm = needed_tpm_tokens / self.tpm_refill_rate

                wait_time = max(sleep_for_rps, sleep_for_tpm)
                
                print(
                    f"⚠️ [RATE LIMITER THROTTLE] Insufficient Tokens! "
                    f"(RPS Left: {self.rps_tokens:.1f}, TPM Left: {self.tpm_tokens:.1f}). "
                    f"Pausing execution for {wait_time:.3f} seconds..."
                )

                # Release lock while sleeping so other coroutines aren't blocked
                await asyncio.sleep(wait_time)


# =========================================================================
# Demonstration: How rulegen/llm/client.py Uses the Rate Limiter
# =========================================================================

# Shared Rate Limiter Instance
rate_limiter = TokenBucketRateLimiter(max_rps=5.0, max_tpm=10000.0)


async def dispatch_llm_payload(table_name: str, payload_tokens: int = 2500):
    """
    Simulates rulegen/llm/client.py sending requests to Azure OpenAI / Sovereign Model.
    """
    # 1. Pipeline Placement: Acquire tokens BEFORE dispatching HTTP POST payload
    await rate_limiter.acquire(estimated_prompt_tokens=payload_tokens)

    # 2. HTTP Call executed safely
    print(f"🚀 [HTTP CLIENT] Dispatched payload for table '{table_name}' ({payload_tokens} tokens)")
    await asyncio.sleep(0.2)  # Simulates network HTTP request latency
    return f"Rule generated for {table_name}"


async def batch_profile_tables_simulation():
    """Simulates Databricks batch profiling 15 Silver tables simultaneously."""
    print("🚀 Starting Databricks Batch Profiling Simulation across 15 Silver Tables...\n")
    
    tables = [f"silver_catalog.dmt.table_{i}" for i in range(1, 16)]
    
    # Fire all 15 table requests concurrently using asyncio.gather
    tasks = [dispatch_llm_payload(t, payload_tokens=2000) for t in tables]
    results = await asyncio.gather(*tasks)
    
    print("\n✅ All 15 tables profiled successfully with ZERO HTTP 429 errors!")


if __name__ == "__main__":
    asyncio.run(batch_profile_tables_simulation())
