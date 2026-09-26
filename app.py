import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq
from neo4j import Driver, GraphDatabase
from neo4j.exceptions import Neo4jError
from pydantic import BaseModel, Field

from config import (
    BASE_DIR,
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    NEO4J_DATABASE,
    GROQ_MODEL,
    GROQ_API_KEY,
    COHERE_API_KEY
)
from logger_config import app_logger
from movie_graph import (
    DATABASE,
    import_catalog,
    recent_recommendations,
    save_recommendation_turn,
    search_movies,
    load_movie_rows,
)
from guardrails import P2GuardrailEngine
from mcp import Neo4jMCPClient
from metadata import CATALOG_METADATA, WATCH_CONTEXT_TAXONOMY, SkillRegistry
from agents import CoordinatorAgent

load_dotenv()

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
driver: Optional[Driver] = None
coordinator_agent: Optional[CoordinatorAgent] = None
mcp_client: Optional[Neo4jMCPClient] = None
skill_registry: Optional[SkillRegistry] = None

if NEO4J_URI and NEO4J_USERNAME and NEO4J_PASSWORD:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    mcp_client = Neo4jMCPClient(driver=driver)
    coordinator_agent = CoordinatorAgent(database=driver, cohere_api_key=COHERE_API_KEY)
    skill_registry = SkillRegistry(database=driver, graph_rag_engine=coordinator_agent.graph_rag_engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    app_logger.info("Starting up Moviemaxx Multi-Agent Graph RAG Application...")
    yield
    app_logger.info("Shutting down Moviemaxx Application...")
    if driver:
        driver.close()


app = FastAPI(
    title="Moviemaxx Multi-Agent Movie Graph & Graph RAG",
    description=(
        "Production API for Moviemaxx Bollywood Movie Recommender featuring Neo4j Knowledge Graph, "
        "Cohere Embeddings Graph RAG, P2 Harness Engineering Guardrails, MCP Server Integration, "
        "System Metadata Skills, and Multi-Agent Experience Planning."
    ),
    version="2.0.0",
    lifespan=lifespan
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.exception_handler(Neo4jError)
async def handle_database_error(_, __) -> JSONResponse:
    app_logger.exception("Neo4j request failed")
    return JSONResponse(
        status_code=503,
        content={"detail": "Neo4j request failed. Check the configured instance and write permissions."},
    )


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1500, example="Find 5 top-rated comedy movies for family night")
    watch_context: Optional[str] = Field(default="solo", description="solo, family, friend, life partner")


class SubgraphRequest(BaseModel):
    movie_ids: List[str]


class MCPQueryRequest(BaseModel):
    query: str
    read_only: bool = True
    parameters: Optional[Dict[str, Any]] = None


def require_driver() -> Driver:
    if driver is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j is not configured. Add NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD to .env.",
        )
    return driver


def catalog_genres(database: Driver) -> List[str]:
    with database.session(database=DATABASE) as session:
        records = session.execute_read(
            lambda tx: list(tx.run("MATCH (genre:Genre) RETURN genre.name AS name ORDER BY name"))
        )
    return [record["name"] for record in records]


def catalog_overview(database: Driver) -> Dict[str, Any]:
    import_catalog(database)
    with database.session(database=DATABASE) as session:
        record = session.execute_read(
            lambda tx: tx.run("MATCH (movie:Movie) RETURN count(movie) AS count").single()
        )
    genres = catalog_genres(database)
    featured = search_movies(database, {"limit": 5})
    history = recent_recommendations(database)
    return {
        "movie_count": record["count"] if record else 0,
        "genres": genres,
        "featured": featured,
        "history": history,
        "agent_mode": "multi_agent_groq" if groq_client else "multi_agent_local",
        "mcp_status": mcp_client.get_status() if mcp_client else {},
        "cohere_rag_active": bool(COHERE_API_KEY),
        "watch_contexts": WATCH_CONTEXT_TAXONOMY
    }


def _safe_text(value: Any, maximum: int = 80) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned[:maximum] or None


_resolved_groq_model: Optional[str] = None


def resolve_groq_model() -> Optional[str]:
    global _resolved_groq_model
    if groq_client is None:
        return None
    if _resolved_groq_model:
        return _resolved_groq_model
    try:
        available = {model.id for model in groq_client.models.list().data}
    except Exception as error:
        app_logger.warning(f"Unable to list Groq models ({type(error).__name__})")
        return None

    _resolved_groq_model = next(
        (model for model in (GROQ_MODEL, "llama-3.3-70b-versatile", "openai/gpt-oss-20b") if model in available),
        None,
    )
    return _resolved_groq_model


