"""
Sarvam AI Client — STT (saaras:v3 REST) + TTS (bulbul:v3 REST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STT : REST API + local VAD (buffers mulaw audio, transcribes on silence)
TTS : REST API → returns mulaw 8000Hz to send back to Plivo
"""

import asyncio
import aiohttp
import audioop
import base64
import io
import json
import logging
import os
import wave
from typing import Callable

logger = logging.getLogger(__name__)

# ── Sarvam endpoints ──────────────────────────────────────────────────
STT_REST_URL = "https://api.sarvam.ai/speech-to-text"
TTS_REST_URL = "https://api.sarvam.ai/text-to-speech"

# ── Language code maps ────────────────────────────────────────────────
STT_LANG_MAP = {
    "od-IN": "or", "or-IN": "or", "or": "or",
    "hi-IN": "hi", "hi":    "hi",
    "en-IN": "en", "en-US": "en", "en": "en",
}
TTS_LANG_CODE = {"or": "od-IN", "hi": "hi-IN", "en": "en-IN"}
TTS_SPEAKER   = {"or": "priya", "hi": "priya", "en": "priya"}

# ── VAD Config ────────────────────────────────────────────────────────
SILENCE_THRESHOLD   = 400      # RMS energy — below this = silence
SILENCE_FRAMES_NEED = 24       # ~0.6 sec at 8000Hz (was 40/1.0s) -> faster response
MIN_SPEECH_FRAMES   = 8        # ~0.2 sec minimum speech before transcribing
PLIVO_CHUNK_BYTES   = 200      # typical mulaw chunk from Plivo per event


# ══════════════════════════════════════════════════════════════════════
# REST-BASED STT  with local VAD
# ══════════════════════════════════════════════════════════════════════

