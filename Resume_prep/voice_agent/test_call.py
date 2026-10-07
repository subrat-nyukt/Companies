import httpx
import asyncio

URL = "http://localhost:8000/trigger-call"
YOUR_NUMBER = "+918510840607"

async def call_me():
    print(f"Triggering call to {YOUR_NUMBER}...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            URL,
            json={"to": YOUR_NUMBER},
            timeout=10.0
        )
    print(f"Status: {resp.status_code}")
    try:
        print(resp.json())
    except:
        print(resp.text)

if __name__ == "__main__":
    asyncio.run(call_me())
