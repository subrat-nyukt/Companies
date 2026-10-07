"""
STEP 3 — Retrieve: Query → Embed → Pinecone Search → Top-K Chunks

What happens here (the "Retrieval" half of RAG):
  1. Take a natural language question about KYC
  2. Embed it using the SAME model used during ingestion (critical!)
  3. Query Pinecone for the top-k most similar chunks
  4. Print results with similarity scores

Run:
    python step3_retrieve.py

Key concepts practised:
  - Why the SAME embedding model must be used at query time
  - Cosine similarity score interpretation
  - Metadata filtering (filter by page number, etc.)
  - top_k tuning — more chunks = more context but more noise
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

load_dotenv()

EMBED_MODEL = "text-embedding-3-small"
TOP_K       = 4     # how many chunks to retrieve

console = Console()

# ── Sample KYC questions to test retrieval ──────────────────────────────────
SAMPLE_QUESTIONS = [
    "What is Enhanced Due Diligence and when is it required?",
    "How often should high-risk customers be reviewed?",
    "What are the penalties for KYC non-compliance?",
    "What is the difference between a PEP and a regular customer?",
    "How does transaction monitoring work for suspicious activity?",
    "What documents are needed to verify a corporate customer's UBO?",
    "What is the filing threshold for a SAR in the US?",
    "What eKYC methods are used for non-face-to-face onboarding?",
]


def embed_query(query: str, client: OpenAI) -> list[float]:
    """
    Embed the user query.

    CRITICAL: Use the EXACT same model as step2_ingest.py.
    If you embed documents with model A and query with model B,
    the vector spaces are incompatible → terrible retrieval quality.
    """
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=[query],
    )
    return response.data[0].embedding


def retrieve(query_vector: list[float], index, top_k: int,
             filter_dict: dict | None = None) -> list[dict]:
    """
    Query Pinecone for the most similar chunks.

    Args:
        query_vector  : embedded query (1536 floats)
        index         : Pinecone index object
        top_k         : number of results to return
        filter_dict   : optional metadata filter, e.g. {"page_num": {"$lte": 5}}

    Returns:
        list of match dicts with keys: id, score, metadata
    """
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,   # ← must be True to get text back!
        filter=filter_dict,
    )
    return results.matches


def display_results(query: str, matches: list) -> None:
    """Pretty-print retrieval results with scores."""
    console.print(f"\n[bold yellow]Query:[/bold yellow] {query}")
    console.print(f"[dim]Retrieved {len(matches)} chunks[/dim]\n")

    for rank, match in enumerate(matches, 1):
        score   = match.score
        text    = match.metadata.get("text", "")
        page    = match.metadata.get("page_num", "?")
        tokens  = match.metadata.get("token_count", "?")

        # Colour-code by relevance score
        if score >= 0.80:
            score_str = f"[bold green]{score:.4f}[/bold green]"
        elif score >= 0.60:
            score_str = f"[bold yellow]{score:.4f}[/bold yellow]"
        else:
            score_str = f"[bold red]{score:.4f}[/bold red]"

        # Truncate text for display
        preview = text[:350].replace("\n", " ") + ("..." if len(text) > 350 else "")

        console.print(Panel(
            f"[dim]Page {page} | {tokens} tokens | Score: {score_str}[/dim]\n\n{preview}",
            title=f"[cyan]Rank #{rank}[/cyan]",
            border_style="blue",
            expand=False,
        ))


def interactive_mode(oai_client: OpenAI, index) -> None:
    """Free-form interactive retrieval loop."""
    console.print("\n[bold cyan]Interactive Retrieval Mode[/bold cyan]")
    console.print("[dim]Type your KYC question. Type 'quit' to exit.[/dim]\n")

    while True:
        query = console.input("[bold]> Question:[/bold] ").strip()
        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue

        vec     = embed_query(query, oai_client)
        matches = retrieve(vec, index, TOP_K)
        display_results(query, matches)


def run_sample_queries(oai_client: OpenAI, index) -> None:
    """Run all sample KYC questions and show a score summary table."""
    table = Table(title="Retrieval Score Summary", box=box.ROUNDED, border_style="cyan")
    table.add_column("#",       style="dim", width=3)
    table.add_column("Question",style="bold", max_width=55)
    table.add_column("Top Score", justify="right")
    table.add_column("Avg Score", justify="right")

    for i, question in enumerate(SAMPLE_QUESTIONS, 1):
        console.rule(f"[bold]Query {i}/{len(SAMPLE_QUESTIONS)}[/bold]")
        vec     = embed_query(question, oai_client)
        matches = retrieve(vec, index, TOP_K)
        display_results(question, matches)

        scores   = [m.score for m in matches]
        top_s    = f"{max(scores):.4f}" if scores else "N/A"
        avg_s    = f"{sum(scores)/len(scores):.4f}" if scores else "N/A"
        table.add_row(str(i), question[:55], top_s, avg_s)

    console.print("\n")
    console.print(table)


# ───────────────────────────────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]KYC RAG — Step 3: Retrieval[/bold cyan]\n"
        "Query → Embed → Pinecone → Top-K Chunks",
        border_style="cyan"
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

    # Show index stats
    stats = index.describe_index_stats()
    console.print(f"[green]✓ Connected to index:[/green] '{index_name}' | "
                  f"Vectors: {stats.total_vector_count}")

    # Menu
    console.print("\n[bold]Choose mode:[/bold]")
    console.print("  [1] Run all sample KYC questions")
    console.print("  [2] Interactive (type your own questions)")

    choice = console.input("\n> ").strip()

    if choice == "1":
        run_sample_queries(oai_client, index)
    elif choice == "2":
        interactive_mode(oai_client, index)
    else:
        console.print("[yellow]Running sample queries by default...[/yellow]")
        run_sample_queries(oai_client, index)


if __name__ == "__main__":
    main()
