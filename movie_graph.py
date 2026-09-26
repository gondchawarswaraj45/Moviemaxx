import csv
import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import Driver


DATASET_PATH = Path(__file__).resolve().parent / "data" / "bollywood_famous_2010_latest_graph_ready.csv"
load_dotenv()
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
BATCH_SIZE = 150
_catalog_loaded = False
GENRE_OVERRIDES = {
    "krrish 3": ["Action", "Adventure", "Sci-Fi"],
    "pk": ["Comedy", "Drama", "Sci-Fi"],
    "teri baaton mein aisa uljha jiya": ["Comedy", "Romance", "Sci-Fi"],
}

CONSTRAINTS = (
    "CREATE CONSTRAINT movie_id IF NOT EXISTS FOR (node:Movie) REQUIRE node.id IS UNIQUE",
    "CREATE CONSTRAINT genre_name IF NOT EXISTS FOR (node:Genre) REQUIRE node.name IS UNIQUE",
    "CREATE CONSTRAINT person_key IF NOT EXISTS FOR (node:Person) REQUIRE node.key IS UNIQUE",
    "CREATE CONSTRAINT platform_name IF NOT EXISTS FOR (node:Platform) REQUIRE node.name IS UNIQUE",
)

MOVIE_QUERY = """
UNWIND $rows AS row
MERGE (movie:Movie {id: row.id})
SET movie += row.properties
"""
GENRE_QUERY = """
UNWIND $rows AS row
MATCH (movie:Movie {id: row.id})
OPTIONAL MATCH (movie)-[old:HAS_GENRE]->()
WITH movie, row, collect(old) AS old_genres
FOREACH (relation IN old_genres | DELETE relation)
WITH movie, row
UNWIND row.genres AS genre_name
MERGE (genre:Genre {name: genre_name})
MERGE (movie)-[:HAS_GENRE]->(genre)
"""
CAST_QUERY = """
UNWIND $rows AS row
MATCH (movie:Movie {id: row.id})
UNWIND row.cast AS person_row
MERGE (person:Person {key: person_row.key})
ON CREATE SET person.name = person_row.name
MERGE (movie)-[:FEATURES]->(person)
"""
DIRECTOR_QUERY = """
UNWIND $rows AS row
MATCH (movie:Movie {id: row.id})
UNWIND row.roles AS role_row
WITH movie, role_row WHERE role_row.role = 'director'
MERGE (person:Person {key: role_row.key})
ON CREATE SET person.name = role_row.name
MERGE (movie)-[:DIRECTED_BY]->(person)
"""
WRITER_QUERY = """
UNWIND $rows AS row
MATCH (movie:Movie {id: row.id})
UNWIND row.roles AS role_row
WITH movie, role_row WHERE role_row.role = 'writer'
MERGE (person:Person {key: role_row.key})
ON CREATE SET person.name = role_row.name
MERGE (movie)-[:WRITTEN_BY]->(person)
"""
PRODUCER_QUERY = """
UNWIND $rows AS row
MATCH (movie:Movie {id: row.id})
UNWIND row.roles AS role_row
WITH movie, role_row WHERE role_row.role = 'producer'
MERGE (person:Person {key: role_row.key})
ON CREATE SET person.name = role_row.name
MERGE (movie)-[:PRODUCED_BY]->(person)
"""
PLATFORM_QUERY = """
UNWIND $rows AS row
MATCH (movie:Movie {id: row.id})
OPTIONAL MATCH (movie)-[old:AVAILABLE_ON]->()
WITH movie, row, collect(old) AS old_platforms
FOREACH (relation IN old_platforms | DELETE relation)
WITH movie, row WHERE row.platform IS NOT NULL
MERGE (platform:Platform {name: row.platform})
MERGE (movie)-[:AVAILABLE_ON]->(platform)
"""


def _text(row: dict[str, str], key: str) -> str | None:
    value = (row.get(key) or "").strip()
    return value or None


def _number(row: dict[str, str], key: str, integer: bool = False) -> int | float | None:
    value = _text(row, key)
    if value is None:
        return None
    try:
        number = float(value.replace(",", ""))
    except ValueError:
        return None
    return int(number) if integer else number


