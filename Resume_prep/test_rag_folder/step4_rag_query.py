"""
STEP 4 — Full RAG: Query → Retrieve → Augment → Generate

This is the complete Retrieval-Augmented Generation loop:
  1. User asks a KYC question
  2. Embed the question (OpenAI)
  3. Retrieve top-k relevant chunks from Pinecone
  4. Build a prompt: [System] + [Retrieved Context] + [User Question]
  5. Send to GPT-4o → get a grounded, cited answer

Run:
    python step4_rag_query.py

Key concepts practised:
  - Prompt construction (system + context + question)
  - Why RAG beats fine-tuning for document-specific Q&A
  - Hallucination reduction through grounded context
  - Source citation from metadata
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL  = "gpt-4o"
TOP_K       = 5      # chunks fed to LLM as context

console = Console()

# ── System Prompt ───────────────────────────────────────────────────────────
# This defines the LLM's persona and grounding rules.
# CRITICAL: "only use the provided context" prevents hallucination.

SYSTEM_PROMPT = """You are a KYC (Know Your Customer) compliance expert assistant
working for a FinTech company. Your job is to answer questions about KYC policies,
AML regulations, due diligence processes, and compliance requirements.

RULES:
1. Answer ONLY based on the provided context excerpts from the KYC Policy Manual.
2. If the context does not contain enough information, say: "The provided documents
   do not contain enough information to answer this question."
