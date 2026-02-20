from typing import List

from openai import OpenAI

from src.config.settings import OPENAI_API_KEY

client_oa = OpenAI(api_key=OPENAI_API_KEY)


def get_embedding(text: str) -> List[float]:
    """Generate embedding for text using OpenAI."""
    response = client_oa.embeddings.create(model="text-embedding-3-small", input=text)
    return response.data[0].embedding
