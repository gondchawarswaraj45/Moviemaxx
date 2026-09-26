from dataclasses import dataclass
from typing import Any, Dict, List

@dataclass
class TextChunk:
    chunk_id: str
    movie_id: str
    text: str
    chunk_type: str  # OVERVIEW, CAST_ROLE, THEME_VERDICT
    metadata: Dict[str, Any]

class RelativeChunker:
    """
    Relative Chunking Engine for Moviemaxx Graph RAG.
    Segments movie data into relative semantic chunks with structured metadata.
    """
    def chunk_movie_record(self, movie: Dict[str, Any]) -> List[TextChunk]:
        movie_id = str(movie.get("id") or movie.get("movie_id") or "")
        props = movie.get("properties") or movie
        title = props.get("title") or props.get("movie_name") or "Unknown Movie"
        year = props.get("year") or props.get("release_year") or ""
        genres = ", ".join(props.get("genres") or []) if isinstance(props.get("genres"), list) else str(props.get("genres") or "")
        rating = props.get("rating") or props.get("imdb_rating") or "N/A"
        platform = props.get("platform") or props.get("ott_platform") or "N/A"
        theme = props.get("theme") or ""
        verdict = props.get("verdict") or ""

        # Extract cast & directors
        cast_list = movie.get("cast") or []
        cast_names = [c["name"] if isinstance(c, dict) else str(c) for c in cast_list] if isinstance(cast_list, list) else []
        director = props.get("director") or ""
        
        chunks: List[TextChunk] = []

        # 1. Overview Chunk
        overview_text = (
            f"Movie: {title} ({year}). Genres: {genres}. "
            f"IMDb Rating: {rating}/10. Streaming Platform: {platform}. "
            f"Theme: {theme}."
        )
        chunks.append(TextChunk(
            chunk_id=f"{movie_id}_overview",
            movie_id=movie_id,
            text=overview_text,
            chunk_type="OVERVIEW",
            metadata={
                "movie_id": movie_id,
                "title": title,
                "year": year,
                "genres": props.get("genres") or [],
                "rating": rating,
                "platform": platform,
                "director": director
            }
        ))

        # 2. Cast & Role Chunk
        cast_text = (
            f"Movie: {title} ({year}). Directed by {director}. "
            f"Starring: {', '.join(cast_names) if cast_names else 'N/A'}. "
            f"Key team: {director} (Director)."
        )
        chunks.append(TextChunk(
            chunk_id=f"{movie_id}_cast",
            movie_id=movie_id,
            text=cast_text,
            chunk_type="CAST_ROLE",
            metadata={
                "movie_id": movie_id,
                "title": title,
                "cast": cast_names,
                "director": director
            }
        ))

        # 3. Theme & Verdict Chunk
        theme_text = (
            f"Movie: {title} ({year}). Theme & Mood: {theme}. "
            f"Box office verdict: {verdict}. Streaming on: {platform}."
        )
        chunks.append(TextChunk(
            chunk_id=f"{movie_id}_theme",
            movie_id=movie_id,
            text=theme_text,
            chunk_type="THEME_VERDICT",
            metadata={
                "movie_id": movie_id,
                "title": title,
                "theme": theme,
                "verdict": verdict,
                "platform": platform
            }
        ))

        return chunks

    def chunk_catalog(self, movies: List[Dict[str, Any]]) -> List[TextChunk]:
        all_chunks: List[TextChunk] = []
        for movie in movies:
            all_chunks.extend(self.chunk_movie_record(movie))
        return all_chunks
