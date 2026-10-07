from __future__ import annotations
"""
LLM Engine — OpenAI GPT-4o with tool calling
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Manages per-call conversation history.
Executes Sarvam-returned language-aware tool calls.
"""

import json
import logging
import os
from typing import Callable, Awaitable

from openai import AsyncOpenAI

from agent_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o")

# ══════════════════════════════════════════════════════════════════════
# TOOL SCHEMAS  (OpenAI function-calling format)
# ══════════════════════════════════════════════════════════════════════

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_specialty_availability",
            "description": (
                "Use when the caller asks which doctors are available in a specialty "
                "such as Cardiology, Orthopedics, Neurology, Pediatrics, Gynecology, "
                "General Medicine, Dermatology, or ENT."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "specialty": {
                        "type": "string",
                        "description": "Medical specialty in English, e.g. Cardiology",
                    }
                },
                "required": ["specialty"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_doctor_availability",
            "description": "Use when the caller asks for a specific doctor's free slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {
                        "type": "string",
                        "enum": [
                            "ANUPAM JENA", "SUBASIS MISHRA", "SANTOSH RATH",
                            "DEBASHIS MISHRA", "OM MISHRA", "PRERANA DASH",
                        ],
                        "description": "Doctor's full name in English only.",
                    }
                },
                "required": ["doctor_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "Book a new appointment. Call ONLY after the caller has confirmed "
                "doctor, day, time, phone, and name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name":  {"type": "string"},
                    "patient_phone": {
                        "type": "string",
                        "description": "E.164 format: +91XXXXXXXXXX",
                    },
                    "doctor_id": {
                        "type": "string",
                        "description": "DR001–DR006 from the doctor reference table.",
                    },
                    "doctor_name": {"type": "string"},
                    "day":  {
                        "type": "string",
                        "description": "Day in English, e.g. Monday",
                    },
                    "time": {
                        "type": "string",
                        "description": "Time in English, e.g. 10:00 AM",
                    },
                },
                "required": ["patient_name", "patient_phone", "doctor_id", "day", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_appointments",
            "description": "Retrieve all confirmed appointments for a patient phone number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_phone": {
                        "type": "string",
                        "description": "Phone in E.164 format.",
                    }
                },
                "required": ["patient_phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modify_appointment",
            "description": "Reschedule an existing appointment to a new day and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"},
                    "new_day":  {
                        "type": "string",
                        "description": "New day in English, e.g. Thursday",
                    },
                    "new_time": {
                        "type": "string",
                        "description": "New time in English, e.g. 2:00 PM",
                    },
                },
                "required": ["appointment_id", "new_day", "new_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"}
                },
                "required": ["appointment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "register_new_patient",
            "description": (
                "Register a brand-new patient. Call only AFTER collecting both "
                "their name and phone number."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name":  {"type": "string"},
                    "phone": {
                        "type": "string",
                        "description": "E.164 format: +91XXXXXXXXXX",
                    },
                },
                "required": ["name", "phone"],
            },
        },
    },
]

# Opening greeting (spoken via TTS on call connect)
OPENING_GREETING = (
    "नमस्ते, कीम्स मेडिकल  में आपका स्वागत है। "
    "मैं आपकी अपॉइंटमेंट बुक करने में सहायता कर सकती हूँ। "
    "आप ओड़िया, हिंदी या English में बात कर सकते हैं।"
)
OPENING_LANG = "hi"   # Hindi greeting — Sarvam TTS: hi-IN / meera


# ══════════════════════════════════════════════════════════════════════
# CONVERSATION MANAGER  (one instance per call)
# ══════════════════════════════════════════════════════════════════════

class ConversationManager:
    """
    Keeps conversation history for one call.
    `tool_executor` is an async callable:
        async def tool_executor(tool_name: str, args: dict, call_sid: str) -> str
    """

    def __init__(
        self,
        call_sid:      str,
        from_number:   str,
        tool_executor: Callable[[str, dict, str], Awaitable[str]],
        on_thinking:   Callable[[str], Awaitable[None]] | None = None,
    ):
        self.call_sid      = call_sid
        self.from_number   = from_number
        self.tool_executor = tool_executor
        self.on_thinking   = on_thinking

        # Auto-detect OpenRouter vs OpenAI keys
        if OPENAI_API_KEY.startswith("sk-or-v1"):
            self.client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENAI_API_KEY,
            )
            # Default to a good OpenRouter model if not overridden
            global OPENAI_MODEL
            if OPENAI_MODEL == "gpt-4o":
                OPENAI_MODEL = "openai/gpt-4o"
        else:
            self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        # Inject caller's number into the system prompt
        prompt = SYSTEM_PROMPT.replace("{{from_number}}", from_number)
        self.messages: list = [{"role": "system", "content": prompt}]

        # Record the opening greeting as first assistant turn so the
        # LLM knows what was already said
        self.messages.append({
            "role":    "assistant",
            "content": OPENING_GREETING,
        })

    # ──────────────────────────────────────────────────────────────────
    # Main entry point
    # ──────────────────────────────────────────────────────────────────

    async def get_response(self, user_text: str, lang: str = "en") -> str:
        """
        Prepend [LANGUAGE: xx] to every user turn so the LLM knows which
        language mode to activate (or=Odia, hi=Hindi, en=English).
        Then send to GPT-4o with tool loop and return the text reply.
        """
        # Inject detected language tag
        tagged = f"[LANGUAGE: {lang}] {user_text}"
        self.messages.append({"role": "user", "content": tagged})

        # CRITICAL: Trigger 'wait' message instantly while LLM processes
        if self.on_thinking:
            await self.on_thinking(lang)

        # Tool-call loop — GPT-4o may call tools several times before
        # producing a plain-text reply.
        while True:
            response = await self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=self.messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.05,   # Very low → consistent language adherence
                max_tokens=450,
            )

            msg = response.choices[0].message

            # ── Plain text reply ──────────────────────────────────────
            if not msg.tool_calls:
                text = msg.content or ""
                self.messages.append({"role": "assistant", "content": text})
                logger.info(f"LLM: {text[:120]}")
                return text

            # ── Tool call(s) ──────────────────────────────────────────
            self.messages.append(msg)          # add assistant tool-call msg

            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                logger.info(f"Tool ▶ {name}({args})")

                result = await self.tool_executor(name, args, self.call_sid)
                logger.info(f"Tool ◀ {result[:120]}")

                self.messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      result,
                })
            # Loop back — LLM will now produce a text reply
