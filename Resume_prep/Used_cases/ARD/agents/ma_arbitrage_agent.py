"""
ARD — agents/ma_arbitrage_agent.py
=====================================
Agent 2: M&A Anti-Trust Arbitrage Agent

Trigger: SEC EDGAR filings, European Commission competition notices,
         China SAMR announcements, CFIUS review updates, deal break/close news.

Output: A structured AgentOutput containing deal risk/opportunity signal,
        with confidence scoring and direct evidence (break-up fees, timelines).

Production features:
- asyncio.wait_for() circuit breaker (agent_timeout_seconds)
- Pydantic schema validation of LLM output
- Self-correction retry loop (max_retries)
- A2A envelope tracing
"""

import asyncio
import json
import logging

from openai import OpenAI
from pydantic import ValidationError

from core.config import settings
from prompts.agent_prompts import MA_ARBITRAGE_SYSTEM, MA_ARBITRAGE_USER_TEMPLATE
from schemas.contracts import AgentOutput, ARDState, build_envelope

logger = logging.getLogger(__name__)
AGENT_NAME = "ma_arbitrage_agent"


async def _call_llm_with_retry(
    openai_client: OpenAI,
    query: str,
    context: str,
) -> AgentOutput:
    """LLM call with Pydantic schema validation and self-correction retry."""
    messages = [
        {"role": "system", "content": MA_ARBITRAGE_SYSTEM},
        {
            "role": "user",
            "content": MA_ARBITRAGE_USER_TEMPLATE.format(query=query, context=context),
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


async def run_ma_arbitrage_agent(
    state: ARDState,
    openai_client: OpenAI,
) -> tuple[AgentOutput | None, dict]:
    """
    Main entry point called by the LangGraph orchestrator node.
    Returns (agent_output | None, a2a_envelope_dict).
    Circuit breaker wraps all exceptions into a failure envelope.
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
