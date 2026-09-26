# Moviemaxx Operational Procedures

This document outlines operational workflows for setup, dataset ingestion, multi-agent execution, diagnostic testing, and deployment.

---

## 1. Environment Setup Procedure

1. **Clone Repository & Set Virtual Environment**:
   ```powershell
   git clone https://github.com/gondchawarswaraj45/Moviemaxx.git
   cd Moviemaxx
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```powershell
   python -m pip install -r requirements.txt
   ```

3. **Configure Credentials in `.env`**:
   Create a `.env` file from `.env.example`:
   ```dotenv
   NEO4J_URI="neo4j+s://your-instance.databases.neo4j.io"
   NEO4J_USERNAME="neo4j"
   NEO4J_PASSWORD="your-password"
   NEO4J_DATABASE="neo4j"

   GROQ_API_KEY="your-groq-key"
   GROQ_MODEL="llama-3.3-70b-versatile"

   COHERE_API_KEY="your-cohere-key"
   COHERE_EMBED_MODEL="embed-english-v3.0"
   ```

---

## 2. Catalog Ingestion & Graph RAG Indexing Procedure

To import/re-sync 3,022 Bollywood movie records into Neo4j and build the Cohere Graph RAG vector index:

- **Via Web UI**: Click **"↻ Sync CSV & RAG Index"** button on the sidebar.
- **Via API Endpoint**:
  ```powershell
  curl -X POST http://127.0.0.1:8000/api/import
  ```

---

## 3. Running Diagnostic Tests & Verification Procedure

Run the complete 23-test suite covering P2 guardrails, Cohere embeddings, Watch Planner agent, MCP client, and FastAPI endpoints:

```powershell
python -m unittest discover -s tests -v
```

---

## 4. Running the Web Application

Launch the FastAPI uvicorn development server:

```powershell
python -m uvicorn app:app --reload --port 8000
```

- **Recommender Web UI**: `http://127.0.0.1:8000`
- **Knowledge Graph Explorer UI**: `http://127.0.0.1:8000/graph`
- **FastAPI OpenAPI Swagger Docs**: `http://127.0.0.1:8000/docs`
