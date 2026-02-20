"""
Integration Tests – Health & Analyze Endpoints

This module contains integration-level tests for core API endpoints.
It verifies both functional behavior and validation rules.

The tests use the shared `client` fixture (TestClient)
to simulate real HTTP requests without running a live server.

────────────────────────────────────────────

1) Health Endpoint Test

test_health_check:

- Sends a GET request to `/health`.
- Verifies that the status code is 200 (service is alive).
- Confirms response structure:
    • "status" must be "ok"
    • "app" field must exist

Purpose:
Ensures the service is running and returns a valid liveness response.
This is critical for monitoring systems and production readiness.

────────────────────────────────────────────

2) Analyze Endpoint – Smoke Test

test_analyze_stub_returns_valid_schema:

- Sends a valid POST request to `/api/v1/analyze`.
- Verifies status code 200.
- Confirms response contains:
    • "category"
    • "summary"
- Ensures category value is one of:
    ("stock", "news", "portfolio", "general")

Purpose:
Validates that the endpoint is functional
and respects the expected response contract.

────────────────────────────────────────────

3) Validation Test – Empty Question

test_analyze_rejects_empty_question:

- Sends a request with an empty "question".
- Expects HTTP 422 (validation error).

Purpose:
Confirms input validation rules are enforced
(min_length constraint in schema).

────────────────────────────────────────────

4) Validation Test – Missing Field

test_analyze_rejects_missing_field:

- Sends a request without the required "question" field.
- Expects HTTP 422.

Purpose:
Ensures required fields are strictly enforced
by Pydantic schema validation.

────────────────────────────────────────────

Why These Tests Matter

✔ Verifies API contract integrity
✔ Ensures validation is properly enforced
✔ Prevents regression during refactoring
✔ Confirms structured JSON responses
✔ Guarantees production-safe behavior

These tests act as a safety net
for the application's core endpoints.
"""


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "app" in body


def test_analyze_stub_returns_valid_schema(client):
    """Smoke test: verify /analyze returns a valid structured JSON response."""
    response = client.post(
        "/api/v1/analyze",
        json={"question": "What is the stock price of Apple?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "category" in body
    assert "summary" in body
    assert body["category"] in ("stock", "news", "portfolio", "general")


def test_analyze_rejects_empty_question(client):
    """Validation: empty question should return 422."""
    response = client.post("/api/v1/analyze", json={"question": ""})
    assert response.status_code == 422


def test_analyze_rejects_missing_field(client):
    """Validation: missing 'question' field should return 422."""
    response = client.post("/api/v1/analyze", json={})
    assert response.status_code == 422
