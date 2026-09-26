import json
import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq
from neo4j import Driver, GraphDatabase
from neo4j.exceptions import Neo4jError
from pydantic import BaseModel, Field

from movie_graph import (
    DATABASE,
    import_catalog,
    recent_recommendations,
    save_recommendation_turn,
    search_movies,
)


load_dotenv()
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
driver: Driver | None = None

if NEO4J_URI and NEO4J_USERNAME and NEO4J_PASSWORD:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    if driver:
        driver.close()


app = FastAPI(title="Moviemaxx Movie Graph", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.exception_handler(Neo4jError)
async def handle_database_error(_, __) -> JSONResponse:
    logger.exception("Neo4j request failed")
    return JSONResponse(
        status_code=503,
        content={"detail": "Neo4j request failed. Check the configured instance and write permissions."},
    )


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1500)


def require_driver() -> Driver:
    if driver is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j is not configured. Add NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD to .env.",
        )
    return driver


def catalog_genres(database: Driver) -> list[str]:
    with database.session(database=DATABASE) as session:
        records = session.execute_read(
            lambda tx: list(tx.run("MATCH (genre:Genre) RETURN genre.name AS name ORDER BY name"))
        )
    return [record["name"] for record in records]


def catalog_overview(database: Driver) -> dict[str, Any]:
    import_catalog(database)
    with database.session(database=DATABASE) as session:
        record = session.execute_read(
            lambda tx: tx.run("MATCH (movie:Movie) RETURN count(movie) AS count").single()
        )
    genres = catalog_genres(database)
    featured = search_movies(database, {"limit": 6})
    history = recent_recommendations(database)
    return {
        "movie_count": record["count"] if record else 0,
        "genres": genres,
        "featured": featured,
        "history": history,
        "agent_mode": "groq" if groq_client else "local",
    }


def _safe_text(value: Any, maximum: int = 80) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned[:maximum] or None


_resolved_groq_model: str | None = None


def resolve_groq_model() -> str | None:
    global _resolved_groq_model
    if groq_client is None:
        return None
    if _resolved_groq_model:
        return _resolved_groq_model
    try:
        available = {model.id for model in groq_client.models.list().data}
    except Exception as error:
        logger.warning("Unable to list Groq models (%s)", type(error).__name__)
        return None

    _resolved_groq_model = next(
        (model for model in (GROQ_MODEL, "openai/gpt-oss-20b", "openai/gpt-oss-120b") if model in available),
        None,
    )
    if _resolved_groq_model and _resolved_groq_model != GROQ_MODEL:
        logger.warning("Configured Groq model unavailable; using %s", _resolved_groq_model)
    return _resolved_groq_model


def _normalise_filters(raw: dict[str, Any], genres: list[str]) -> dict[str, Any]:
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
        limit = int(raw.get("limit", 6))
    except (TypeError, ValueError):
        limit = 6

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


def fallback_filters(question: str, genres: list[str], history: list[dict[str, Any]]) -> dict[str, Any]:
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
        "limit": 6,
    }
    if history and any(phrase in lowered for phrase in ("more like", "similar to those", "another like", "more like that")):
        previous = history[0].get("filters") or {}
        filters.update({key: previous.get(key) for key in filters if key in previous})
    return _normalise_filters(filters, genres)


def apply_follow_up_memory(
    question: str,
    filters: dict[str, Any],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
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


def extract_filters(question: str, genres: list[str], history: list[dict[str, Any]]) -> tuple[dict[str, Any], bool]:
    model = resolve_groq_model()
    if model is None:
        return fallback_filters(question, genres, history), False

    recent_context = [
        {
            "question": turn.get("question"),
            "filters": turn.get("filters"),
            "movies": [movie.get("title") for movie in turn.get("movies", []) if movie],
        }
        for turn in history[:4]
    ]
    try:
        response = groq_client.chat.completions.create(
            model=model,
            temperature=0.1,
            max_tokens=1000,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Convert a movie request into JSON search filters for a Neo4j catalog. "
                        "Return only these keys: genres (array using exact available genre names), "
                        "actor, director, year (integer or null), minimum_rating (number or null), "
                        "platform, title, theme, limit (integer 1-12). Use null/empty values when "
                        "not requested. For a follow-up such as 'more like those', reuse the previous "
                        "filters. Never invent genres outside the available list."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"question": question, "available_genres": genres, "recent_graph_memory": recent_context}
                    ),
                },
            ],
        )
        content = response.choices[0].message.content or "{}"
        return _normalise_filters(json.loads(content), genres), True
    except Exception:
        logger.exception("Groq filter extraction failed; using local filter matching")
        return fallback_filters(question, genres, history), False