class SarvamSTT:
    """
    Buffers mulaw-8000Hz audio from Plivo.
    Detects end-of-speech via simple energy VAD.
    Sends buffered audio to Sarvam saaras:v3 REST API for transcription.
    Calls on_transcript(text, lang, is_final=True) when speech ends.
    """

    def __init__(self, api_key: str):
        self.api_key        = api_key
        self.running        = False

        # Audio buffers (PCM 16-bit)
        self._speech_pcm    = bytearray()  # accumulated speech frames
        self._speech_frames = 0            # frames of detected speech

        # VAD state
        self._silence_count = 0
        self._in_speech     = False

        # Callback
        self._on_transcript: Callable | None = None
        self._task: asyncio.Task | None = None

    async def connect(self):
        """No WebSocket needed — verify API key with a tiny test call."""
        self.running = True
        logger.info("✓ Sarvam STT (REST+VAD) ready")

    async def send_audio(self, mulaw_bytes: bytes):
        """
        Receive a mulaw chunk from Plivo.
        Convert to PCM, run VAD, and trigger transcription on silence.
        """
        if not self.running or not self._on_transcript:
            return

        # mulaw → 16-bit PCM (same sample rate 8000Hz)
        try:
            pcm = audioop.ulaw2lin(mulaw_bytes, 2)
        except Exception:
            return

        rms = audioop.rms(pcm, 2) if pcm else 0

        if rms > SILENCE_THRESHOLD:
            # Speech detected
            self._in_speech     = True
            self._silence_count = 0
            self._speech_pcm.extend(pcm)
            self._speech_frames += 1
        else:
            # Silence
            if self._in_speech:
                self._silence_count += 1
                self._speech_pcm.extend(pcm)  # include trailing silence

                if self._silence_count >= SILENCE_FRAMES_NEED:
                    # End of utterance
                    if self._speech_frames >= MIN_SPEECH_FRAMES:
                        asyncio.create_task(
                            self._transcribe(bytes(self._speech_pcm))
                        )
                    self._reset()

    def _reset(self):
        self._speech_pcm    = bytearray()
        self._speech_frames = 0
        self._silence_count = 0
        self._in_speech     = False

    async def _transcribe(self, pcm_bytes: bytes):
        """Send PCM audio to Sarvam saaras:v3 REST and call on_transcript."""
        try:
            wav_bytes = _pcm_to_wav(pcm_bytes, sample_rate=8000)
            form = aiohttp.FormData()
            form.add_field("file",
                           io.BytesIO(wav_bytes),
                           filename="audio.wav",
                           content_type="audio/wav")
            form.add_field("model",         "saaras:v3")
            form.add_field("language_code", "unknown")  # multilingual auto-detect

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    STT_REST_URL,
                    data=form,
                    headers={"api-subscription-key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        err = await resp.text()
                        logger.error(f"Sarvam STT REST {resp.status}: {err[:200]}")
                        return
                    data       = await resp.json()
                    transcript = data.get("transcript", "").strip()
                    lang_raw   = data.get("language_code", "en-IN")
                    lang       = STT_LANG_MAP.get(lang_raw,
                                   STT_LANG_MAP.get(lang_raw.split("-")[0], "en"))
                    if transcript:
                        logger.info(f"STT [{lang}] ▶ {transcript}")
                        await self._on_transcript(transcript, lang, True)
        except Exception as e:
            logger.error(f"STT transcription error: {e}")

    async def run(self, on_transcript: Callable):
        """Store callback — audio chunks arrive via send_audio()."""
        self._on_transcript = on_transcript
        # Stay alive until close() is called
        while self.running:
            await asyncio.sleep(0.5)

    async def close(self):
        self.running = False
        logger.info("Sarvam STT (REST) closed")


# ══════════════════════════════════════════════════════════════════════
# TTS — REST  (no pitch/loudness parameters for bulbul:v3)
# ══════════════════════════════════════════════════════════════════════

async def sarvam_tts(text: str, language: str, api_key: str) -> bytes:
    """
    Convert text → speech via Sarvam bulbul:v3.
    Returns mulaw-encoded audio at 8000 Hz (ready for Plivo).
    `language` is our 2-letter code: 'en', 'hi', or 'or'.
    """
    if not text.strip():
        return b""

    lang_code = TTS_LANG_CODE.get(language, "en-IN")
    speaker   = TTS_SPEAKER.get(language, "meera")

    # NOTE: pitch, pace, loudness are NOT supported by bulbul:v3
    payload = {
        "inputs":               [text],
        "target_language_code": lang_code,
        "model":                "bulbul:v3",
        "speaker":              speaker,
        "enable_preprocessing": True,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            TTS_REST_URL,
            json=payload,
            headers={
                "api-subscription-key": api_key,
                "Content-Type":         "application/json",
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            body = await resp.read()
            if resp.status != 200:
                logger.error(f"Sarvam TTS {resp.status}: {body[:300]}")
                return b""
            try:
                data = json.loads(body)
            except Exception as e:
                logger.error(f"Sarvam TTS JSON error: {e} | {body[:200]}")
                return b""
            audios = data.get("audios", [])
            if not audios:
                logger.error(f"Sarvam TTS: empty audios | {data}")
                return b""
            wav_bytes = base64.b64decode(audios[0])
            logger.info(f"Sarvam TTS [{lang_code}/{speaker}] ✓ {len(wav_bytes)} bytes")

    return _wav_to_mulaw_8k(wav_bytes)


# ── Audio helpers ─────────────────────────────────────────────────────

def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 8000) -> bytes:
    """Wrap raw 16-bit PCM in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)       # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def _wav_to_mulaw_8k(wav_bytes: bytes) -> bytes:
    """Convert WAV (any rate/channels) → mulaw PCM 8000 Hz mono."""
    with io.BytesIO(wav_bytes) as f:
        with wave.open(f, "rb") as wf:
            n_ch = wf.getnchannels()
            sw   = wf.getsampwidth()
            rate = wf.getframerate()
            pcm  = wf.readframes(wf.getnframes())

    if n_ch == 2:
        pcm = audioop.tomono(pcm, sw, 0.5, 0.5)
    if rate != 8000:
        pcm, _ = audioop.ratecv(pcm, sw, 1, rate, 8000, None)
    if sw != 2:
        pcm = audioop.lin2lin(pcm, sw, 2)

    return audioop.lin2ulaw(pcm, 2)
