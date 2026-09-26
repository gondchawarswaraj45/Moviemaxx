from typing import Any, Dict, List
from .base_agent import BaseAgent

class StreamingAgent(BaseAgent):
    """
    Sub-Agent 3: OTT Streaming Platform & Where-To-Watch Navigation Agent.
    Resolves streaming availability, platform links, and access instructions.
    """
    def __init__(self):
        super().__init__(
            name="StreamingAgent",
            role="OTT Platform Navigation & Where-To-Watch Specialist"
        )

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        movies: List[Dict[str, Any]] = input_data.get("movies", [])
        platform_guides = []

        for movie in movies:
            title = movie.get("title", "Untitled")
            platform = movie.get("platform")
            year = movie.get("year", "")
            
            if platform and str(platform).strip() and str(platform).lower() != "none":
                guide = {
                    "movie_title": title,
                    "platform": platform,
                    "status": "Available Streaming",
                    "badge": f"🍿 Available on {platform}",
                    "navigation_note": f"Search '{title}' on {platform} app or website."
                }
            else:
                guide = {
                    "movie_title": title,
                    "platform": "Theatrical / Digital Rental",
                    "status": "Check VOD",
                    "badge": "🎟️ Available via Digital Purchase/Rental or Satellite TV",
                    "navigation_note": f"'{title}' ({year}) is available on YouTube Movies / Google Play or TV broadcast."
                }
            platform_guides.append(guide)

        return {
            "agent": self.name,
            "platform_guides": platform_guides
        }
