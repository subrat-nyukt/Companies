"""
Production Transactional Outbox & Self-Healing Reconciler Pattern
===================================================================
Prevents State Drift between SQL Database and Vector Database in Voice Agents.

Architectural Pattern:
1. Voice Agent writes SQL Record + Outbox Event inside a SINGLE ACID SQL Transaction.
2. Async Outbox Worker consumes Outbox events and upserts to Vector DB idempotently.
3. Self-Healing Reconciler cron job periodically catches and repairs any orphaned state drift.
"""

import asyncio
import uuid
import time
import json
from typing import Dict, List, Optional


# =========================================================================
# Simulated Databases
# =========================================================================

class MockSQLDatabase:
    def __init__(self):
        self.call_logs: Dict[str, dict] = {}
        self.outbox_events: Dict[str, dict] = {}

    def execute_transactional_outbox_write(self, call_id: str, transcript: str, patient_id: str):
        """
        ACID Transaction: Writes both the Call Record and the Outbox Event.
        Either BOTH succeed or BOTH fail together.
        """
        # Step A: Save structured call record
        self.call_logs[call_id] = {
            "call_id": call_id,
            "patient_id": patient_id,
            "transcript": transcript,
            "vector_sync_status": "PENDING",  # PENDING, SYNCED, FAILED
            "created_at": time.time()
        }
        
        # Step B: Save Outbox Event inside SAME transaction
        outbox_id = f"evt_{uuid.uuid4().hex[:8]}"
        self.outbox_events[outbox_id] = {
            "outbox_id": outbox_id,
            "call_id": call_id,
            "event_type": "UPSERT_VECTOR_MEMORY",
            "payload": {"call_id": call_id, "transcript": transcript},
            "status": "UNPROCESSED",          # UNPROCESSED, PROCESSED, FAILED
            "retry_count": 0,
            "created_at": time.time()
        }
        print(f"🔒 [SQL ACID TX] Successfully committed Call Record '{call_id}' & Outbox Event '{outbox_id}'")


class MockVectorDatabase:
    def __init__(self, fail_rate_simulation: bool = False):
        self.vectors: Dict[str, dict] = {}
        self.fail_rate_simulation = fail_rate_simulation

    def upsert_vector(self, call_id: str, embedding_vector: List[float], metadata: dict):
        """Simulates Vector DB Upsert (Qdrant / Chroma / Pinecone)."""
        if self.fail_rate_simulation and call_id == "call_fail_demo":
            raise ConnectionError("💥 Vector DB Network Timeout / Cluster Outage!")

        self.vectors[call_id] = {
            "id": call_id,
            "vector": embedding_vector,
            "metadata": metadata
        }
        print(f"🌲 [Vector DB] Successfully upserted vector for call_id: {call_id}")


# Initialize DBs
sql_db = MockSQLDatabase()
vector_db = MockVectorDatabase(fail_rate_simulation=True)


# =========================================================================
# Pattern 1: Async Outbox Worker (Decoupled Reliable Sync)
# =========================================================================

async def process_outbox_events():
    """
    Background Worker: Polls SQL Outbox table, processes vector embeddings,
    and updates SQL status once Vector DB acknowledges receipt.
    """
    unprocessed_events = [
        e for e in sql_db.outbox_events.values() 
        if e["status"] == "UNPROCESSED" and e["retry_count"] < 3
    ]

    for event in unprocessed_events:
        outbox_id = event["outbox_id"]
        call_id = event["call_id"]
        transcript = event["payload"]["transcript"]

        try:
            # 1. Generate Embedding (Simulated)
            mock_embedding = [0.12, 0.45, 0.88, 0.23]

            # 2. Upsert to Vector DB idempotently
            vector_db.upsert_vector(
                call_id=call_id,
                embedding_vector=mock_embedding,
                metadata={"transcript": transcript}
            )

            # 3. Mark Outbox as PROCESSED & SQL Record as SYNCED
            event["status"] = "PROCESSED"
            sql_db.call_logs[call_id]["vector_sync_status"] = "SYNCED"
            print(f"✅ [Outbox Worker] Event {outbox_id} processed. State in SYNC.")

        except Exception as e:
            event["retry_count"] += 1
            print(f"⚠️ [Outbox Worker Error] Event {outbox_id} failed (Retry {event['retry_count']}): {e}")
            if event["retry_count"] >= 3:
                event["status"] = "FAILED"
                sql_db.call_logs[call_id]["vector_sync_status"] = "FAILED"


# =========================================================================
# Pattern 2: Self-Healing Reconciliation Cron Job
# =========================================================================

async def run_state_drift_reconciler():
    """
    Self-Healing Cron Job: Runs periodically (e.g. hourly) to detect and repair
    any state drift between SQL DB and Vector DB.
    """
    print("\n🔍 [RECONCILER] Running periodic State Drift Audit...")
    
    # Identify Unsynced / Failed SQL Records older than threshold
    drifted_records = [
        call for call in sql_db.call_logs.values()
        if call["vector_sync_status"] in ["PENDING", "FAILED"]
    ]

    print(f"📊 [RECONCILER] Found {len(drifted_records)} drifted records requiring repair.")

    for record in drifted_records:
        c_id = record["call_id"]
        
        # Check if vector actually exists in Vector DB
        if c_id not in vector_db.vectors:
            print(f"🛠️ [RECONCILER] Repairing missing vector for call_id: {c_id}...")
            try:
                # Force repair re-upsert
                vector_db.fail_rate_simulation = False  # Resolve simulated outage
                vector_db.upsert_vector(
                    call_id=c_id,
                    embedding_vector=[0.12, 0.45, 0.88, 0.23],
                    metadata={"transcript": record["transcript"]}
                )
                record["vector_sync_status"] = "SYNCED"
                print(f"🎉 [RECONCILER] Successfully repaired state drift for call_id: {c_id}")
            except Exception as ex:
                print(f"❌ [RECONCILER] Repair failed: {ex}")


# =========================================================================
# Demonstration Simulation
# =========================================================================

async def main():
    print("🚀 --- SIMULATION: Voice Agent Ending Call & Writing State ---")
    
    # 1. Normal Call (Succeeds)
    sql_db.execute_transactional_outbox_write(
        call_id="call_success_001",
        transcript="Patient reported mild fever and requested appointment.",
        patient_id="patient_101"
    )

    # 2. Failing Call (Vector DB connection drops)
    sql_db.execute_transactional_outbox_write(
        call_id="call_fail_demo",
        transcript="Patient inquired about prescription refill.",
        patient_id="patient_102"
    )

    print("\n🚀 --- OUTBOX WORKER RUN 1 ---")
    await process_outbox_events()

    print("\n🚀 --- RECONCILER CRON JOB RUN (Self-Healing State Drift) ---")
    await run_state_drift_reconciler()

if __name__ == "__main__":
    asyncio.run(main())
