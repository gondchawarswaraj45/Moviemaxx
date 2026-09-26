---
name: cohere-vector-search
description: Performs Cohere vector embedding similarity search over relative movie dataset chunks for semantic query matching.
---

# Cohere Vector Search Skill

## Capabilities
- Generates 384+ dimension embeddings using Cohere API `embed-english-v3.0`.
- Searches relative text chunks (`OVERVIEW`, `CAST_ROLE`, `THEME_VERDICT`).
- Computes cosine similarity between query vector and movie chunk vectors.
- Performs Reciprocal Rank Fusion (RRF) with Graph Cypher traversal.