def _normalise_filters(raw: Dict[str, Any], genres: List[str]) -> Dict[str, Any]:
    requested_genres = raw.get("genres", [])
    if isinstance(requested_genres, str):
        requested_genres = [requested_genres]
    genre_lookup = {genre.casefold(): genre for genre in genres}
    selected_genres = []
    if isinstance(requested_genres, list):
        for value in requested_genres:
            if isinstance(value, str) and value.casefold() in genre_lookup:
                selected_genres.append(genre_lookup[value.casefold()])

    year = raw.get("year")
    try:
        year = int(year) if year not in (None, "") else None
    except (TypeError, ValueError):
        year = None
    if year is not None and not 1900 <= year <= 2100:
        year = None

    try:
        minimum_rating = float(raw.get("minimum_rating"))
    except (TypeError, ValueError):
        minimum_rating = None
    if minimum_rating is not None and not 0 <= minimum_rating <= 10:
        minimum_rating = None

    try:
        limit = int(raw.get("limit", 5))
    except (TypeError, ValueError):
        limit = 5

    return {
        "genres": list(dict.fromkeys(selected_genres)),
        "actor": _safe_text(raw.get("actor")),
        "director": _safe_text(raw.get("director")),
        "year": year,
        "minimum_rating": minimum_rating,
        "platform": _safe_text(raw.get("platform")),
        "title": _safe_text(raw.get("title")),
        "theme": _safe_text(raw.get("theme")),
        "limit": max(1, min(limit, 12)),
    }


def fallback_filters(question: str, genres: List[str], history: List[Dict[str, Any]]) -> Dict[str, Any]:
    lowered = question.casefold()
    selected_genres = [genre for genre in genres if re.search(rf"\b{re.escape(genre.casefold())}\b", lowered)]
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", lowered)
    rating_match = re.search(r"(?:rated|rating|above)\s*(?:above\s*)?(\d(?:\.\d)?)", lowered)
    minimum_rating = float(rating_match.group(1)) if rating_match else None
    if minimum_rating is None and any(phrase in lowered for phrase in ("highly rated", "top rated", "best rated")):
        minimum_rating = 7.0
    actor_match = re.search(r"\b(?:starring|with actor|actor)\s+([a-z][a-z .'-]{1,50})", question, re.IGNORECASE)
    director_match = re.search(r"\bdirected by\s+([a-z][a-z .'-]{1,50})", question, re.IGNORECASE)
    platform = next((name for name in ("netflix", "prime video", "jiocinema", "sonyliv", "zee5") if name in lowered), None)
    filters = {
        "genres": selected_genres,
        "actor": actor_match.group(1).strip() if actor_match else None,
        "director": director_match.group(1).strip() if director_match else None,
        "year": int(year_match.group(1)) if year_match else None,
        "minimum_rating": minimum_rating,
        "platform": platform,
        "title": None,
        "theme": None,
        "limit": 5,
    }
    if history and any(phrase in lowered for phrase in ("more like", "similar to those", "another like", "more like that")):
        previous = history[0].get("filters") or {}
        filters.update({key: previous.get(key) for key in filters if key in previous})
    return _normalise_filters(filters, genres)


