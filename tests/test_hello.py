import json
import pytest
from app import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_hello_returns_200(client):
    """GET /hello should return HTTP 200."""
    response = client.get("/hello")
    assert response.status_code == 200


def test_hello_returns_json(client):
    """GET /hello should return JSON content."""
    response = client.get("/hello")
    assert response.content_type == "application/json"


def test_hello_message(client):
    """GET /hello should return the expected greeting message."""
    response = client.get("/hello")
    data = json.loads(response.data)
    assert data == {"message": "Hello, World!"}


def test_hello_post_not_allowed(client):
    """POST /hello should return HTTP 405 Method Not Allowed."""
    response = client.post("/hello")
    assert response.status_code == 405
