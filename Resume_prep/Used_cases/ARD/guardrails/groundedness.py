"""
ARD — guardrails/groundedness.py
==================================
Synchronous, blocking Groundedness Guardrail.

Implements the RAG Triad Metric 2: Groundedness / Faithfulness.

Algorithm:
1. Split the synthesis draft into discrete sentences.
2. For each sentence, call the LLM-as-a-Judge to classify it as:
   - SUPPORTED   → sentence is directly traceable to the retrieved context
   - CONTRADICTED → sentence directly contradicts context (immediate fail)
   - NEUTRAL     → sentence makes an assertion not found in context (non-grounded)
3. Compute score = supported_count / total_sentences
4. If any CONTRADICTED verdict → score = 0.0 immediately
5. Return score; the graph node decides pass/fail against the threshold.

This runs SYNCHRONOUSLY before any report is published — it is a compliance gate.
"""

import json
import re
import logging

from openai import OpenAI

from core.config import settings
from prompts.agent_prompts import GROUNDEDNESS_SYSTEM, GROUNDEDNESS_USER_TEMPLATE

logger = logging.getLogger(__name__)


def _split_sentences(text: str) -> list[str]:
    """
    Simple sentence splitter that handles abbreviations poorly (acceptable for production
    augmentation but appropriate for this use case).
    Filters out sentences shorter than 20 characters (typically not factual claims).
    """
    raw = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in raw if len(s.strip()) > 20]


def evaluate_groundedness(
    synthesis_text: str,
    context_chunks: list[dict],
    openai_client: OpenAI = None,
) -> tuple[float, list[dict]]:
    """
    Evaluate groundedness of every sentence in the synthesis against retrieved context.

    Args:
        synthesis_text: The full text of the synthesis draft to evaluate.
        context_chunks: Retrieved chunks (list of dicts with 'text' key).
        openai_client: Optional pre-initialized OpenAI client.

    Returns:
        (score: float 0.0-1.0, verdicts: list of per-sentence verdict dicts)
    
    Score interpretation:
        1.0 → Fully grounded — all sentences supported by retrieved context
        <1.0 → One or more sentences not grounded → blocked for analyst review
        0.0 → Direct contradiction detected → immediate hard block
    """
    if openai_client is None:
        openai_client = OpenAI(api_key=settings.openai_api_key)

    # Build context string from all retrieved chunks
    context_str = "\n\n---\n\n".join(
        f"[Source: {c.get('source', 'unknown')}]\n{c['text']}"
        for c in context_chunks
    )

    # Concatenate all text fields from the synthesis for evaluation
    sentences = _split_sentences(synthesis_text)
    if not sentences:
        logger.warning("[Groundedness] No evaluable sentences found in synthesis.")
        return 1.0, []

    verdicts = []
    supported_count = 0

    for sentence in sentences:
        prompt = GROUNDEDNESS_USER_TEMPLATE.format(
            context=context_str,
            sentence=sentence,
        )
        try:
            response = openai_client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": GROUNDEDNESS_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,   # Deterministic evaluation
                max_tokens=150,
            )
            result = json.loads(response.choices[0].message.content)
            verdict = result.get("verdict", "NEUTRAL").upper()
            reason = result.get("reason", "")

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"[Groundedness] LLM call failed for sentence: {e}")
            verdict = "NEUTRAL"
            reason = f"Evaluation failed: {str(e)}"

        verdicts.append({
            "sentence": sentence,
            "verdict": verdict,
            "reason": reason,
        })

        if verdict == "CONTRADICTED":
            # Hard fail — any contradiction is an immediate block
            logger.warning(f"[Groundedness] CONTRADICTION DETECTED: '{sentence}'")
            return 0.0, verdicts

        if verdict == "SUPPORTED":
            supported_count += 1

    score = supported_count / len(sentences) if sentences else 1.0
    logger.info(
        f"[Groundedness] Score: {score:.2f} "
        f"({supported_count}/{len(sentences)} sentences supported)"
    )
    return score, verdicts


def extract_synthesis_text(synthesis_draft: dict) -> str:
    """
    Concatenate all text fields from the SynthesisOutput dict into one evaluable string.
    Only evaluates the key factual commentary fields, not headlines or trade ideas.
    """
    fields_to_check = ["executive_summary", "macro_commentary", "event_driven_commentary"]
    parts = []
    for field in fields_to_check:
        val = synthesis_draft.get(field, "")
        if isinstance(val, str) and val:
            parts.append(val)
    return " ".join(parts)
