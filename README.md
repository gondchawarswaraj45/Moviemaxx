# 🎬 MovieMaxx — Movie Recommendation System

> A graph-powered movie recommendation system built with **Neo4j** that leverages the natural relationships between movies, actors, directors, and genres to deliver intelligent, context-aware suggestions.

---

## 📌 Project Domain

**Domain:** Movie Recommendations / Entertainment Intelligence

This project explores how **graph databases** can be used to model and query the complex, interconnected world of movies. Unlike traditional recommendation engines that rely solely on collaborative filtering or content-based approaches, MovieMaxx harnesses the power of a **knowledge graph** to uncover deep, multi-hop relationships — such as *"movies directed by the same person who acted alongside your favorite actor"* or *"highly-rated films in a genre you haven't explored yet."*

### Why Graphs for Recommendations?

| Traditional (Relational) | Graph-Based (Neo4j) |
|---|---|
| Flat tables with JOINs | Nodes & relationships — natural data model |
| Expensive multi-hop queries | Traversals are fast & intuitive |
| Hard to discover hidden connections | Relationships are first-class citizens |
| Rigid schema | Flexible, evolving schema |

---

## 👥 Team

| Name | Role |
|---|---|
| **Swaraj Gondchawar** | Team Member |
| **Siddhesh Asati** | Team Member |
| **Vishal Auti** | Team Member |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Database** | [Neo4j Aura](https://neo4j.com/product/auradb/) (Graph Database) |
| **Query Language** | Cypher |
| **AI / Agent Tools** | Neo4j Aura MCP, Neo4j Agent Memory Service |
| **Environment** | GitHub Codespaces / VS Code |

---

## 🏗️ Architecture

```
┌──────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   User /     │       │   Application    │       │    Neo4j Aura   │
│   AI Agent   │──────▶│   Layer (MCP)    │──────▶│   Graph DB      │
└──────────────┘       └──────────────────┘       └─────────────────┘
                              │                          │
                              ▼                          ▼
                       ┌──────────────┐          ┌──────────────────┐
                       │ Agent Memory │          │  Knowledge Graph │
                       │   Service    │          │  (Movies, Actors,│
                       └──────────────┘          │  Genres, etc.)   │
                                                 └──────────────────┘
```

---

## 🎯 Key Features

- **Graph-Based Recommendations** — Traverse relationships between movies, actors, directors, and genres for meaningful suggestions
- **Cypher-Powered Queries** — Use Neo4j's expressive query language to find hidden connections
- **AI Agent Integration** — Connect with Neo4j MCP for intelligent, conversational recommendations
- **Persistent Memory** — Leverage Neo4j Agent Memory Service to remember user preferences across sessions
- **Knowledge Graph Exploration** — Visualize and explore the movie graph interactively

---

## ⚡ Getting Started

### Prerequisites

- [Neo4j Aura Free](https://neo4j.com/product/auradb/) account
- [VS Code](https://code.visualstudio.com/) or GitHub Codespaces

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Moviemaxx
```

### 2. Configure Environment

Copy the example environment file and fill in your Neo4j credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Neo4j Aura instance details:

```env
NEO4J_URI="neo4j://your-instance-address:7687"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="your-password"
NEO4J_DATABASE="neo4j"
NEO4J_READ_ONLY="true"
```

### 3. Set Up Neo4j Aura MCP

1. In the [Aura Console](https://console.neo4j.io/), find your instance ID under **Instances**.
2. Replace `<instance-id>` in `.vscode/mcp.json` with your Aura instance ID.
3. Start the `neo4j-mcp` server from your editor's MCP server controls.
4. Authorize access when prompted.

### 4. Load Movie Data

Use the Neo4j example movie dataset or load your own:

```cypher
:play movies
```

---

## 📊 Sample Cypher Queries

**Find movie recommendations based on shared actors:**

```cypher
MATCH (u:Person)-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(coActor:Person)-[:ACTED_IN]->(rec:Movie)
WHERE u.name = "Tom Hanks" AND NOT (u)-[:ACTED_IN]->(rec)
RETURN rec.title AS Recommendation, COUNT(coActor) AS SharedActors
ORDER BY SharedActors DESC
LIMIT 10
```

**Discover genre-based recommendations:**

```cypher
MATCH (m:Movie)-[:IN_GENRE]->(g:Genre)<-[:IN_GENRE]-(rec:Movie)
WHERE m.title = "The Matrix"
RETURN rec.title AS Recommendation, COLLECT(g.name) AS SharedGenres
ORDER BY SIZE(SharedGenres) DESC
LIMIT 10
```

---

## 📚 Resources

- [Neo4j GraphAcademy](https://graphacademy.neo4j.com/) — Free hands-on courses
- [Neo4j Documentation](https://neo4j.com/docs/) — Product & Cypher docs
- [Neo4j Example Datasets](https://neo4j.com/docs/getting-started/appendix/example-data/) — Ready-to-use datasets
- [Neo4j Community](https://community.neo4j.com/) — Developer community forum

---

## 📝 License

This project was built as part of the [Neo4j Mini Agentic Hack](https://github.com/neo4j-graphacademy/workshop-hackathon).
