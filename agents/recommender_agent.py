from typing import Any, Dict, List
from .base_agent import BaseAgent
from rag.graph_rag import GraphRAGEngine

class RecommenderAgent(BaseAgent):
    """
    Sub-Agent 2: Graph RAG Movie Recommender Agent.
    Utilizes Graph RAG (Neo4j Cypher Traversal + Cohere Embeddings Vector Search)
    to select and rank top 5 movie recommendations for the user query.
    """
    def __init__(self, graph_rag_engine: GraphRAGEngine):
        super().__init__(
            name="RecommenderAgent",
            role="Top-5 Graph RAG Movie Recommender"
        )
        self.rag_engine = graph_rag_engine

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        query = input_data.get("question", "")
        filters = input_data.get("filters", {})
        top_k = input_data.get("top_k", 5)

        # Execute Graph RAG hybrid search
        recommended_movies = self.rag_engine.hybrid_recommend(query, filters, top_k=top_k)

        return {
            "agent": self.name,
            "recommended_count": len(recommended_movies),
            "movies": recommended_movies,
            "rag_mode": "graph_cohere_hybrid"
        }
