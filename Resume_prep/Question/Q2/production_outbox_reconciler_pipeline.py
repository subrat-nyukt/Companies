"""
Production-Grade Reliability Pipeline for Dual-Database Consistency
=====================================================================
Components:
1. Transactional Outbox (ACID PostgreSQL Atomic Write)
2. Asynchronous Outbox Worker (Decoupled Background Sync)
3. Deterministic Vector IDs (Idempotent Vector Upserts)
4. Self-Healing Reconciler (Periodic Audit & Repair Cron Job)
"""

import asyncio
import uuid
import time
import json
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor


class ProductionReliabilityPipeline:
    def __init__(self, db_connection_string: str):
        self.db_uri = db_connection_string

    def get_db_connection(self):
        """Returns a PostgreSQL connection."""
        return psycopg2.connect(self.db_uri, cursor_factory=RealDictCursor)

    # =========================================================================
    # LAYER 1: ATOMIC WRITE (Transactional Outbox Pattern)
    # =========================================================================
    def save_voice_call_transactional(self, call_id: str, patient_id: str, transcript: str):
        """
        Single PostgreSQL ACID Transaction:
        Writes BOTH Call Log AND Outbox Event. Either BOTH succeed or BOTH fail.
        """
        conn = self.get_db_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    # 1. Write Call Log
                    cur.execute("""
                        INSERT INTO call_logs (call_id, patient_id, transcript, vector_sync_status, created_at)
                        VALUES (%s, %s, %s, 'PENDING', NOW())
                        ON CONFLICT (call_id) DO NOTHING;
                    """, (call_id, patient_id, transcript))

                    # 2. Write Outbox Event in SAME ACID Transaction
                    outbox_id = f"evt_{uuid.uuid4().hex[:12]}"
                    payload_json = json.dumps({"call_id": call_id, "transcript": transcript})
                    
                    cur.execute("""
                        INSERT INTO outbox_events (outbox_id, call_id, event_type, payload, status, retry_count, created_at)
                        VALUES (%s, %s, 'UPSERT_VECTOR_MEMORY', %s, 'UNPROCESSED', 0, NOW());
                    """, (outbox_id, call_id, payload_json))

            print(f"🔒 [LAYER 1: ACID SUCCESS] Saved Call '{call_id}' & Outbox Event '{outbox_id}'")
        except Exception as e:
            conn.rollback()
            print(f"❌ [LAYER 1: TX ROLLBACK] Failed to save call record: {e}")
            raise e
        finally:
            conn.close()

    # =========================================================================
    # LAYER 2: ASYNC EXECUTION (Background Worker + Deterministic Vector IDs)
    # =========================================================================
    async def run_outbox_worker(self, vector_db_client, embedding_service):
        """
        Background Worker: Fetches UNPROCESSED events, embeds text,
        and performs IDEMPOTENT upserts using deterministic Vector IDs.
        """
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                # Fetch pending outbox events
                cur.execute("""
                    SELECT outbox_id, call_id, payload 
                    FROM outbox_events 
                    WHERE status = 'UNPROCESSED' AND retry_count < 3 
                    ORDER BY created_at ASC LIMIT 20;
                """)
                unprocessed_events = cur.fetchall()

            for event in unprocessed_events:
                outbox_id = event["outbox_id"]
                call_id = event["call_id"]
                payload = json.loads(event["payload"])
                transcript = payload["transcript"]

                try:
                    # A. Generate Vector Embedding
                    vector = await embedding_service.get_embedding(transcript)

                    # B. Idempotent Upsert using call_id as Vector ID (vector_id = call_id)
                    vector_db_client.upsert(
                        id=call_id,  # Deterministic Vector ID!
                        vector=vector,
                        payload={"call_id": call_id, "transcript": transcript}
                    )

                    # C. Update PostgreSQL status to SYNCED & PROCESSED
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                UPDATE outbox_events SET status = 'PROCESSED', updated_at = NOW() WHERE outbox_id = %s;
                            """, (outbox_id,))
                            cur.execute("""
                                UPDATE call_logs SET vector_sync_status = 'SYNCED', updated_at = NOW() WHERE call_id = %s;
                            """, (call_id,))
                    print(f"✅ [LAYER 2: ASYNC WORKER] Synced call '{call_id}' to Vector DB.")

                except Exception as err:
                    print(f"⚠️ [LAYER 2: WORKER ERROR] Event '{outbox_id}' failed: {err}")
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                UPDATE outbox_events SET retry_count = retry_count + 1 WHERE outbox_id = %s;
                            """, (outbox_id,))
        finally:
            conn.close()

    # =========================================================================
    # LAYER 3: AUTOMATED REPAIR (Self-Healing Reconciler Cron Job)
    # =========================================================================
    async def run_reconciler_cron_job(self, vector_db_client, embedding_service):
        """
        Periodic Cron Job (Runs Nightly at 2:00 AM):
        Finds any records stuck in 'PENDING' for > 30 mins and repairs state drift.
        """
        print("\n🔍 [LAYER 3: RECONCILER] Starting State Drift Audit...")
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                # Find call records stuck in PENDING status
                cur.execute("""
                    SELECT call_id, transcript 
                    FROM call_logs 
                    WHERE vector_sync_status = 'PENDING' 
                    AND created_at < NOW() - INTERVAL '30 minutes';
                """)
                drifted_records = cur.fetchall()

            print(f"📊 [LAYER 3: RECONCILER] Found {len(drifted_records)} drifted records to repair.")

            for record in drifted_records:
                call_id = record["call_id"]
                transcript = record["transcript"]

                # Force Re-embed and Repair Vector DB
                vector = await embedding_service.get_embedding(transcript)
                vector_db_client.upsert(
                    id=call_id,
                    vector=vector,
                    payload={"call_id": call_id, "transcript": transcript}
                )

                # Mark SYNCED in PostgreSQL
                with conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE call_logs SET vector_sync_status = 'SYNCED', updated_at = NOW() WHERE call_id = %s;
                        """, (call_id,))
                print(f"🎉 [LAYER 3: RECONCILER REPAIRED] Fixed state drift for call '{call_id}'")

        finally:
            conn.close()
