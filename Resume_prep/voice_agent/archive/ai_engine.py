import json
import logging
import asyncio
import websockets

logger = logging.getLogger(__name__)

class SarvamSTTClient:
    """
    [AI ENGINEER TASK]
    Your job is to complete this class to connect to Sarvam's Real-time STT API.
    
    Model to use: saaras:v3
    Language: Odia (or "or")
    Audio Format: 8000Hz, mu-law (from Plivo)
    """

    def __init__(self):
        self.sarvam_ws_url = "wss://api.sarvam.ai/speech-to-text/streaming" # Verify with Sarvam docs
        self.api_key = "YOUR_SARVAM_API_KEY" # Add your Sarvam API Key here
        self.ws = None

    async def connect(self):
        """
        [TODO for AI Engineer]: 
        1. Open a WebSocket connection to self.sarvam_ws_url.
        2. Pass any required headers (like API Key).
        3. Send any initial connection payload Sarvam requires (e.g. setting the model, language, sample rate).
        """
        logger.info("Connecting to Sarvam STT... (TO BE IMPLEMENTED by AI Engineer)")
        # self.ws = await websockets.connect(self.sarvam_ws_url, extra_headers={"Authorization": f"Bearer {self.api_key}"})
        # pass initial config to self.ws
        pass

    async def send_audio(self, base64_payload: str):
        """
        [TODO for AI Engineer]:
        1. When Plivo sends audio payload, this function is called.
        2. Format the base64_payload as required by Sarvam's WebSocket schema and send it using self.ws.send()
        """
        if not self.ws:
            return
        
        # message = {"audio": base64_payload, "is_final": False}
        # await self.ws.send(json.dumps(message))
        pass
    
    async def listen_for_transcripts(self):
        """
        [TODO for AI Engineer]:
        1. Run an async loop listening to self.ws.receive().
        2. Parse the JSON response from Sarvam.
        3. Print the transcribed Odia text to the console!
        """
        if not self.ws:
            return
        
        # while True:
        #     response = await self.ws.recv()
        #     data = json.loads(response)
        #     if "transcript" in data:
        #          print(f"USER SAID: {data['transcript']}")
        pass
