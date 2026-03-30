"""Batch embedding generation using OpenAI text-embedding-3-small."""

import time

from openai import OpenAI

from src.config.settings import OPENAI_API_KEY

client_oa = OpenAI(api_key=OPENAI_API_KEY)


def get_embeddings_batch(
    texts: list[str], batch_size: int = 2048, max_retries: int = 3
) -> list[list[float]]:
    """Generate embeddings for a list of texts in batches.

    Args:
        texts: List of strings to embed.
        batch_size: Max texts per OpenAI API call (limit: 2048).
        max_retries: Max retries per batch on transient failures.

    Returns:
        List of embedding vectors in the same order as input texts.
    """
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        for attempt in range(max_retries):
            try:
                response = client_oa.embeddings.create(
                    model="text-embedding-3-small",
                    input=chunk,
                )
                chunk_embeddings = [
                    item.embedding
                    for item in sorted(response.data, key=lambda x: x.index)
                ]
                all_embeddings.extend(chunk_embeddings)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"  ⚠️ Embedding error (retry {attempt + 1}/{max_retries} in {wait}s): {e}")
                    time.sleep(wait)
                else:
                    raise

    return all_embeddings