def apply_follow_up_memory(
    question: str,
    filters: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    lowered = question.casefold()
    follow_up_phrases = ("more like", "similar to those", "another like", "more like that")
    if not history or not any(phrase in lowered for phrase in follow_up_phrases):
        return filters

    previous = history[0]
    previous_filters = previous.get("filters") or {}
    remembered = dict(filters)
    for key in ("genres", "actor", "director", "year", "minimum_rating", "platform", "title", "theme"):
        if not remembered.get(key) and previous_filters.get(key):
            remembered[key] = previous_filters[key]
    excluded = list(previous_filters.get("exclude_ids") or [])
    excluded.extend(movie.get("id") for movie in previous.get("movies", []) if movie and movie.get("id"))
    remembered["exclude_ids"] = list(dict.fromkeys(excluded))
    return remembered


def requested_result_limit(question: str, default_limit: int) -> int:
    singular_request = re.search(
        r"\b(?:a|an|one|single|any)\s+(?:[a-z0-9]+(?:[-'][a-z0-9]+)*\s+){0,3}(?:movie|film)\b",
        question,
        re.IGNORECASE,
    )
    if singular_request:
        return 1
    return max(1, min(default_limit, 12))


def compose_answer(
    question: str,
    filters: Dict[str, Any],
    movies: List[Dict[str, Any]],
    history: List[Dict[str, Any]],
) -> Tuple[str, bool]:
    if not movies:
        return "I couldn't verify matching films in the catalog.", False

    qualifiers = []
    if filters.get("genres"):
        qualifiers.append("genre: " + ", ".join(filters["genres"]))
    if filters.get("year"):
        qualifiers.append(f"year: {filters['year']}")
    if filters.get("minimum_rating") is not None:
        qualifiers.append(f"catalog rating: {filters['minimum_rating']}+")

    result_phrase = "this film" if len(movies) == 1 else "these films"
    intro = f"I found {result_phrase} in the Neo4j catalog"
    if qualifiers:
        intro += " (" + "; ".join(qualifiers) + ")"
    intro += "."
    details = []
    for movie in movies:
        fields = [str(movie.get("year") or "year unknown")]
        if movie.get("rating") is not None:
            fields.append(f"catalog rating {movie['rating']}")
        if movie.get("genres"):
            fields.append("genres: " + ", ".join(movie["genres"]))
        details.append(f"- {movie.get('title', 'Untitled')} · " + " · ".join(fields))
    follow_up = "Want another recommendation?" if len(movies) == 1 else "Want to narrow these by another filter?"
    return intro + "\n" + "\n".join(details) + "\n" + follow_up, False


def extract_filters(question: str, genres: List[str], history: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], bool]:
    model = resolve_groq_model()
    if model is None:
        return fallback_filters(question, genres, history), False

    try:
        response = groq_client.chat.completions.create(
            model=model,
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Convert a movie request into JSON search filters for Neo4j. "
                        "Return only keys: genres (array), actor, director, year, minimum_rating, platform, title, theme, limit (default 5)."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"question": question, "available_genres": genres}),
                },
            ],
        )
        content = response.choices[0].message.content or "{}"
        return _normalise_filters(json.loads(content), genres), True
    except Exception:
        return fallback_filters(question, genres, history), False


# ==========================================
# WEB UI ROUTES
# ==========================================

@app.get("/", summary="Serve Main Recommender Web UI", tags=["Web UI"])
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/graph", summary="Serve Knowledge Graph Explorer Web UI", tags=["Web UI"])
def graph_page() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "graph.html")


# ==========================================
# CORE SYSTEM ENDPOINTS
# ==========================================

@app.get("/api/health", summary="Health Check", tags=["System"])
def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "neo4j_configured": driver is not None,
        "groq_configured": groq_client is not None,
        "cohere_configured": bool(COHERE_API_KEY),
        "mcp_available": mcp_client.is_mcp_executable_available() if mcp_client else False,
        "p2_guardrails_active": True,
        "multi_agent_system_ready": coordinator_agent is not None
    }


@app.get("/api/overview", summary="Catalog Overview", tags=["System"])
def overview() -> Dict[str, Any]:
    database = require_driver()
    return catalog_overview(database)


@app.get("/api/metadata/skills", summary="System Metadata and Agent Skills", tags=["Metadata & Skills"])
def get_skills_metadata() -> Dict[str, Any]:
    if not skill_registry:
        raise HTTPException(status_code=503, detail="Skill registry not initialized.")
    return {
        "catalog_metadata": CATALOG_METADATA,
        "watch_contexts": WATCH_CONTEXT_TAXONOMY,
        "agent_skills": skill_registry.list_skill_metadata()
    }


# ==========================================
# FASTAPI API DIAGNOSTIC TEST SUITE ENDPOINTS
# ==========================================

