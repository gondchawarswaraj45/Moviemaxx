import unittest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app import app

class APIEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("p2_guardrails_active", data)

    def test_skills_metadata_endpoint(self):
        response = self.client.get("/api/metadata/skills")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("catalog_metadata", data)
        self.assertIn("watch_contexts", data)
        self.assertIn("agent_skills", data)

    def test_graph_data_catalog_mode(self):
        response = self.client.get("/api/graph/data?mode=catalog")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mode"], "catalog")
        self.assertIn("nodes", data)
        self.assertIn("edges", data)

    def test_graph_data_metadata_mode(self):
        response = self.client.get("/api/graph/data?mode=metadata")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mode"], "metadata")
        self.assertIn("nodes", data)
        self.assertIn("edges", data)

    def test_api_test_neo4j(self):
        response = self.client.get("/api/test/neo4j")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["test"], "Neo4j Graph Database Test")

    def test_api_test_embeddings(self):
        response = self.client.get("/api/test/embeddings")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["test"], "Embedding Model Test")

    def test_api_test_vector_db(self):
        response = self.client.get("/api/test/vector-db")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["test"], "Vector Database Search Test")

    def test_graph_ui_page(self):
        response = self.client.get("/graph")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Knowledge Graph Explorer", response.text)

if __name__ == "__main__":
    unittest.main()