3. Always cite which section or page your answer comes from.
4. Be precise and use correct regulatory terminology.
5. Structure your answer clearly with bullet points where appropriate.
"""


# ───────────────────────────────────────────────────────────────────────────
# RETRIEVAL
# ───────────────────────────────────────────────────────────────────────────

def embed_query(query: str, client: OpenAI) -> list[float]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=[query])
    return resp.data[0].embedding


def retrieve_chunks(query_vec: list[float], index, top_k: int) -> list[dict]:
    matches = index.query(
        vector=query_vec,
        top_k=top_k,
        include_metadata=True,
    ).matches
    return matches


# ───────────────────────────────────────────────────────────────────────────
# PROMPT CONSTRUCTION
# ───────────────────────────────────────────────────────────────────────────

def build_context_block(matches: list) -> tuple[str, list[str]]:
    """
    Assembles the retrieved chunks into a formatted context string
    that gets injected into the LLM prompt.

    Returns:
        context_text : formatted string of all chunks
        sources      : list of "Page X (score: Y)" citations
    """
    context_parts = []
    sources = []

    for i, match in enumerate(matches, 1):
        text  = match.metadata.get("text", "")
        page  = match.metadata.get("page_num", "?")
        score = match.score

        context_parts.append(
            f"[Excerpt {i} | Page {page} | Relevance: {score:.3f}]\n{text}"
        )
        sources.append(f"Page {page} (score: {score:.3f})")

    context_text = "\n\n---\n\n".join(context_parts)
    return context_text, sources


def build_prompt_messages(question: str, context: str) -> list[dict]:
    """
    Constructs the OpenAI chat messages list.

    Structure:
      [0] system  → role + grounding rules
      [1] user    → context + question

    WHY put context in the user message (not system)?
    → The system message is for fixed instructions. Context changes per query.
      Some models also pay more attention to user-turn content.
    """
    user_content = (
        f"CONTEXT FROM KYC POLICY MANUAL:\n"
        f"{'='*60}\n"
        f"{context}\n"
        f"{'='*60}\n\n"
        f"QUESTION: {question}"
    )
    return [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": user_content},
    ]


# ───────────────────────────────────────────────────────────────────────────
# GENERATION
# ───────────────────────────────────────────────────────────────────────────

def generate_answer(messages: list[dict], client: OpenAI) -> str:
    """
    Calls GPT-4o with the augmented prompt.

    temperature=0.2 → low randomness for factual compliance answers.
    max_tokens=800  → enough for a detailed answer without waste.
    """
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=800,
    )
    return response.choices[0].message.content


# ───────────────────────────────────────────────────────────────────────────
# FULL RAG PIPELINE
# ───────────────────────────────────────────────────────────────────────────

def rag_query(question: str, oai_client: OpenAI, index) -> None:
    """
    End-to-end RAG pipeline for one question.
    Prints retrieved chunks + LLM answer with citations.
    """
    console.rule(f"[bold cyan]RAG Query[/bold cyan]")
    console.print(f"[bold yellow]Q:[/bold yellow] {question}\n")

    # Step A — Embed the question
    console.print("[dim]→ Embedding query...[/dim]")
    query_vec = embed_query(question, oai_client)

    # Step B — Retrieve from Pinecone
    console.print(f"[dim]→ Retrieving top-{TOP_K} chunks from Pinecone...[/dim]")
    matches = retrieve_chunks(query_vec, index, TOP_K)

    if not matches:
        console.print("[red]No relevant chunks found in Pinecone.[/red]")
        return

    # Step C — Build context + prompt
    context, sources = build_context_block(matches)
    messages = build_prompt_messages(question, context)

    # Step D — Generate answer
    console.print(f"[dim]→ Generating answer with {CHAT_MODEL}...[/dim]\n")
    answer = generate_answer(messages, oai_client)

    # Step E — Display
    console.print(Panel(
        Markdown(answer),
        title="[bold green]Answer[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))

    console.print(f"[dim]Sources: {' | '.join(sources)}[/dim]\n")


# ───────────────────────────────────────────────────────────────────────────
# DEMO QUESTIONS + INTERACTIVE LOOP
# ───────────────────────────────────────────────────────────────────────────

DEMO_QUESTIONS = [
    "What is the difference between Standard Due Diligence and Enhanced Due Diligence?",
    "Who qualifies as a Politically Exposed Person and what extra steps are required?",
    "What are the SAR filing thresholds in the US and UK?",
    "How is the KYC risk score calculated? What factors are weighted?",
    "What are the major penalties financial institutions face for KYC failures? Give examples.",
    "What is the tipping-off prohibition and why is it important?",
    "How does eKYC handle the higher risk of non-face-to-face onboarding?",
    "What is a UBO and how do you verify one in a complex corporate structure?",
]


def main():
    console.print(Panel.fit(
        "[bold cyan]KYC RAG — Step 4: Full RAG Pipeline[/bold cyan]\n"
        f"Query → Pinecone Retrieval → GPT-4o Generation",
        border_style="cyan",
    ))

    openai_key   = os.getenv("OPENAI_API_KEY")
    pinecone_key = os.getenv("PINECONE_API_KEY")
    index_name   = os.getenv("PINECONE_INDEX_NAME", "kyc-rag-index")

    if not openai_key or not pinecone_key:
        console.print("[red]ERROR: Missing API keys in .env[/red]")
        return

    oai_client = OpenAI(api_key=openai_key)
    pc         = Pinecone(api_key=pinecone_key)
    index      = pc.Index(index_name)

    stats = index.describe_index_stats()
    console.print(f"[green]✓ Pinecone:[/green] '{index_name}' | {stats.total_vector_count} vectors indexed\n")

    console.print("[bold]Choose mode:[/bold]")
    console.print("  [1] Run demo questions (recommended first run)")
    console.print("  [2] Ask your own question")
    console.print("  [3] Interactive loop (keep asking)")

    choice = console.input("\n> ").strip()

    if choice == "1":
        for q in DEMO_QUESTIONS:
            rag_query(q, oai_client, index)
            console.input("[dim]Press Enter for next question...[/dim]")

    elif choice == "2":
        q = console.input("\n[bold]Your question:[/bold] ").strip()
        if q:
            rag_query(q, oai_client, index)

    elif choice == "3":
        console.print("[dim]Type 'quit' to exit[/dim]")
        while True:
            q = console.input("\n[bold]> Question:[/bold] ").strip()
            if q.lower() in ("quit", "exit", "q"):
                break
            if q:
                rag_query(q, oai_client, index)
    else:
        # Default to first demo question
        rag_query(DEMO_QUESTIONS[0], oai_client, index)

    console.print("\n[bold green]✅ RAG session complete![/bold green]")


if __name__ == "__main__":
    main()
