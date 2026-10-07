"""
ARD — agents/central_bank_agent.py
=====================================
Agent 1: Central Bank Sentiment Agent

Trigger: Fed, ECB, PBOC, BoE speeches, economic data releases,
         monetary policy minutes, inflation prints.

Output: A structured AgentOutput containing the primary hawkish/dovish
        signal, with confidence scoring and direct evidence quotes.

Production features:
- asyncio.wait_for() circuit breaker (agent_timeout_seconds)
- Pydantic schema validation of LLM output
- Self-correction retry loop (max_retries)
- A2A envelope tracing
"""

import asyncio
import json
import logging
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from core.config import settings
from prompts.agent_prompts import CENTRAL_BANK_SYSTEM, CENTRAL_BANK_USER_TEMPLATE
from schemas.contracts import AgentOutput, ARDState, build_envelope

logger = logging.getLogger(__name__)
AGENT_NAME = "central_bank_sentiment_agent"


async def _call_llm_with_retry(
    openai_client: OpenAI,
    query: str,
    context: str,
) -> AgentOutput:
    """
    Call the LLM and validate output against AgentOutput schema.
    Implements self-correction loop: if the LLM output fails Pydantic
    validation, it sends the error back to the LLM for correction.
    """
    messages = [
        {"role": "system", "content": CENTRAL_BANK_SYSTEM},
        {
            "role": "user",
            "content": CENTRAL_BANK_USER_TEMPLATE.format(query=query, context=context),
        },
    ]

    for attempt in range(settings.max_retries + 1):
        logger.info(f"[{AGENT_NAME}] LLM call attempt {attempt + 1}/{settings.max_retries + 1}")

        response = openai_client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = response.choices[0].message.content

        try:
            data = json.loads(raw)
            return AgentOutput(**data)

        except (json.JSONDecodeError, ValidationError) as e:
            if attempt < settings.max_retries:
                logger.warning(f"[{AGENT_NAME}] Schema validation failed (attempt {attempt + 1}): {e}")
                # Self-correction: feed the error back so the LLM can fix its output
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Your output failed validation with error: {e}. "
                        "Please re-generate the JSON strictly matching the required schema "
                        "(agent_name, signal, confidence, evidence, source_url, asset_class)."
                    ),
                })
            else:
                raise ValueError(
                    f"[{AGENT_NAME}] Self-correction exhausted after {settings.max_retries} retries. "
                    f"Last error: {e}"
                )

    raise RuntimeError(f"[{AGENT_NAME}] Unexpected exit from retry loop.")


async def run_central_bank_agent(
    state: ARDState,
    openai_client: OpenAI,
) -> tuple[AgentOutput | None, dict]:
    """
    Main entry point called by the LangGraph orchestrator node.

    Returns:
        (agent_output | None, a2a_envelope_dict)

    Circuit breaker: any exception inside asyncio.wait_for wraps into a
    HITL-escalation envelope. The orchestrator node handles the failure path.
    """
    query = state["trigger_query"]
    context_chunks = state.get("retrieved_chunks", [])
    context_str = "\n\n---\n\n".join(
        f"[Source: {c.get('source', 'unknown')}]\n{c['text']}"
        for c in context_chunks
    ) or "No context retrieved."

    try:
        output = await asyncio.wait_for(
            _call_llm_with_retry(openai_client, query, context_str),
            timeout=settings.agent_timeout_seconds,
        )
        logger.info(
            f"[{AGENT_NAME}] Signal: '{output.signal}' | Confidence: {output.confidence:.2f}"
        )
        envelope = build_envelope(
            state, sender=AGENT_NAME, target="synthesis_agent",
            payload=output.model_dump(), status="success",
        )
        return output, envelope

    except asyncio.TimeoutError:
        error_msg = f"{AGENT_NAME} timed out after {settings.agent_timeout_seconds}s"
        logger.error(f"[Circuit Breaker] {error_msg}")
        envelope = build_envelope(
            state, sender=AGENT_NAME, target="synthesis_agent",
            payload={}, status="circuit_breaker", error=error_msg,
        )
        return None, envelope

    except Exception as e:
        error_msg = f"{AGENT_NAME} failed: {str(e)}"
        logger.error(f"[Circuit Breaker] {error_msg}")
        envelope = build_envelope(
            state, sender=AGENT_NAME, target="synthesis_agent",
            payload={}, status="circuit_breaker", error=error_msg,
        )
        return None, envelope
