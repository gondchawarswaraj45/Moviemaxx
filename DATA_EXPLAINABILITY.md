# Moviemaxx Data Explainability & Provenance

Data explainability is a core pillar of Moviemaxx. Unlike black-box recommendation models that invent details or hallucinate movie availability, Moviemaxx grounds every recommendation in deterministic graph relationships and vector embeddings.

---

## 1. Knowledge Graph Schema & Node Lineage

Moviemaxx models the Bollywood movie ecosystem as an interconnected graph in Neo4j:

```
(Viewer:Viewer) ──[:ASKED]──> (Turn:RecommendationTurn) ──[:RECOMMENDED {rank}]──> (Movie:Movie)
                                                                                  │
     ┌───────────────────────────┬───────────────────────────┬────────────────────┘
     │                           │                           │
     ▼                           ▼                           ▼
(Genre:Genre)              (Person:Person)          (Platform:Platform)
 [:HAS_GENRE]             [:FEATURES]                [:AVAILABLE_ON]
                          [:DIRECTED_BY]
```

### Node Attributes & Provenance

| Node Label | Key Properties | Data Provenance |
| :--- | :--- | :--- |
| `Movie` | `id`, `title`, `year`, `rating`, `runtime`, `verdict`, `theme`, `platform` | Normalized graph dataset (3,022 Bollywood records) |
| `Genre` | `name` | Canonical genre taxonomy (Action, Romance, Comedy, Thriller, Sci-Fi, etc.) |
| `Person` | `key`, `name` | Actor, Director, Writer, Producer entities |
| `Platform` | `name` | OTT Streaming services (Netflix, Prime Video, JioCinema, ZEE5, SonyLIV, Sun NXT) |
| `Viewer` | `id` | Session viewer entity |
| `RecommendationTurn` | `id`, `question`, `answer`, `filtersJson`, `createdAt` | Conversational graph memory turns |

---

## 2. Graph RAG Hybrid Scoring Formula

Every recommended movie receives an explicit, explainable **Hybrid Match Score**:

$$\text{Hybrid Score} = (0.5 \times \text{Graph Rank Score}) + (0.5 \times \text{Cohere Vector Similarity})$$

Where:
- **Graph Rank Score**: Derived from exact Cypher relationship traversal (`HAS_GENRE`, `FEATURES`, `AVAILABLE_ON`) weighted by IMDb catalog rating.
- **Cohere Vector Similarity**: Cosine similarity between the query embedding and the movie's relative text chunk embeddings (`embed-english-v3.0`).

### Transparency in UI
Every movie card displays:
- **IMDb Rating**: Unaltered catalog rating.
- **Primary Genres**: Exact graph genre node connections.
- **Where to Watch**: Exact platform node connection.
- **Graph RAG Match Percentage**: Quantitative score ($0\text{--}100\%$).

---

## 3. Conversational Memory Traceability

When follow-up questions are asked (e.g. *"Show me more like those"*):
1. Previous turn filters (`genres`, `minimum_rating`, `actor`, `platform`) are loaded from `RecommendationTurn` nodes.
2. Previously shown movie IDs are appended to `exclude_ids`.
3. The new Cypher query excludes already seen films while preserving search intent.
