from abc import ABC, abstractmethod
from typing import Any, Dict, List
from neo4j import Driver

from guardrails import P2GuardrailEngine, GuardrailResult
from movie_graph import search_movies
from metadata.catalog_metadata import CATALOG_METADATA, WATCH_CONTEXT_TAXONOMY

class BaseSkill(ABC):
    """Abstract Agent Skill Base Class."""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        pass

class SafetyP2GuardrailSkill(BaseSkill):
    """Skill 1: Safety & Harness Engineering Guardrail Audit."""
    def __init__(self):
        super().__init__(
            name="SafetyP2GuardrailSkill",
            description="Evaluates user prompts for prompt injection, jailbreaks, and unsafe commands."
        )
        self.engine = P2GuardrailEngine()

    def execute(self, prompt: str, **kwargs) -> Dict[str, Any]:
        res: GuardrailResult = self.engine.evaluate(prompt)
        return {
            "is_safe": res.is_safe,
            "risk_level": res.risk_level,
            "violation_type": res.violation_type,
            "warning_message": res.warning_message,
            "sanitized_prompt": res.sanitized_prompt
        }

class MovieGraphSearchSkill(BaseSkill):
    """Skill 2: Cypher Graph Traversal Search in Neo4j."""
    def __init__(self, database: Driver):
        super().__init__(
            name="MovieGraphSearchSkill",
            description="Searches Neo4j graph nodes and relationships using structured filters."
        )
        self.database = database

    def execute(self, filters: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        movies = search_movies(self.database, filters)
        return {
            "count": len(movies),
            "movies": movies
        }

class CohereVectorSearchSkill(BaseSkill):
    """Skill 3: Cohere Embeddings Semantic Vector Search."""
    def __init__(self, graph_rag_engine: Any):
        super().__init__(
            name="CohereVectorSearchSkill",
            description="Computes semantic vector similarity over Cohere embeddings for query matching."
        )
        self.rag_engine = graph_rag_engine

    def execute(self, query: str, filters: Dict[str, Any], top_k: int = 5, **kwargs) -> Dict[str, Any]:
        movies = self.rag_engine.hybrid_recommend(query, filters, top_k=top_k)
        return {
            "top_k": top_k,
            "recommended_movies": movies
        }

class StreamingPlatformSkill(BaseSkill):
    """Skill 4: OTT Streaming Platform Availability & Navigation."""
    def __init__(self):
        super().__init__(
            name="StreamingPlatformSkill",
            description="Resolves streaming availability, platform links, and subscription details."
        )

    def execute(self, movies: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        platform_breakdown = {}
        for m in movies:
            title = m.get("title", "Untitled")
            platform = m.get("platform") or "Not currently listed on major OTT"
            platform_breakdown[title] = {
                "platform": platform,
                "is_available": platform != "Not currently listed on major OTT",
                "watch_url_hint": f"Search '{title}' on {platform}" if platform != "Not currently listed on major OTT" else "Check theatrical re-releases or digital rental"
            }
        return {"streaming_details": platform_breakdown}

class WatchContextPlannerSkill(BaseSkill):
    """Skill 5: Social Watch Experience & Context Planner."""
    def __init__(self):
        super().__init__(
            name="WatchContextPlannerSkill",
            description="Plans viewing experience based on watch partners (solo, family, friends, life partner)."
        )

    def execute(self, context_key: str, **kwargs) -> Dict[str, Any]:
        key = (context_key or "solo").casefold()
        if "family" in key:
            matched_key = "family"
        elif "partner" in key or "date" in key or "couple" in key or "wife" in key or "husband" in key:
            matched_key = "life partner"
        elif "friend" in key or "buddy" in key or "buddies" in key or "group" in key:
            matched_key = "friend"
        else:
            matched_key = "solo"

        ctx_info = WATCH_CONTEXT_TAXONOMY.get(matched_key, WATCH_CONTEXT_TAXONOMY["solo"])
        return {
            "context_key": matched_key,
            "label": ctx_info["label"],
            "description": ctx_info["description"],
            "preferred_genres": ctx_info["preferred_genres"],
            "vibe_tips": ctx_info["vibe_tips"]
        }

class SkillRegistry:
    """Registry managing all agent skills."""
    def __init__(self, database: Driver, graph_rag_engine: Any):
        self.skills: Dict[str, BaseSkill] = {
            "guardrail": SafetyP2GuardrailSkill(),
            "graph_search": MovieGraphSearchSkill(database),
            "vector_search": CohereVectorSearchSkill(graph_rag_engine),
            "streaming": StreamingPlatformSkill(),
            "watch_planner": WatchContextPlannerSkill(),
        }

    def get_skill(self, name: str) -> BaseSkill:
        return self.skills[name]

    def list_skill_metadata(self) -> List[Dict[str, str]]:
        return [{"name": s.name, "description": s.description} for s in self.skills.values()]
