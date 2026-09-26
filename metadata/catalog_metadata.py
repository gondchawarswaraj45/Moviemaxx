from typing import Any, Dict

CATALOG_METADATA: Dict[str, Any] = {
    "system": "Moviemaxx Knowledge Graph",
    "version": "2.0",
    "nodes": {
        "Movie": {
            "description": "Bollywood film entity",
            "properties": {
                "id": "Unique string identifier (e.g. BW00001)",
                "title": "Film title string",
                "year": "Release year integer (e.g. 2010..2024)",
                "language": "Primary spoken language (Hindi, etc.)",
                "industry": "Film industry label (Bollywood)",
                "region": "Regional market label (India/North)",
                "certificate": "Censor rating (U, UA, A)",
                "rating": "IMDb rating float (0.0 to 10.0)",
                "criticRating": "Critic consensus rating float",
                "audienceRating": "Audience score float",
                "runtime": "Runtime in minutes integer",
                "verdict": "Box office performance (Blockbuster, Hit, Super Hit, Flop)",
                "theme": "Narrative motif or emotional tone",
                "platform": "Primary streaming provider (Netflix, Prime Video, JioCinema, SonyLIV, Zee5)",
                "worldwideCollection": "Box office revenue in Crore INR"
            }
        },
        "Genre": {
            "description": "Categorical movie style",
            "properties": {"name": "Genre name string (Action, Comedy, Drama, Thriller, Sci-Fi, Romance, etc.)"}
        },
        "Person": {
            "description": "Cast or crew member",
            "properties": {
                "key": "Normalized slug identifier (e.g. deepak-khan)",
                "name": "Full artist name"
            }
        },
        "Platform": {
            "description": "OTT Streaming service provider",
            "properties": {"name": "Platform name (Netflix, Prime Video, JioCinema, SonyLIV, Zee5)"}
        },
        "Viewer": {
            "description": "Application user entity",
            "properties": {"id": "Unique user session identifier"}
        },
        "RecommendationTurn": {
            "description": "Stored conversational recommendation memory turn",
            "properties": {
                "id": "Turn UUID",
                "question": "User prompt text",
                "answer": "Generated agent response",
                "filtersJson": "JSON representation of extracted query filters",
                "createdAt": "Timestamp string"
            }
        }
    },
    "relationships": [
        "(Movie)-[:HAS_GENRE]->(Genre)",
        "(Movie)-[:FEATURES]->(Person)",
        "(Movie)-[:DIRECTED_BY]->(Person)",
        "(Movie)-[:WRITTEN_BY]->(Person)",
        "(Movie)-[:PRODUCED_BY]->(Person)",
        "(Movie)-[:AVAILABLE_ON]->(Platform)",
        "(Viewer)-[:ASKED]->(RecommendationTurn)",
        "(RecommendationTurn)-[:RECOMMENDED {rank: int}]->(Movie)"
    ]
}

WATCH_CONTEXT_TAXONOMY: Dict[str, Any] = {
    "solo": {
        "label": "Solo Chill",
        "description": "Immersive, thought-provoking, dark thrillers, deep dramas, or intense cinema.",
        "preferred_genres": ["Drama", "Thriller", "Mystery", "Crime", "Sci-Fi"],
        "vibe_tips": "Grab headphones, dim lights, and enjoy uninterrupted cinematic storytelling."
    },
    "family": {
        "label": "Family Movie Night",
        "description": "Clean, wholesome, feel-good comedies, family dramas, sports, or historical epics.",
        "preferred_genres": ["Comedy", "Family", "Drama", "Sports", "Historical"],
        "censor_certificates": ["U", "UA"],
        "vibe_tips": "Prepare popcorn, gather around the main TV, suitable for all ages."
    },
    "friend": {
        "label": "Friends Hangout",
        "description": "High-energy, comedy, action blockbusters, fast-paced thrillers, horror.",
        "preferred_genres": ["Comedy", "Action", "Horror", "Adventure"],
        "vibe_tips": "High energy vibe with snacks and lively group commentary!"
    },
    "life partner": {
        "label": "Date Night / Life Partner",
        "description": "Romantic comedies, emotional romances, visually stunning cinema, or light drama.",
        "preferred_genres": ["Romance", "Comedy", "Musical", "Drama"],
        "vibe_tips": "Cozy ambiance, favorite drinks, romantic and engaging mood."
    }
}
