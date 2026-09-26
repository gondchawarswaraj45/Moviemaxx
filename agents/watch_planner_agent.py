import re
from typing import Any, Dict, List
from .base_agent import BaseAgent
from metadata.catalog_metadata import WATCH_CONTEXT_TAXONOMY

class WatchPlannerAgent(BaseAgent):
    """
    Sub-Agent 4: Social Watch Context & Viewing Experience Planner Agent.
    Tailors recommendations and viewing plans based on who the user is watching with
    (Friend, Family, Solo, Life Partner / Date Night).
    """
    def __init__(self):
        super().__init__(
            name="WatchPlannerAgent",
            role="Social Watch Experience & Vibe Planner"
        )

    def detect_watch_context(self, question: str, explicit_context: str = "") -> str:
        text = f"{question} {explicit_context}".lower()

        if any(w in text for w in ["family", "kids", "parents", "children", "relatives", "mom", "dad"]):
            return "family"
        elif any(w in text for w in ["partner", "wife", "husband", "date", "girlfriend", "boyfriend", "romantic", "couple", "life partner"]):
            return "life partner"
        elif any(w in text for w in ["friend", "friends", "buddies", "pals", "group", "bros", "chums"]):
            return "friend"
        else:
            return "solo"

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        question = input_data.get("question", "")
        explicit_context = input_data.get("watch_context", "")
        movies: List[Dict[str, Any]] = input_data.get("movies", [])

        context_key = self.detect_watch_context(question, explicit_context)
        context_meta = WATCH_CONTEXT_TAXONOMY.get(context_key, WATCH_CONTEXT_TAXONOMY["solo"])

        # Tailor specific advice for recommended movies based on watch context
        tailored_movie_notes = []
        for movie in movies:
            title = movie.get("title", "Untitled")
            certificate = movie.get("certificate", "UA")
            rating = movie.get("rating", 7.0)
            genres = movie.get("genres", [])

            if context_key == "family":
                suitability = "Great for Family Viewing! Wholesome entertainment." if certificate in ["U", "UA"] else "Parental Guidance Advised."
            elif context_key == "life partner":
                suitability = "Perfect Date Night Pick! High emotional engagement." if any(g in ["Romance", "Comedy", "Drama"] for g in genres) else "Good engaging story for couples."
            elif context_key == "friend":
                suitability = "Awesome Friends Hangout Pick! High energy and entertaining."
            else:
                suitability = "Ideal Solo Watch! Deep immersive cinematic experience."

            tailored_movie_notes.append({
                "movie_title": title,
                "context_suitability": suitability,
                "certificate": certificate
            })

        return {
            "agent": self.name,
            "detected_context": context_key,
            "context_label": context_meta["label"],
            "context_description": context_meta["description"],
            "vibe_tips": context_meta["vibe_tips"],
            "movie_context_notes": tailored_movie_notes
        }
