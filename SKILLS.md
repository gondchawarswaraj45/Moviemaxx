# Moviemaxx Agent Skills Index

Moviemaxx exposes specialized executable agent skills for graph traversal, semantic vector retrieval, streaming navigation, social watch planning, and harness engineering safety audit.

---

## 1. Skill Index & Descriptions

| Skill Name | Location | Description |
| :--- | :--- | :--- |
| `movie-graph-search` | `skills/movie-graph-search/SKILL.md` | Executes Cypher graph traversal queries over Neo4j to find movies by genre, cast, director, rating, year, or platform. |
| `cohere-vector-search` | `skills/cohere-vector-search/SKILL.md` | Computes semantic vector similarity over Cohere embeddings (`embed-english-v3.0`) for relative text dataset chunks. |
| `streaming-platform-nav` | `skills/streaming-platform-nav/SKILL.md` | Resolves OTT platform streaming availability (Netflix, Prime Video, JioCinema, ZEE5, SonyLIV, Sun NXT) and navigation guides. |
| `watch-context-planner` | `skills/watch-context-planner/SKILL.md` | Tailors recommendations and viewing plans based on social watch partners (`solo`, `family`, `friend`, `life partner`). |
| `p2-guardrail-audit` | `skills/p2-guardrail-audit/SKILL.md` | Audits user prompts for prompt injection, system prompt leaks, DAN mode, Cypher injection, and unsafe commands. |

---

## 2. Accessing Skills via API

Skills metadata can be retrieved dynamically via FastAPI endpoint:

```http
GET /api/metadata/skills
```

Sample JSON response:
```json
{
  "catalog_metadata": { ... },
  "watch_contexts": { ... },
  "agent_skills": [
    {
      "name": "SafetyP2GuardrailSkill",
      "description": "Evaluates user prompts for prompt injection, jailbreaks, and unsafe commands."
    },
    {
      "name": "MovieGraphSearchSkill",
      "description": "Searches Neo4j graph nodes and relationships using structured filters."
    },
    {
      "name": "CohereVectorSearchSkill",
      "description": "Computes semantic vector similarity over Cohere embeddings for query matching."
    },
    {
      "name": "StreamingPlatformSkill",
      "description": "Resolves streaming availability, platform links, and subscription details."
    },
    {
      "name": "WatchContextPlannerSkill",
      "description": "Plans viewing experience based on watch partners (solo, family, friends, life partner)."
    }
  ]
}
```
