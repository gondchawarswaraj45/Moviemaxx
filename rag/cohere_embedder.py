import logging
import math
import numpy as np
from typing import List, Union
import cohere
from config import COHERE_API_KEY, COHERE_EMBED_MODEL

logger = logging.getLogger(__name__)

class CohereEmbedder:
    """
    Cohere API Embedding Service for Graph RAG vector search.
    Utilizes COHERE_API_KEY for embedding generation with embed-english-v3.0,
    with an offline fallback embedder if key is omitted.
    """
    def __init__(self, api_key: str = COHERE_API_KEY, model: str = COHERE_EMBED_MODEL):
        self.api_key = api_key or ""
        self.model = model
        self.client = None
        if self.api_key:
            try:
                # Support both Cohere v2 and v1 client signatures
                if hasattr(cohere, "ClientV2"):
                    self.client = cohere.ClientV2(api_key=self.api_key)
                else:
                    self.client = cohere.Client(api_key=self.api_key)
                logger.info("Initialized Cohere Embedder client.")
            except Exception as e:
                logger.warning(f"Failed to initialize Cohere client: {e}. Fallback active.")

    def embed_texts(self, texts: List[str], input_type: str = "search_document") -> List[List[float]]:
        if not texts:
            return []
        
        if self.client:
            try:
                if hasattr(self.client, "embed"):
                    res = self.client.embed(
                        texts=texts,
                        model=self.model,
                        input_type=input_type,
                        embedding_types=["float"]
                    )
                    if hasattr(res, "embeddings"):
                        embeddings = res.embeddings
                        if hasattr(embeddings, "float_"):
                            return embeddings.float_
                        elif isinstance(embeddings, list):
                            return embeddings
                        elif hasattr(embeddings, "float"):
                            return embeddings.float
            except Exception as e:
                logger.warning(f"Cohere embedding API call failed: {e}. Falling back to deterministic embedding.")

        # Fallback deterministic vector generator (dimension 384)
        return [self._fallback_embed(text) for text in texts]

    def embed_query(self, query: str) -> List[float]:
        res = self.embed_texts([query], input_type="search_query")
        return res[0] if res else self._fallback_embed(query)

    def _fallback_embed(self, text: str, dim: int = 384) -> List[float]:
        """Deterministic TF-IDF/Feature Hashing embedding generator for offline/keyless execution."""
        words = text.lower().split()
        vector = np.zeros(dim, dtype=np.float32)
        if not words:
            return vector.tolist()
        
        for idx, word in enumerate(words):
            hash_val = hash(word)
            pos = abs(hash_val) % dim
            sign = 1.0 if (hash_val % 2 == 0) else -1.0
            weight = 1.0 / (1.0 + math.log(idx + 1))
            vector[pos] += sign * weight
            
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
