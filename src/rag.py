"""
rag.py
───────
Retrieval-Augmented Generation over restaurant reviews.
Uses sentence-transformers to embed queries,
then pgvector similarity search via Supabase.

For reviews without embeddings yet, falls back to
keyword search over text_translated column.
"""

import os
from typing import Optional
import streamlit as st

# ── Embedding model ───────────────────────────────────────────────────────────
@st.cache_resource
def get_embed_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def embed_text(text: str) -> list[float]:
    model = get_embed_model()
    return model.encode(text, convert_to_tensor=False).tolist()


# ── Main RAG function ─────────────────────────────────────────────────────────

def retrieve_relevant_reviews(
    query: str,
    restaurant_id: Optional[int] = None,
    limit: int = 5,
) -> list[dict]:
    """
    Find the most relevant reviews for a natural language query.
    Tries vector search first, falls back to keyword search.

    Returns list of dicts with keys:
      text, stars, restaurant_name, similarity_score (optional)
    """
    from database import search_reviews_semantic, get_supabase

    # Try semantic search first
    try:
        query_emb = embed_text(query)
        results   = search_reviews_semantic(query_emb, restaurant_id, limit)
        if results:
            return results
    except Exception as e:
        print(f"Semantic search failed, using keyword fallback: {e}")

    # Keyword fallback — simple ILIKE search
    sb = get_supabase()
    words = query.lower().split()[:3]  # use first 3 words

    q = (
        sb.table("reviews")
        .select("text_translated, stars, restaurant_id, restaurants(name)")
    )
    if restaurant_id:
        q = q.eq("restaurant_id", restaurant_id)

    # Search for first keyword (simple fallback)
    if words:
        q = q.ilike("text_translated", f"%{words[0]}%")

    resp = q.limit(limit).execute()
    return resp.data or []


def format_reviews_for_context(reviews: list[dict]) -> str:
    """Format retrieved reviews into a readable context string for the LLM."""
    if not reviews:
        return "No relevant reviews found."

    lines = []
    for i, r in enumerate(reviews, 1):
        restaurant = (
            r.get("restaurants", {}).get("name", "")
            if isinstance(r.get("restaurants"), dict)
            else r.get("restaurant_name", "Unknown restaurant")
        )
        stars   = r.get("stars", "?")
        text    = r.get("text_translated") or r.get("text", "")
        score   = r.get("similarity", "")
        score_str = f" [similarity: {score:.2f}]" if score else ""

        lines.append(
            f"Review {i} — {restaurant} ({stars}★){score_str}:\n"
            f'"{text[:300]}{"..." if len(text) > 300 else ""}"'
        )

    return "\n\n".join(lines)


def answer_from_reviews(
    question: str,
    restaurant_id: Optional[int] = None,
) -> dict:
    """
    Full RAG pipeline:
    1. Retrieve relevant reviews
    2. Format as context
    3. Return context + source reviews (LLM call happens in agent.py)
    """
    reviews = retrieve_relevant_reviews(question, restaurant_id, limit=5)
    context = format_reviews_for_context(reviews)

    return {
        "context":  context,
        "sources":  reviews,
        "n_found":  len(reviews),
    }


# ── Embed and store reviews (run once during setup) ───────────────────────────

def embed_and_store_reviews(batch_size: int = 50):
    """
    Embed all reviews in the DB that don't have embeddings yet.
    Run this once after populating the reviews table.
    Safe to re-run — skips already-embedded reviews.
    """
    from database import get_supabase
    sb = get_supabase()

    # Get reviews without embeddings
    resp = (
        sb.table("reviews")
        .select("id, text_translated, text")
        .is_("embedding", "null")
        .limit(500)
        .execute()
    )
    reviews = resp.data or []

    if not reviews:
        print("All reviews already embedded.")
        return

    print(f"Embedding {len(reviews)} reviews...")
    model = get_embed_model()

    for i in range(0, len(reviews), batch_size):
        batch = reviews[i:i+batch_size]
        texts = [
            r.get("text_translated") or r.get("text", "")
            for r in batch
        ]
        texts = [t[:512] for t in texts]  # truncate for model

        embeddings = model.encode(texts, convert_to_tensor=False).tolist()

        for review, emb in zip(batch, embeddings):
            sb.table("reviews").update(
                {"embedding": emb}
            ).eq("id", review["id"]).execute()

        print(f"  Embedded {min(i+batch_size, len(reviews))}/{len(reviews)}")

    print("Done embedding reviews.")
