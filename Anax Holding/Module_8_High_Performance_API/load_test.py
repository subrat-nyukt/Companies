import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor

url = "http://127.0.0.1:8001/ingest/trade"
symbols = ["EURUSD", "XAUUSD", "BTCUSD", "GBPUSD", "US30"]

def send_mock_trade(thread_id):
    # Generate a random MT5 style trade
    trade = {
        "trade_id": f"TRD-{random.randint(100000, 999999)}",
        "symbol": random.choice(symbols),
        "price": round(random.uniform(1.0, 2000.0), 2),
        "volume": round(random.uniform(0.1, 5.0), 2),
        "timestamp": time.time()
    }
    
    try:
        # Measure true round-trip network time locally
        start = time.time()
        response = requests.post(url, json=trade)
        end = time.time()
        
        latency_ms = (end - start) * 1000
        server_ms = response.json().get('server_processing_time_ms')
        
        # You will see the server processes it in ~0.5 milliseconds, while the network takes longer.
        print(f"[Client {thread_id}] Trade Ingested | Server Execution: {server_ms} ms | Total Round-Trip Latency: {latency_ms:.2f} ms")
    except requests.exceptions.ConnectionError:
        print("[ERROR] Connection refused. Start the main.py FastAPI server on port 8001 first!")

print("[LOAD TEST] INITIATING HIGH-VELOCITY API STRESS TEST [LOAD TEST]")
print("Firing 100 trades to the API concurrently...")
time.sleep(2)

# Use Python Multithreading to simulate hundreds of external trading terminals hitting the API at the exact same split-second
with ThreadPoolExecutor(max_workers=50) as executor:
    for i in range(100):
        executor.submit(send_mock_trade, i)

print("\n[COMPLETE] Load test complete.")
print("If you have Docker/Redis running, see your cached data here: http://127.0.0.1:8001/market/latest/XAUUSD")
