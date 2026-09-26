---
name: movie-graph-search
description: Executes structured Cypher graph traversal queries over Neo4j to find movies by genre, cast, director, rating, year, or platform.
---

# Movie Graph Search Skill

## Capabilities
- Query `(Movie)` nodes and relationships (`HAS_GENRE`, `FEATURES`, `DIRECTED_BY`, `AVAILABLE_ON`).
- Filter by exact or fuzzy parameters:
  - `genres`: list of genre strings
  - `actor`: actor/performer name string
  - `director`: director name string
  - `year`: release year integer
  - `minimum_rating`: IMDb minimum score float
  - `platform`: OTT platform name string

## Schema
Input: `filters` dict containing query parameters.
Output: List of matching `Movie` records with genres, cast, director, rating, and platform metadata.