def _split_names(value: str | None) -> list[str]:
    if not value:
        return []
    names: dict[str, str] = {}
    for part in value.split("|"):
        name = part.strip()
        if name:
            names.setdefault(name.casefold(), name)
    return list(names.values())


def _person_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")


def normalize_movie_row(row: dict[str, str]) -> dict[str, Any] | None:
    movie_id = _text(row, "movie_id")
    title = _text(row, "movie_name")
    if not movie_id or not title:
        return None

    genres = _split_names("|".join(filter(None, (_text(row, "genre"), _text(row, "secondary_genres")))))
    canonical_title = re.sub(r"\s+-\s+Extended Graph Record \d+$", "", title, flags=re.IGNORECASE).strip().casefold()
    genres = GENRE_OVERRIDES.get(
        canonical_title,
        [genre for genre in genres if genre.casefold() != "sci-fi"],
    )
    cast_names = _split_names(_text(row, "starred_names"))
    roles = [
        {"role": role, "name": name, "key": _person_key(name)}
        for role, key in (("director", "director"), ("writer", "writer"), ("producer", "producer"))
        if (name := _text(row, key))
    ]
    properties = {
        "title": title,
        "year": _number(row, "release_year", integer=True),
        "releaseDate": _text(row, "release_date"),
        "language": _text(row, "language"),
        "industry": _text(row, "industry"),
        "region": _text(row, "region"),
        "certificate": _text(row, "certificate"),
        "rating": _number(row, "imdb_rating"),
        "criticRating": _number(row, "critic_rating"),
        "audienceRating": _number(row, "audience_rating"),
        "runtime": _number(row, "runtime_minutes", integer=True),
        "verdict": _text(row, "verdict"),
        "theme": _text(row, "theme"),
        "franchise": _text(row, "franchise"),
        "platform": _text(row, "ott_platform"),
        "worldwideCollection": _number(row, "worldwide_collection_crore_inr"),
        "genres": genres,
    }
    if canonical_title in GENRE_OVERRIDES:
        properties["platform"] = None
    normalized_properties = {key: value for key, value in properties.items() if value is not None}
    if canonical_title in GENRE_OVERRIDES:
        normalized_properties["platform"] = None
    return {
        "id": movie_id,
        "properties": normalized_properties,
        "genres": genres,
        "cast": [{"name": name, "key": _person_key(name)} for name in cast_names],
        "roles": roles,
        "platform": properties["platform"],
    }


def load_movie_rows(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        rows = [normalize_movie_row(row) for row in reader]
    return [row for row in rows if row is not None]


def _write_batch(tx: Any, rows: list[dict[str, Any]]) -> None:
    for query in (
        MOVIE_QUERY,
        GENRE_QUERY,
        CAST_QUERY,
        DIRECTOR_QUERY,
        WRITER_QUERY,
        PRODUCER_QUERY,
        PLATFORM_QUERY,
    ):
        tx.run(query, rows=rows).consume()


def import_catalog(database: Driver, force: bool = False) -> int:
    global _catalog_loaded
    if _catalog_loaded and not force:
        return len(load_movie_rows())

    rows = load_movie_rows()
    with database.session(database=DATABASE) as session:
        for constraint in CONSTRAINTS:
            session.run(constraint).consume()
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start : start + BATCH_SIZE]
            session.execute_write(lambda tx: _write_batch(tx, batch))
    _catalog_loaded = True
    return len(rows)


