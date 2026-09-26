import logging
from typing import Any, Dict, List
from neo4j import Driver

from .guardrail_agent import GuardrailAgent
from .recommender_agent import RecommenderAgent
from .streaming_agent import StreamingAgent
from .watch_planner_agent import WatchPlannerAgent
from rag.graph_rag import GraphRAGEngine

logger = logging.getLogger(__name__)

class CoordinatorAgent:
    """
    Master Multi-Agent Coordinator for Moviemaxx.
    Orchestrates GuardrailAgent, RecommenderAgent, StreamingAgent, and WatchPlannerAgent
    to process queries, enforce P2 guardrails, retrieve top 5 Graph RAG recommendations,
    provide streaming navigation, and construct tailored watch plans.
    """
    def __init__(self, database: Driver, cohere_api_key: str = ""):
        self.database = database
        self.graph_rag_engine = GraphRAGEngine(database, cohere_api_key=cohere_api_key)
        
        # Sub-agents
        self.guardrail_agent = GuardrailAgent()
        self.recommender_agent = RecommenderAgent(self.graph_rag_engine)
        self.streaming_agent = StreamingAgent()
        self.watch_planner_agent = WatchPlannerAgent()

    def process_query(self, question: str, filters: Dict[str, Any], watch_context: str = "") -> Dict[str, Any]:
        logger.info(f"CoordinatorAgent processing user question: '{question}'")

        # Step 1: P2 Guardrail Safety Audit
        guardrail_res = self.guardrail_agent.process({"question": question})
        if not guardrail_res.get("is_safe"):
            logger.warning(f"Query blocked by P2 GuardrailAgent: {guardrail_res.get('violation_type')}")
            return {
                "status": "BLOCKED",
                "guardrail": guardrail_res,
                "reply": f"⚠️ {guardrail_res.get('warning_message')}\nYour query was flagged by Moviemaxx P2 Harness Engineering Guardrails. Please rephrase your movie request.",
                "movies": [],
                "agent_contributions": [self.guardrail_agent.name]
            }

        # Step 2: Graph RAG Recommendation (Top 5 Movies)
        rec_res = self.recommender_agent.process({
            "question": question,
            "filters": filters,
            "top_k": 5
        })
        movies: List[Dict[str, Any]] = rec_res.get("movies", [])

        # Step 3: OTT Streaming Platform Navigation
        stream_res = self.streaming_agent.process({"movies": movies})

        # Step 4: Social Watch Context Experience Planner
        planner_res = self.watch_planner_agent.process({
            "question": question,
            "watch_context": watch_context,
            "movies": movies
        })

        # Step 5: Synthesize Clean Response Summary
        reply_text = self._synthesize_response(
            question=question,
            movies=movies,
            stream_info=stream_res,
            planner_info=planner_res
        )

        return {
            "status": "SUCCESS",
            "reply": reply_text,
            "movies": movies,
            "filters": filters,
            "guardrail": guardrail_res,
            "streaming": stream_res,
            "watch_plan": planner_res,
            "agent_contributions": [
                self.guardrail_agent.name,
                self.recommender_agent.name,
                self.streaming_agent.name,
                self.watch_planner_agent.name
            ]
        }

    def _synthesize_response(
        self,
        question: str,
        movies: List[Dict[str, Any]],
        stream_info: Dict[str, Any],
        planner_info: Dict[str, Any]
    ) -> str:
        if not movies:
            return "I searched the Neo4j Graph and Cohere Vector Index, but couldn't find matching films. Try adjusting the genre, year, or streaming platform!"

        ctx_label = planner_info.get("context_label", "Solo Chill")
        vibe_tips = planner_info.get("vibe_tips", "")

        return (
            f"🎬 **Top 5 Moviemaxx Recommendations for {ctx_label}**\n"
            f"💡 **Watch Plan Vibe:** {vibe_tips}\n"
            f"🕸️ *Traversed Neo4j Knowledge Graph relationships (HAS_GENRE, FEATURES, AVAILABLE_ON) & Cohere Embeddings.*"
        )