def requested_result_limit(question: str, default_limit: int) -> int:
    singular_request = re.search(
        r"\b(?:a|an|one|single|any)\s+(?:[a-z0-9]+(?:[-'][a-z0-9]+)*\s+){0,3}(?:movie|film)\b",
        question,
        re.IGNORECASE,
    )
    if singular_request:
        return 1
    return max(1, min(default_limit, 12))


def local_answer(question: str, movies: list[dict[str, Any]], filters: dict[str, Any]) -> str:
    if not movies:
        return "I couldn't find a match in the movie graph. Try a genre, actor, director, year, or streaming platform."
    titles = ", ".join(
        f"{movie.get('title', 'Untitled')} ({movie.get('year') or 'year unknown'}, "
        f"{movie['rating'] if movie.get('rating') is not None else 'unrated'})"
        for movie in movies[:5]
    )
    return f"Based on the movie graph, these are the closest matches for your request: {titles}. Want more like one of these?"


def compose_answer(
    question: str,
    filters: dict[str, Any],
    movies: list[dict[str, Any]],
    history: list[dict[str, Any]],
) -> tuple[str, bool]:
    if not movies:
        if filters.get("exclude_ids"):
            return "Those were the last matches for your saved filters. Try another genre, performer, or year.", False
        if filters.get("genres"):
            return f"I couldn't confidently verify a {', '.join(filters['genres'])} movie in this catalog.", False
        return local_answer(question, movies, filters), False

    qualifiers = []
    if filters.get("genres"):
        qualifiers.append("genre: " + ", ".join(filters["genres"]))
    if filters.get("year"):
        qualifiers.append(f"year: {filters['year']}")
    if filters.get("minimum_rating") is not None:
        qualifiers.append(f"catalog rating: {filters['minimum_rating']}+")
    if filters.get("actor"):
        qualifiers.append("cast: " + filters["actor"])
    if filters.get("director"):
        qualifiers.append("director: " + filters["director"])
    if filters.get("platform"):
        qualifiers.append("platform: " + filters["platform"])

    is_follow_up = bool(filters.get("exclude_ids"))
    if is_follow_up:
        seen_noun = "film" if len(filters["exclude_ids"]) == 1 else "films"
        intro = f"Using your previous graph search, I skipped the {seen_noun} already shown."
    else:
        result_phrase = "this film" if len(movies) == 1 else "these films"
        intro = f"I found {result_phrase} in the Neo4j catalog"
    if qualifiers:
        intro += " (" + "; ".join(qualifiers) + ")"
    intro += "."
    details = []
    for movie in movies[:filters.get("limit", 5)]:
        fields = [str(movie.get("year") or "year unknown")]
        if movie.get("rating") is not None:
            fields.append(f"catalog rating {movie['rating']}")
        if movie.get("genres"):
            fields.append("genres: " + ", ".join(movie["genres"]))
        if movie.get("platform"):
            fields.append("streaming: " + movie["platform"])
        details.append(f"- {movie.get('title', 'Untitled')} · " + " · ".join(fields))
    follow_up = "Want another recommendation?" if len(movies) == 1 else "Want to narrow these by another filter?"
    return intro + "\n" + "\n".join(details) + "\n" + follow_up, False


def graph_genres(database: Driver) -> list[str]:
    import_catalog(database)
    return catalog_genres(database)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "neo4j_configured": driver is not None,
        "groq_configured": groq_client is not None,
        "agent_mode": "groq" if groq_client else "local",
    }


@app.get("/api/overview")
def overview() -> dict[str, Any]:
    database = require_driver()
    return catalog_overview(database)


@app.post("/api/import")
def refresh_catalog() -> dict[str, Any]:
    database = require_driver()
    import_catalog(database, force=True)
    return catalog_overview(database)


@app.post("/api/chat")
def chat(request: QuestionRequest) -> dict[str, Any]:
    database = require_driver()
    import_catalog(database)
    genres = catalog_genres(database)
    history = recent_recommendations(database)
    filters, filters_used_groq = extract_filters(request.question, genres, history)
    filters = apply_follow_up_memory(request.question, filters, history)
    filters["limit"] = requested_result_limit(request.question, filters.get("limit", 6))
    movies = search_movies(database, filters)
    movies = movies[:filters["limit"]]
    answer, answer_used_groq = compose_answer(request.question, filters, movies, history)
    save_recommendation_turn(database, request.question, answer, filters, movies)
    return {
        "reply": answer,
        "filters": filters,
        "movies": movies,
        "history": recent_recommendations(database),
        "agent_mode": "groq" if filters_used_groq or answer_used_groq else "local",
    }
