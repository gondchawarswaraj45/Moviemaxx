<![CDATA[<div align="center">

# 🎬 MovieMaxx

### **Bollywood Film Graph — Context-Aware Movie Recommendation System**

[![Neo4j](https://img.shields.io/badge/Neo4j-Aura-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)](https://neo4j.com/product/auradb/)
[![Cypher](https://img.shields.io/badge/Cypher-Query%20Language-4581C3?style=for-the-badge)](https://neo4j.com/docs/cypher-manual/)
[![MCP](https://img.shields.io/badge/MCP-Agent%20Protocol-FF6F00?style=for-the-badge)](https://neo4j.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

> A graph-powered, context-aware movie recommendation engine built on **Neo4j** that models **1,000+ Bollywood films** across **19 genres** — leveraging knowledge graph traversals, AI agent integration, and persistent memory for intelligent, personalized movie discovery.

---

</div>

## 📌 Problem Statement

**Context-Aware Customer Support Agent** — Traditional movie recommendation systems rely on flat databases and simple filtering. They fail to capture the rich, interconnected relationships between movies, actors, directors, genres, and streaming platforms. MovieMaxx solves this by treating the entire Bollywood film ecosystem as a **knowledge graph**, enabling multi-hop relationship discovery and context-aware, conversational recommendations.

---

## 🌟 Key Features

| Feature | Description |
|---------|-------------|
| 🎯 **Graph-Based Recommendations** | Traverse multi-hop relationships between movies, actors, directors, and genres for deep, meaningful suggestions |
| 🧠 **Persistent Agent Memory** | Neo4j Agent Memory Service remembers user preferences, past searches, and interaction history across sessions |
| 💬 **Conversational AI Interface** | Natural language queries powered by Neo4j MCP — ask questions like *"Recommend highly rated thriller movies"* |
| 📊 **1,000+ Film Catalog** | Comprehensive Bollywood movie database with IMDb ratings, cast, directors, and streaming availability |
| 🎭 **19 Connected Genres** | Action, Adventure, Biography, Comedy, Coming-of-Age, Crime, Drama, Family, Historical, Horror, Musical, Mystery, and more |
| 📺 **Streaming Platform Info** | Know where to watch — JioCinema, Prime Video, Sun NXT, JioHotstar, and others |
| 📥 **CSV → Neo4j Sync** | Import and sync movie catalogs from CSV directly into the graph database |
| 🔍 **Extended Graph Records** | Rich metadata per film including graph record IDs, ratings, genre tags, and streaming links |

---

## 🏗️ Architecture

```
┌──────────────────┐       ┌──────────────────────┐       ┌─────────────────────┐
│                  │       │                      │       │                     │
│   User / Agent   │──────▶│   Neo4j Aura MCP     │──────▶│   Neo4j Aura DB     │
│   (Natural Lang) │       │   (Model Context     │       │   (Graph Database)  │
│                  │       │    Protocol)          │       │                     │
└──────────────────┘       └──────────────────────┘       └─────────────────────┘
                                    │                              │
                                    ▼                              ▼
                           ┌──────────────────┐          ┌──────────────────────┐
                           │  Agent Memory    │          │  Knowledge Graph     │
                           │  Service         │          │  ├── Movies (1,000+) │
                           │  ├── Preferences │          │  ├── Persons (Cast)  │
                           │  ├── History     │          │  ├── Directors       │
                           │  └── Context     │          │  ├── Genres (19)     │
                           └──────────────────┘          │  └── Streaming Info  │
                                                         └──────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Database** | [Neo4j Aura](https://neo4j.com/product/auradb/) | Cloud-hosted graph database |
| **Query Language** | Cypher | Graph traversal & pattern matching |
| **Agent Protocol** | Neo4j Aura MCP | AI agent ↔ database communication |
| **Memory** | Neo4j Agent Memory Service | Persistent user context & preferences |
| **Data Pipeline** | CSV → Neo4j Import | Bulk catalog ingestion |
| **Environment** | GitHub Codespaces / VS Code | Development & deployment |

---

## ⚡ Getting Started

### Prerequisites

- [Neo4j Aura](https://neo4j.com/product/auradb/) account (Free tier available)
- [VS Code](https://code.visualstudio.com/) or GitHub Codespaces
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/gondchawarswaraj45/Moviemaxx.git
cd Moviemaxx
```

### 2. Configure Environment

Create a `.env` file from the example template:

```bash
cp .env.example .env
```

Update `.env` with your Neo4j Aura credentials (see `.env.example` for the required variables).

> ⚠️ **Important:** Never commit your `.env` file. It is already included in `.gitignore`.

### 3. Set Up Neo4j Aura MCP

1. Log in to the [Neo4j Aura Console](https://console.neo4j.io/)
2. Locate your instance ID under **Instances**
3. Update the MCP configuration in `.vscode/mcp.json` with your instance ID
4. Start the MCP server from your editor's MCP controls
5. Authorize access when prompted

### 4. Load the Movie Dataset

Import the Bollywood movie catalog into your Neo4j instance:

```bash
# Use the CSV sync feature to import the dataset
# Or load the Neo4j example movie dataset:
```

```cypher
:play movies
```

---

## 🔍 How It Works

### Graph Data Model

```
(:Person)-[:ACTED_IN]->(:Movie)-[:IN_GENRE]->(:Genre)
(:Person)-[:DIRECTED]->(:Movie)-[:AVAILABLE_ON]->(:Platform)
(:Movie)-[:HAS_RATING {score: 9.1}]->(:Rating)
```

### Conversational Recommendations

MovieMaxx uses Neo4j's MCP to understand natural language queries and translate them into graph traversals:

| User Query | What Happens Behind the Scenes |
|-----------|-------------------------------|
| *"Recommend highly rated thriller movies"* | Traverses `Movie→Genre` relationships, filters by IMDb rating |
| *"Find movies of Shahrukh Khan"* | Finds `Person` node, traverses `ACTED_IN` relationships |
| *"Show me more like those"* | Uses Agent Memory to recall prior recommendations and find similar patterns |

### Persistent Memory

The Agent Memory Service creates a **context graph** per user:
- 🔄 Remembers previous searches and recommendations
- 📈 Learns preferences over time
- 🎯 Delivers increasingly personalized suggestions with each interaction

---

## 👥 Team

| Name | Role |
|------|------|
| **Swaraj Gondchawar** | Team Lead |
| **Siddhesh Asati** | Team Member |
| **Vishal Auti** | Team Member |

---

## 📚 Resources

- [Neo4j GraphAcademy](https://graphacademy.neo4j.com/) — Free hands-on graph database courses
- [Cypher Manual](https://neo4j.com/docs/cypher-manual/) — Query language reference
- [Neo4j Aura Documentation](https://neo4j.com/docs/aura/) — Cloud database docs
- [Neo4j Community](https://community.neo4j.com/) — Developer community forum

---

## 📝 License

This project was built as part of the **Neo4j Agent Memory: Build Sprint, Pune — hackFront India 2026 Pre-Hack Series**.

---

<div align="center">

**Built with ❤️ using Neo4j Graph Database**

*Stories connect to stories.*

</div>
]]>
