import logging
from typing import Any, Dict, List, Tuple
from neo4j import Driver

from .cohere_embedder import CohereEmbedder
from .chunker import RelativeChunker, TextChunk
from movie_graph import search_movies, load_movie_rows

logger = logging.getLogger(__name__)

class GraphRAGEngine:
    """
    Graph RAG Engine combining Neo4j Knowledge Graph Traversal
    with Cohere Vector Embeddings and Relative Chunking.
    """
    def __init__(self, database: Driver, cohere_api_key: str = ""):
        self.database = database
        self.embedder = CohereEmbedder(api_key=cohere_api_key)
        self.chunker = RelativeChunker()
        self._chunks: List[TextChunk] = []
        self._chunk_embeddings: List[List[float]] = []
        self._is_indexed = False

    def initialize_vector_index(self) -> int:
        """Loads catalog movies, chunks dataset relatively, and generates Cohere embeddings."""
        if self._is_indexed:
            return len(self._chunks)
            
        try:
            movies = load_movie_rows()
            self._chunks = self.chunker.chunk_catalog(movies)
            texts = [c.text for c in self._chunks]
            
            # Batch embedding generation
            logger.info(f"Generating Cohere embeddings for {len(texts)} relative chunks...")
            self._chunk_embeddings = self.embedder.embed_texts(texts, input_type="search_document")
            self._is_indexed = True
            logger.info(f"Graph RAG Vector Index successfully built with {len(self._chunks)} chunks.")
            return len(self._chunks)
        except Exception as e:
            logger.exception(f"Error building Graph RAG vector index: {e}")
            return 0

    def hybrid_recommend(self, query: str, filters: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Executes Graph RAG: Fuses Neo4j Graph Traversal with Cohere Vector Search.
        Always returns exactly top_k (default 5) movies ranked by Graph RAG score.
        """
        # Ensure vector index is initialized
        if not self._is_indexed:
            self.initialize_vector_index()

        # 1. Neo4j Graph Search (Cypher)
        # Query extra candidates to allow hybrid re-ranking
        graph_filters = dict(filters)
        graph_filters["limit"] = max(20, top_k * 3)
        graph_movies = search_movies(self.database, graph_filters)

        # Map candidate IDs
        candidate_map: Dict[str, Dict[str, Any]] = {m["id"]: m for m in graph_movies}

        # 2. Cohere Vector Similarity Search
        query_vector = self.embedder.embed_query(query)
        vector_scores: Dict[str, float] = {}

        if self._chunk_embeddings and self._chunks:
            for idx, chunk in enumerate(self._chunks):
                sim = self.embedder.cosine_similarity(query_vector, self._chunk_embeddings[idx])
                m_id = chunk.movie_id
                # Keep maximum chunk similarity score per movie
                if m_id not in vector_scores or sim > vector_scores[m_id]:
                    vector_scores[m_id] = sim

        # 3. Hybrid Graph RAG Fusion (Combined Scoring)
        fused_results: List[Tuple[float, Dict[str, Any]]] = []

        # If graph search returned candidates, score them with both Graph & Vector weights
        if candidate_map:
            max_rating = 10.0
            for rank, (m_id, movie) in enumerate(candidate_map.items()):
                # Graph Score: normalized rank + IMDb rating
                graph_rank_score = 1.0 - (rank / max(len(candidate_map), 1))
                rating_score = (movie.get("rating") or 5.0) / max_rating
                g_score = 0.6 * graph_rank_score + 0.4 * rating_score

                # Vector Score from Cohere embedding
                v_score = vector_scores.get(m_id, 0.5)

                # Final Hybrid Fusion Score (0.5 Graph + 0.5 Vector)
                hybrid_score = 0.5 * g_score + 0.5 * v_score

                movie_item = dict(movie)
                movie_item["vector_similarity"] = round(float(v_score), 4)
                movie_item["graph_score"] = round(float(g_score), 4)
                movie_item["hybrid_score"] = round(float(hybrid_score), 4)
                fused_results.append((hybrid_score, movie_item))
        else:
            # Fallback to pure Cohere Vector Search if graph filtering was too strict
            top_vector_mids = sorted(vector_scores.items(), key=lambda x: x[1], reverse=True)[:top_k*2]
            all_movies = {m["id"]: m for m in load_movie_rows()}
            for m_id, v_score in top_vector_mids:
                if m_id in all_movies:
                    m_data = all_movies[m_id]["properties"]
                    m_data["id"] = m_id
                    m_data["genres"] = all_movies[m_id].get("genres", [])
                    m_data["cast"] = [c["name"] for c in all_movies[m_id].get("cast", [])[:4]]
                    m_data["vector_similarity"] = round(float(v_score), 4)
                    m_data["graph_score"] = 0.0
                    m_data["hybrid_score"] = round(float(v_score), 4)
                    fused_results.append((v_score, m_data))

        # Sort by hybrid score descending
        fused_results.sort(key=lambda x: x[0], reverse=True)

        # Extract top_k movies (default 5 movies as per query hits requirement)
        recommended_movies = [item[1] for item in fused_results[:top_k]]
        return recommended_movies
