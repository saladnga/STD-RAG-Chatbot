"""
Score document retrieval against evals/cases/rag.jsonl.

    cd backend && python -m evals.run_retrieval

Needs the real OpenAI and Supabase keys in app/.env: it searches the live document
table. Question embeddings are cached in evals/cache/, so re-runs make no OpenAI calls.

Scores are at file level for now. Chunks have no page numbers until Phase 3.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from statistics import mean

from evals.metrics import hit_at_k, recall_at_k, reciprocal_rank
from evals.schema import APP_DIR, EVALS_DIR, load_cases

sys.path.insert(0, str(APP_DIR))
from llm_clients import EMBEDDING_MODEL  # noqa: E402
from rag import retriever  # noqa: E402

K = 5
# What chat actually uses (services/chat_analysis.get_rag_context_for_chat): top 3 chunks
# with similarity >= 0.5. Measured separately so threshold changes show their real effect.
PROD_TOP_K = 3
PROD_THRESHOLD = retriever.DEFAULT_SIMILARITY_THRESHOLD

CACHE_PATH = EVALS_DIR / "cache" / "query_embeddings.json"
RESULTS_PATH = EVALS_DIR / "results" / "retrieval-latest.json"


def cached(embed):
    """Wrap an embedding function so each (model, question) pair is only ever paid for once."""
    cache = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}

    def embed_cached(text):
        key = hashlib.sha256(f"{EMBEDDING_MODEL}\n{text}".encode()).hexdigest()
        if key not in cache:
            cache[key] = embed(text)
            CACHE_PATH.parent.mkdir(exist_ok=True)
            CACHE_PATH.write_text(json.dumps(cache))
        return cache[key]

    return embed_cached


def main():
    original_embed = retriever.create_query_embedding
    retriever.create_query_embedding = cached(original_embed)
    try:
        return _score()
    finally:
        # Put the real function back, so later suites in the same process (evals.baseline)
        # measure real embedding calls instead of cache hits.
        retriever.create_query_embedding = original_embed


def _score():

    rows = []
    for case in load_cases("rag"):
        # Threshold 0 so ranking is measured even when similarity is low.
        chunks = retriever.retrieve_relevant_chunks(case.question, max_results=K, similarity_threshold=0.0)
        files = [chunk["source"] for chunk in chunks]
        prod_files = [c["source"] for c in chunks[:PROD_TOP_K] if c["similarity_score"] >= PROD_THRESHOLD]
        relevant = {source.file for source in case.expected_sources}
        rows.append(
            {
                "id": case.id,
                "hit@5": hit_at_k(files, relevant, K),
                "recall@5": recall_at_k(files, relevant, K),
                "rr": reciprocal_rank(files, relevant),
                "prod_hit": hit_at_k(prod_files, relevant, PROD_TOP_K),
                "top_similarity": round(chunks[0]["similarity_score"], 3) if chunks else None,
                "retrieved": files,
            }
        )

    summary = {
        "hit@5": mean(r["hit@5"] for r in rows),
        "recall@5": mean(r["recall@5"] for r in rows),
        "mrr": mean(r["rr"] for r in rows),
        "prod_hit": mean(r["prod_hit"] for r in rows),
    }

    print(f"{'case':<9} {'hit@5':>5} {'recall':>6} {'rr':>5} {'prod':>5} {'top sim':>7}")
    for r in rows:
        print(
            f"{r['id']:<9} {'yes' if r['hit@5'] else 'NO':>5} {r['recall@5']:>6.2f} {r['rr']:>5.2f}"
            f" {'yes' if r['prod_hit'] else 'NO':>5} {r['top_similarity']!s:>7}"
        )
    print(f"\n{len(rows)} cases · embedding {EMBEDDING_MODEL}")
    for name, value in summary.items():
        print(f"  {name:<9} {value:.3f}")

    result = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "embedding_model": EMBEDDING_MODEL,
        "k": K,
        "prod": {"top_k": PROD_TOP_K, "threshold": PROD_THRESHOLD},
        "summary": summary,
        "cases": rows,
    }
    RESULTS_PATH.parent.mkdir(exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    main()