@app.get("/api/test/neo4j", summary="Test Neo4j Graph Database Connection & Query", tags=["Diagnostic Tests"])
def test_neo4j_db() -> Dict[str, Any]:
    database = require_driver()
    start_time = time.time()
    try:
        with database.session(database=DATABASE) as session:
            res = session.run(
                "MATCH (m:Movie) RETURN count(m) AS total_movies, count(DISTINCT m.platform) AS total_platforms"
            ).single()
            latency_ms = round((time.time() - start_time) * 1000, 2)
            app_logger.info(f"API Test /api/test/neo4j passed in {latency_ms}ms")
            return {
                "test": "Neo4j Graph Database Test",
                "status": "PASSED",
                "latency_ms": latency_ms,
                "database_name": DATABASE,
                "node_count": res["total_movies"] if res else 0,
                "platform_count": res["total_platforms"] if res else 0,
                "message": "Successfully executed Cypher graph query on connected Neo4j instance."
            }
    except Exception as e:
        app_logger.error(f"API Test /api/test/neo4j failed: {e}")
        return {"test": "Neo4j Graph Database Test", "status": "FAILED", "error": str(e)}


@app.get("/api/test/llm", summary="Test Groq LLM Model Completion", tags=["Diagnostic Tests"])
def test_llm_model() -> Dict[str, Any]:
    model_name = resolve_groq_model()
    if not groq_client or not model_name:
        return {
            "test": "LLM Model Test",
            "status": "SKIPPED",
            "message": "Groq LLM is not configured or GROQ_API_KEY is missing. App is running in local fallback mode."
        }

    start_time = time.time()
    try:
        response = groq_client.chat.completions.create(
            model=model_name,
            max_tokens=60,
            messages=[{"role": "user", "content": "Respond with 'Groq LLM connection operational'."}]
        )
        latency_ms = round((time.time() - start_time) * 1000, 2)
        reply = response.choices[0].message.content.strip()
        app_logger.info(f"API Test /api/test/llm passed in {latency_ms}ms")
        return {
            "test": "LLM Model Test",
            "status": "PASSED",
            "latency_ms": latency_ms,
            "model_used": model_name,
            "llm_response": reply
        }
    except Exception as e:
        app_logger.error(f"API Test /api/test/llm failed: {e}")
        return {"test": "LLM Model Test", "status": "FAILED", "error": str(e)}


@app.get("/api/test/embeddings", summary="Test Cohere Embedding Model Generation", tags=["Diagnostic Tests"])
def test_embedding_model() -> Dict[str, Any]:
    if not coordinator_agent:
        raise HTTPException(status_code=503, detail="Coordinator agent not ready.")

    start_time = time.time()
    try:
        embedder = coordinator_agent.graph_rag_engine.embedder
        sample_text = "Dabangg action comedy Bollywood movie"
        vector = embedder.embed_query(sample_text)
        latency_ms = round((time.time() - start_time) * 1000, 2)
        
        is_cohere_native = embedder.client is not None
        app_logger.info(f"API Test /api/test/embeddings passed in {latency_ms}ms")
        return {
            "test": "Embedding Model Test",
            "status": "PASSED",
            "latency_ms": latency_ms,
            "provider": "Cohere API (native)" if is_cohere_native else "Deterministic Local Embedder (Fallback)",
            "model_name": embedder.model,
            "sample_input": sample_text,
            "vector_dimension": len(vector),
            "vector_sample": [round(float(v), 5) for v in vector[:5]]
        }
    except Exception as e:
        app_logger.error(f"API Test /api/test/embeddings failed: {e}")
        return {"test": "Embedding Model Test", "status": "FAILED", "error": str(e)}


@app.get("/api/test/vector-db", summary="Test Vector Similarity Search Index", tags=["Diagnostic Tests"])
def test_vector_db_search() -> Dict[str, Any]:
    if not coordinator_agent:
        raise HTTPException(status_code=503, detail="Coordinator agent not ready.")

    start_time = time.time()
    try:
        rag_engine = coordinator_agent.graph_rag_engine
        results = rag_engine.hybrid_recommend("high energy comedy movie", {}, top_k=5)
        latency_ms = round((time.time() - start_time) * 1000, 2)
        
        app_logger.info(f"API Test /api/test/vector-db passed in {latency_ms}ms")
        return {
            "test": "Vector Database Search Test",
            "status": "PASSED",
            "latency_ms": latency_ms,
            "vector_chunks_indexed": len(rag_engine._chunks),
            "top_matched_count": len(results),
            "top_matched_movies": [
                {
                    "id": m.get("id"),
                    "title": m.get("title"),
                    "vector_similarity": m.get("vector_similarity"),
                    "hybrid_score": m.get("hybrid_score")
                }
                for m in results
            ]
        }
    except Exception as e:
        app_logger.error(f"API Test /api/test/vector-db failed: {e}")
        return {"test": "Vector Database Search Test", "status": "FAILED", "error": str(e)}


