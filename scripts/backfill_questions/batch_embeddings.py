"""Batch embedding generation using OpenAI text-embedding-3-small."""

from openai import OpenAI

from src.config.settings import OPENAI_API_KEY

client_oa = OpenAI(api_key=OPENAI_API_KEY)


def get_embeddings_batch(
    texts: list[str], batch_size: int = 2048
) -> list[list[float]]:
    """Generate embeddings for a list of texts in batches.

    Args:
        texts: List of strings to embed.
        batch_size: Max texts per OpenAI API call (limit: 2048).

    Returns:
        List of embedding vectors in the same order as input texts.
    """
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        response = client_oa.embeddings.create(
            model="text-embedding-3-small",
            input=chunk,
        )
        chunk_embeddings = [
            item.embedding
            for item in sorted(response.data, key=lambda x: x.index)
        ]
        all_embeddings.extend(chunk_embeddings)

    return all_embeddings
