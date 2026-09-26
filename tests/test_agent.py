import unittest
import json
from unittest.mock import MagicMock, patch

from app import (
    apply_follow_up_memory,
    compose_answer,
    extract_filters,
    fallback_filters,
    requested_result_limit,
)
from movie_graph import load_movie_rows, normalize_movie_row


class MovieCatalogTests(unittest.TestCase):
    def test_supplied_csv_loads_all_movies_with_graph_fields(self):
        movies = load_movie_rows()

        self.assertGreaterEqual(len(movies), 1000)
        self.assertEqual(movies[0]["properties"]["title"], "Dabangg")
        self.assertIn("Historical", movies[0]["genres"])
        self.assertGreater(len(movies[0]["cast"]), 0)
        self.assertTrue(movies[0]["roles"])

    def test_invalid_rows_without_an_id_or_title_are_skipped(self):
        self.assertIsNone(normalize_movie_row({"movie_id": "", "movie_name": "Untitled"}))
        self.assertIsNone(normalize_movie_row({"movie_id": "BW123", "movie_name": ""}))

    def test_sci_fi_genre_overrides_noisy_csv_labels(self):
        false_positive = normalize_movie_row({
            "movie_id": "BW00497",
            "movie_name": "Vicky Donor - Extended Graph Record 497",
            "genre": "Sci-Fi",
            "secondary_genres": "Drama",
        })
        corrected = normalize_movie_row({
            "movie_id": "BW00040",
            "movie_name": "PK",
            "genre": "Action",
            "secondary_genres": "Social|Historical",
        })

        self.assertNotIn("Sci-Fi", false_positive["genres"])
        self.assertEqual(corrected["genres"], ["Comedy", "Drama", "Sci-Fi"])
        self.assertIsNone(corrected["platform"])


class MovieQuestionTests(unittest.TestCase):
    def test_local_filters_read_genre_year_and_high_rating(self):
        filters = fallback_filters(
            "Recommend highly rated comedy movies from 2015",
            ["Action", "Comedy", "Thriller"],
            [],
        )

        self.assertEqual(filters["genres"], ["Comedy"])
        self.assertEqual(filters["year"], 2015)
        self.assertEqual(filters["minimum_rating"], 7.0)

    def test_follow_up_reuses_filters_from_graph_memory(self):
        history = [{"filters": {"genres": ["Thriller"], "minimum_rating": 8.0, "limit": 5}}]

        filters = fallback_filters("Show me more like those", ["Comedy", "Thriller"], history)

        self.assertEqual(filters["genres"], ["Thriller"])
        self.assertEqual(filters["minimum_rating"], 8.0)
        self.assertEqual(filters["limit"], 5)

    def test_groq_extracts_structured_filters_from_question(self):
        client = MagicMock()
        client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps({"genres": ["Comedy"], "year": 2015, "limit": 4})))
        ]

        with patch("app.groq_client", client), patch("app.resolve_groq_model", return_value="test-model"):
            filters, used_groq = extract_filters("A comedy from 2015", ["Comedy", "Thriller"], [])

        self.assertTrue(used_groq)
        self.assertEqual(filters["genres"], ["Comedy"])
        self.assertEqual(filters["year"], 2015)
        self.assertEqual(filters["limit"], 4)

    def test_follow_up_memory_excludes_previously_shown_movies(self):
        filters = {"genres": ["Thriller"], "minimum_rating": 7.0}
        history = [{
            "filters": {"genres": ["Thriller"], "minimum_rating": 7.0},
            "movies": [{"id": "BW00001"}, {"id": "BW00002"}],
        }]

        remembered = apply_follow_up_memory("Show me more like those", filters, history)

        self.assertEqual(remembered["genres"], ["Thriller"])
        self.assertEqual(remembered["exclude_ids"], ["BW00001", "BW00002"])

    def test_answer_uses_movie_fields_without_inventing_details(self):
        candidates = [{
            "id": "BW00001",
            "title": "Dabangg",
            "year": 2010,
            "rating": 6.5,
            "genres": ["Action", "Comedy"],
            "platform": None,
        }]

        answer, used_groq = compose_answer("Suggest an action movie", {}, candidates, [])

        self.assertFalse(used_groq)
        self.assertIn("Dabangg", answer)
        self.assertIn("Action, Comedy", answer)
        self.assertNotIn("streaming:", answer)

    def test_single_result_answer_uses_singular_wording(self):
        movies = [{"id": "BW00040", "title": "PK", "year": 2014, "genres": ["Sci-Fi"]}]

        answer, _ = compose_answer("Find me an Sci-Fi movie", {"genres": ["Sci-Fi"], "limit": 1}, movies, [])

        self.assertTrue(answer.startswith("I found this film in the Neo4j catalog"))
        self.assertIn("Want another recommendation?", answer)

    def test_singular_movie_request_returns_one_result(self):
        self.assertEqual(requested_result_limit("Find me an Sci-Fi movie", 6), 1)
        self.assertEqual(requested_result_limit("Find me Sci-Fi movies", 6), 6)


if __name__ == "__main__":
    unittest.main()