# ==========================================
# KNOWLEDGE GRAPH DATA API (For Graph UI)
# ==========================================

@app.post("/api/graph/subgraph", summary="Get Neo4j Subgraph for Recommended Movies", tags=["Knowledge Graph UI"])
def get_recommendation_subgraph(req: SubgraphRequest) -> Dict[str, Any]:
    database = require_driver()
    if not req.movie_ids:
        return {"nodes": [], "edges": []}

    query = """
    MATCH (m:Movie) WHERE m.id IN $movie_ids
    OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
    OPTIONAL MATCH (m)-[:FEATURES]->(p:Person)
    OPTIONAL MATCH (m)-[:AVAILABLE_ON]->(plat:Platform)
    RETURN m.id AS m_id, m.title AS title, m.year AS year,
           collect(DISTINCT g.name) AS genres,
           collect(DISTINCT p.name)[0..2] AS actors,
           plat.name AS platform
    """
    with database.session(database=DATABASE) as session:
        records = session.execute_read(lambda tx: list(tx.run(query, movie_ids=req.movie_ids)))

    nodes_dict = {}
    edges_list = []

    for r in records:
        m_id = r["m_id"]
        title = f"{r['title']} ({r['year'] or ''})"
        nodes_dict[m_id] = {"id": m_id, "label": title, "color": "#8b5cf6", "group": "Movie"}

        for g_name in (r["genres"] or []):
            g_id = f"genre_{g_name.lower()}"
            if g_id not in nodes_dict:
                nodes_dict[g_id] = {"id": g_id, "label": g_name, "color": "#10b981", "group": "Genre"}
            edges_list.append({"from": m_id, "to": g_id, "label": "HAS_GENRE"})

        for a_name in (r["actors"] or []):
            a_id = f"actor_{a_name.lower().replace(' ', '_')}"
            if a_id not in nodes_dict:
                nodes_dict[a_id] = {"id": a_id, "label": a_name, "color": "#f59e0b", "group": "Person"}
            edges_list.append({"from": m_id, "to": a_id, "label": "FEATURES"})

        plat = r["platform"]
        if plat:
            plat_id = f"plat_{plat.lower().replace(' ', '_')}"
            if plat_id not in nodes_dict:
                nodes_dict[plat_id] = {"id": plat_id, "label": plat, "color": "#ec4899", "group": "Platform"}
            edges_list.append({"from": m_id, "to": plat_id, "label": "AVAILABLE_ON"})

    return {"nodes": list(nodes_dict.values()), "edges": edges_list}


@app.get("/api/graph/data", summary="Get Knowledge Graph Data for Visual Explorer", tags=["Knowledge Graph UI"])
def get_graph_data(mode: str = Query(default="catalog", description="catalog or metadata")) -> Dict[str, Any]:
    database = require_driver()

    if mode.lower() == "metadata":
        nodes = []
        edges = []

        for name, meta in CATALOG_METADATA["nodes"].items():
            nodes.append({
                "id": f"schema_{name}",
                "label": f"Schema: {name}",
                "color": "#3b82f6",
                "title": meta.get("description", "")
            })

        for ctx_key, ctx_val in WATCH_CONTEXT_TAXONOMY.items():
            nodes.append({
                "id": f"context_{ctx_key}",
                "label": f"Watch Context: {ctx_val['label']}",
                "color": "#ec4899",
                "title": ctx_val.get("description", "")
            })
            edges.append({
                "from": f"context_{ctx_key}",
                "to": "schema_Movie",
                "label": "RECOMMENDS_FOR"
            })

        if skill_registry:
            for skill in skill_registry.skills.values():
                nodes.append({
                    "id": f"skill_{skill.name}",
                    "label": f"Skill: {skill.name}",
                    "color": "#10b981",
                    "title": skill.description
                })
                edges.append({
                    "from": f"skill_{skill.name}",
                    "to": "schema_Movie",
                    "label": "OPERATES_ON"
                })

        return {"nodes": nodes, "edges": edges, "mode": "metadata"}

    with database.session(database=DATABASE) as session:
        records = session.execute_read(
            lambda tx: list(tx.run(
                """
                MATCH (m:Movie)
                OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
                OPTIONAL MATCH (m)-[:FEATURES]->(p:Person)
                OPTIONAL MATCH (m)-[:AVAILABLE_ON]->(plat:Platform)
                RETURN m.id AS m_id, m.title AS title, m.year AS year,
                       collect(DISTINCT g.name)[0..2] AS genres,
                       collect(DISTINCT p.name)[0..2] AS actors,
                       plat.name AS platform
                LIMIT 35
                """
            ))
        )

    nodes_dict = {}
    edges_list = []

    for r in records:
        m_id = r["m_id"]
        title = f"{r['title']} ({r['year'] or ''})"
        nodes_dict[m_id] = {"id": m_id, "label": title, "color": "#8b5cf6", "group": "Movie"}

        for g_name in (r["genres"] or []):
            g_id = f"genre_{g_name.lower()}"
            if g_id not in nodes_dict:
                nodes_dict[g_id] = {"id": g_id, "label": g_name, "color": "#10b981", "group": "Genre"}
            edges_list.append({"from": m_id, "to": g_id, "label": "HAS_GENRE"})

        for a_name in (r["actors"] or []):
            a_id = f"actor_{a_name.lower().replace(' ', '_')}"
            if a_id not in nodes_dict:
                nodes_dict[a_id] = {"id": a_id, "label": a_name, "color": "#f59e0b", "group": "Person"}
            edges_list.append({"from": m_id, "to": a_id, "label": "FEATURES"})

        plat = r["platform"]
        if plat:
            plat_id = f"plat_{plat.lower().replace(' ', '_')}"
            if plat_id not in nodes_dict:
                nodes_dict[plat_id] = {"id": plat_id, "label": plat, "color": "#ec4899", "group": "Platform"}
            edges_list.append({"from": m_id, "to": plat_id, "label": "AVAILABLE_ON"})

    return {
        "nodes": list(nodes_dict.values()),
        "edges": edges_list,
        "mode": "catalog"
    }