def search_movies(database: Driver, filters: dict[str, Any]) -> list[dict[str, Any]]:
    query = """
    MATCH (movie:Movie)
    OPTIONAL MATCH (movie)-[:HAS_GENRE]->(genre:Genre)
    OPTIONAL MATCH (movie)-[:FEATURES]->(actor:Person)
    OPTIONAL MATCH (movie)-[:DIRECTED_BY]->(director:Person)
    WITH movie,
         collect(DISTINCT genre.name) AS genres,
         collect(DISTINCT actor.name) AS cast,
         collect(DISTINCT director.name)[0] AS director
    WHERE (size($genres) = 0 OR any(item IN genres WHERE item IN $genres))
      AND ($actor IS NULL OR any(name IN cast WHERE toLower(name) CONTAINS toLower($actor)))
      AND ($director IS NULL OR (director IS NOT NULL AND toLower(director) CONTAINS toLower($director)))
      AND ($year IS NULL OR movie.year = $year)
      AND ($minimum_rating IS NULL OR movie.rating >= $minimum_rating)
      AND ($platform IS NULL OR toLower(coalesce(movie.platform, '')) CONTAINS toLower($platform))
      AND ($title IS NULL OR toLower(movie.title) CONTAINS toLower($title))
    AND ($theme IS NULL OR toLower(coalesce(movie.theme, '')) CONTAINS toLower($theme))
    AND (size($exclude_ids) = 0 OR NOT movie.id IN $exclude_ids)
            AND NOT movie.title CONTAINS 'Extended Graph Record'
    RETURN movie.id AS id, movie.title AS title, movie.year AS year,
           movie.language AS language, movie.industry AS industry,
           movie.rating AS rating, movie.runtime AS runtime,
           movie.verdict AS verdict, movie.theme AS theme,
           movie.platform AS platform, movie.worldwideCollection AS worldwideCollection,
           genres, cast[0..4] AS cast, director
    ORDER BY coalesce(movie.rating, 0) DESC, movie.title ASC
    LIMIT $limit
    """
    parameters = {
        "genres": filters.get("genres", []),
        "actor": filters.get("actor"),
        "director": filters.get("director"),
        "year": filters.get("year"),
        "minimum_rating": filters.get("minimum_rating"),
        "platform": filters.get("platform"),
        "title": filters.get("title"),
        "theme": filters.get("theme"),
        "exclude_ids": filters.get("exclude_ids", []),
        "limit": max(1, min(int(filters.get("limit", 6)), 200)),
    }
    with database.session(database=DATABASE) as session:
        records = session.execute_read(lambda tx: list(tx.run(query, **parameters)))
    return [dict(record) for record in records]


def save_recommendation_turn(
    database: Driver,
    question: str,
    answer: str,
    filters: dict[str, Any],
    movies: list[dict[str, Any]],
) -> None:
    query = """
    MERGE (viewer:Viewer {id: $viewer_id})
    CREATE (turn:RecommendationTurn {
        id: $turn_id,
        question: $question,
        answer: $answer,
        filtersJson: $filters_json,
        createdAt: datetime()
    })
    CREATE (viewer)-[:ASKED]->(turn)
    WITH turn
    UNWIND $recommendations AS recommendation
    MATCH (movie:Movie {id: recommendation.id})
    CREATE (turn)-[:RECOMMENDED {rank: recommendation.rank}]->(movie)
    """
    from uuid import uuid4

    with database.session(database=DATABASE) as session:
        session.execute_write(
            lambda tx: tx.run(
                query,
                viewer_id="moviemaxx-demo-viewer",
                turn_id=str(uuid4()),
                question=question,
                answer=answer,
                filters_json=json.dumps(json_safe_filters(filters)),
                recommendations=[
                    {"id": movie["id"], "rank": rank}
                    for rank, movie in enumerate(movies)
                ],
            ).consume()
        )


def json_safe_filters(filters: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in filters.items()
        if value is None or isinstance(value, (str, int, float, bool)) or isinstance(value, list)
    }


def recent_recommendations(database: Driver, limit: int = 6) -> list[dict[str, Any]]:
    query = """
    MATCH (:Viewer {id: $viewer_id})-[:ASKED]->(turn:RecommendationTurn)
    OPTIONAL MATCH (turn)-[recommendation:RECOMMENDED]->(movie:Movie)
    WITH turn, recommendation, movie
    ORDER BY recommendation.rank
    WITH turn, collect(movie {
        .id, .title, .year, .rating, .genres, .theme, .platform
    }) AS movies
    RETURN turn.question AS question, turn.answer AS answer,
           turn.filtersJson AS filtersJson, toString(turn.createdAt) AS createdAt, movies
    ORDER BY turn.createdAt DESC
    LIMIT $limit
    """
    with database.session(database=DATABASE) as session:
        records = session.execute_read(
            lambda tx: list(
                tx.run(query, viewer_id="moviemaxx-demo-viewer", limit=limit)
            )
        )
    history = [dict(record) for record in records]
    for turn in history:
        turn["filters"] = json.loads(turn.pop("filtersJson") or "{}")
    return history
