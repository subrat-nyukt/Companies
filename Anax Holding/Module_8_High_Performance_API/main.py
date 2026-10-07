from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import redis
import json
import time
import os

app = FastAPI(title="Anax High-Throughput Trade Ingestion")

# Connect to Redis (Defaults to localhost if running directly via Python, or reads docker network environment)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
except Exception as e:
    redis_client = None

class TradeTick(BaseModel):
    trade_id: str
    symbol: str
    price: float
    volume: float
    timestamp: float

# Mock Kafka Producer
class MockKafkaProducer:
    @staticmethod
    def send(topic: str, message: dict):
        # In a real app, this uses confluent_kafka library to push to a live cluster.
        # Here we simulate a high-speed fire-and-forget push to a message queue.
        pass

def process_trade_background(trade: dict):
    """Background task to ensure the API never blocks IO, guaranteeing sub-millisecond responses."""
    try:
        # 1. Push to in-memory Redis for ultra-fast front-end Dashboard queries (e.g., the Latest Live Price)
        redis_client.set(f"latest_price:{trade['symbol']}", trade['price'])
        
        # Keep a rolling queue of the last 100 trades for charting
        redis_client.lpush(f"trade_history:{trade['symbol']}", json.dumps(trade))
        redis_client.ltrim(f"trade_history:{trade['symbol']}", 0, 99) 
    except Exception:
        pass # Ignore if Redis isn't running locally for the student

    # 2. Push to Kafka for downstream Data Lake ingestion (Into the Medallion Bronze layer safely)
    MockKafkaProducer.send(topic="raw-trades-stream", message=trade)

@app.post("/ingest/trade")
async def ingest_trade(trade: TradeTick, background_tasks: BackgroundTasks):
    # Record ingestion timestamp to measure API latency
    ingest_time = time.time()
    
    # Delegate deep IO-blocking operations (Redis + Kafka) to a background thread!
    # This guarantees the API instantly returns an HTTP 200 so the MT5 execution server never gets bottlenecked.
    background_tasks.add_task(process_trade_background, trade.dict())
    
    # The moment this code finishes, the client gets the 200 OK. 
    return {
        "status": "queued",
        "server_processing_time_ms": round((time.time() - ingest_time) * 1000, 4)
    }

@app.get("/market/latest/{symbol}")
def get_latest_price(symbol: str):
    """Retrieve the real-time price instantly from the Redis cache memory"""
    try:
        price = redis_client.get(f"latest_price:{symbol}")
        if not price:
            return {"error": "No recent trades for symbol in cache"}
        return {"symbol": symbol, "latest_price": float(price)}
    except Exception:
        return {"error": "Redis not connected"}

if __name__ == "__main__":
    import uvicorn
    # Port 8001 so it doesn't collide with Module 5 which we put on Port 8000
    print("Starting High-Velocity API Server on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