# ==========================================
# MCP PROTOCOL & CHAT ENDPOINTS
# ==========================================

@app.get("/api/mcp/schema", summary="Get Neo4j MCP Graph Schema", tags=["MCP Protocol"])
def get_mcp_schema() -> Dict[str, Any]:
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP Client not available.")
    return mcp_client.get_schema()


@app.post("/api/mcp/query", summary="Execute MCP Cypher Query", tags=["MCP Protocol"])
def execute_mcp_query(req: MCPQueryRequest) -> Dict[str, Any]:
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP Client not available.")
    if req.read_only:
        results = mcp_client.read_cypher(req.query, req.parameters)
        return {"results": results, "count": len(results)}
    else:
        return mcp_client.write_cypher(req.query, req.parameters)


@app.post("/api/import", summary="Re-Sync Catalog & Graph RAG Index", tags=["Catalog Operations"])
def refresh_catalog() -> Dict[str, Any]:
    database = require_driver()
    import_catalog(database, force=True)
    if coordinator_agent:
        coordinator_agent.graph_rag_engine.initialize_vector_index()
    return catalog_overview(database)


@app.post("/api/chat", summary="Multi-Agent Movie Recommendation Endpoint", tags=["Recommender Agent"])
def chat(request: QuestionRequest) -> Dict[str, Any]:
    app_logger.info(f"Received chat question: '{request.question}' with context: '{request.watch_context}'")
    database = require_driver()
    import_catalog(database)
    genres = catalog_genres(database)
    history = recent_recommendations(database)

    # 1. Extract query filters
    filters, _ = extract_filters(request.question, genres, history)
    filters["limit"] = 5  # Recommends 5 movies as per requirement

    # 2. Invoke Multi-Agent Coordinator
    agent_response = coordinator_agent.process_query(
        question=request.question,
        filters=filters,
        watch_context=request.watch_context or "solo"
    )

    # 3. Save recommendation turn if successful
    if agent_response.get("status") == "SUCCESS":
        save_recommendation_turn(
            database=database,
            question=request.question,
            answer=agent_response["reply"],
            filters=filters,
            movies=agent_response["movies"]
        )

    return {
        "reply": agent_response["reply"],
        "status": agent_response["status"],
        "filters": filters,
        "movies": agent_response.get("movies", []),
        "guardrail": agent_response.get("guardrail"),
        "streaming": agent_response.get("streaming"),
        "watch_plan": agent_response.get("watch_plan"),
        "agent_contributions": agent_response.get("agent_contributions", []),
        "history": recent_recommendations(database),
        "agent_mode": "multi_agent_system"
    }
