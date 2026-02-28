"""
Pytest Configuration – Test Client Setup (tests/conftest.py)

This module defines shared test configuration and reusable fixtures
for the entire test suite.

In pytest, `conftest.py` is a special file. Any fixtures defined here
are automatically available across all test files without importing them.

────────────────────────────────────────────

Purpose of This File

- Provides a reusable FastAPI TestClient instance.
- Centralizes test setup logic.
- Prepares the application for endpoint testing.

────────────────────────────────────────────

Client Fixture

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

Explanation:

- The `client` fixture creates a FastAPI TestClient instance.
- It wraps the actual FastAPI application (`app`).
- Allows sending HTTP requests (GET, POST, etc.) without running
  a real server.

Scope:

- scope="session" means the client is created once per test session.
- Improves performance by avoiding repeated initialization.

────────────────────────────────────────────

Benefits

✔ Reusable test client across all test files
✔ Avoids duplicate setup code
✔ Enables clean endpoint testing
✔ Simulates real API requests internally
✔ Supports testing of routes, validation, and error handling

────────────────────────────────────────────

Example Usage in a Test File

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200

Here, `client` is automatically injected by pytest.

────────────────────────────────────────────

Architecture During Testing

Test Function
   ↓
client fixture
   ↓
TestClient(app)
   ↓
FastAPI Application
   ↓
Response

This file acts as the testing gateway for the application.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Returns a synchronous test client for the FastAPI app."""
    return TestClient(app)
