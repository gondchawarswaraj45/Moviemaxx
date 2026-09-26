# Moviemaxx

Moviemaxx is a conversational Bollywood movie recommender backed by Neo4j. It imports the supplied 1,000-row CSV into a connected movie graph, searches that graph for candidates, and uses Groq to turn natural-language questions into safe filters and grounded recommendations.

## How It Works

1. The first catalog request imports the CSV in batches. **Sync CSV catalog** can re-run the idempotent import.
2. Neo4j represents `Movie`, `Genre`, `Person`, and `Platform` nodes. Relationships connect movies to genres, cast, directors, writers, producers, and streaming platforms.
3. Groq converts questions into validated filters such as genre, actor, director, year, rating, and platform. The application builds fixed Cypher queries from those filters; it never executes model-generated Cypher.
4. Moviemaxx formats replies directly from graph results (year, rating, genre, and platform), avoiding invented film or availability details. If Groq is unavailable or not configured, local genre/year/rating matching still returns results.
5. Questions, filters, answers, and recommended movie relationships are saved as `Viewer → RecommendationTurn → Movie`. Follow-ups such as “show me more like those” reuse the stored filters.

## Configure

Set these values in `.env` (the application does not print them):

```dotenv
NEO4J_URI="neo4j+s://your-instance.databases.neo4j.io"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="your-neo4j-password"
NEO4J_DATABASE="neo4j"
GROQ_API_KEY="your-groq-api-key"
GROQ_MODEL="openai/gpt-oss-20b"
```

The Neo4j account must have permission to create constraints and write nodes and relationships. Groq is optional; without `GROQ_API_KEY`, the app uses local genre/year/rating matching and still queries Neo4j. At startup of the first chat request, Moviemaxx checks the configured model against the models available to the key and falls back to an available Groq OSS model when needed.

## Run

From this project folder, install dependencies into the selected Python environment and launch the app:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`. The first load imports the CSV. Use **Sync CSV catalog** to re-import it later.

Run the focused tests with:

```powershell
python -m unittest discover -s tests -v
```

This is a single-viewer prototype. Search history is shared by this local demo viewer and stored in the configured Neo4j database.
