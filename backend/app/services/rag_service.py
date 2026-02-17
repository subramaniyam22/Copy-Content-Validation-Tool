"""RAG service — embed guideline rules and retrieve relevant ones for validation."""
import numpy as np
from typing import Optional

from openai import AzureOpenAI
from app.config import settings
from app.utils.logging import logger


class RAGService:
    """In-memory vector store for guideline rule retrieval (pgvector-ready schema)."""

    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.OPENAI_API_KEY,
            api_version=settings.API_VERSION,
            azure_endpoint=settings.AZURE_ENDPOINT,
        )
        self.embedding_model = settings.EMBEDDING_MODEL
        # In-memory store: {rule_id: {"embedding": [...], "rule": {...}}}
        self._store: dict[int, dict] = {}

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a text string."""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text[:8000],  # Truncate for token limit
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return []

    def index_rules(self, rules: list[dict]):
        """
        Index guideline rules for retrieval.
        Each rule: {id, rule_id, rule_text, fix_template, examples_good, examples_bad, ...}
        """
        for rule in rules:
            text_to_embed = f"{rule.get('rule_text', '')} {rule.get('fix_template', '')} {rule.get('examples_good', '')} {rule.get('examples_bad', '')}"
            embedding = self.embed_text(text_to_embed.strip())
            if embedding:
                self._store[rule.get("id", id(rule))] = {
                    "embedding": embedding,
                    "rule": rule,
                }

        logger.info(f"Indexed {len(self._store)} rules for RAG retrieval")

    def retrieve(self, query_text: str, top_n: int = 5) -> list[dict]:
        """Retrieve top-N most relevant rules for a given text chunk."""
        if not self._store:
            return []

        query_emb = self.embed_text(query_text)
        if not query_emb:
            return []

        query_vec = np.array(query_emb)
        scored = []

        for rule_id, data in self._store.items():
            stored_vec = np.array(data["embedding"])
            # Cosine similarity
            dot = np.dot(query_vec, stored_vec)
            norm = np.linalg.norm(query_vec) * np.linalg.norm(stored_vec)
            similarity = dot / norm if norm > 0 else 0
            scored.append((similarity, data["rule"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [rule for _, rule in scored[:top_n]]

    def clear(self):
        """Clear the in-memory store."""
        self._store.clear()
