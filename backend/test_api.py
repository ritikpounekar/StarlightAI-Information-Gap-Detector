import os
import unittest
from unittest.mock import patch

import pymupdf
from fastapi.testclient import TestClient

from main import _frontend_origins, app


class ResearchApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_extracts_text_from_uploaded_pdf(self):
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 72), "Official scholarship deadline is November 15, 2026.")
        response = self.client.post(
            "/api/extract",
            files={"file": ("notice.pdf", document.tobytes(), "application/pdf")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("November 15, 2026", response.json()["text"])

    def test_rejects_private_network_source_urls(self):
        response = self.client.post(
            "/api/research",
            json={
                "query": "Check scholarship deadline",
                "sources": [{"name": "Local server", "url": "http://127.0.0.1/private"}],
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_api_health_route_is_available(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "online")

    def test_stream_endpoint_returns_unbuffered_sse_with_cors(self):
        response = self.client.post(
            "/api/research/stream",
            headers={"Origin": "http://localhost:5173"},
            json={
                "query": "Check scholarship deadline",
                "sources": [
                    {
                        "name": "Official notice",
                        "text": "The scholarship application deadline is November 15, 2026.",
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        self.assertEqual(response.headers["x-accel-buffering"], "no")
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")
        self.assertIn("event: result\ndata:", response.text)
        self.assertIn("event: complete\ndata: {}", response.text)

    def test_frontend_origins_accept_csv_and_trim_trailing_slashes(self):
        with patch.dict(
            os.environ,
            {"FRONTEND_ORIGIN": " https://one.example/ ,https://two.example/// "},
        ):
            self.assertEqual(
                _frontend_origins(),
                ["https://one.example", "https://two.example"],
            )


if __name__ == "__main__":
    unittest.main()
