"""Embedding provider adapter for Google Gemini API."""
import os
from typing import Protocol
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Embedder implementation using Google Gemini's gemini-embedding-001."""

    def __init__(self, model_name: str = "gemini-embedding-001", dimensions: int = 768) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")

        self.model_name = model_name
        self.dimensions = dimensions
        self.client = genai.Client(api_key=self.api_key)

    def embed_documents(self, texts: list[str], batch_size: int = 50) -> list[list[float]]:
        """Batch embed document chunks to stay within API payload limits."""
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=batch,
                config=types.EmbedContentConfig(output_dimensionality=self.dimensions),
            )
            for emb in response.embeddings:
                all_vectors.append(emb.values)
        return all_vectors

    def embed_query(self, question: str) -> list[float]:
        """Embed a single query question."""
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=question,
            config=types.EmbedContentConfig(output_dimensionality=self.dimensions),
        )
        return response.embeddings[0].values
