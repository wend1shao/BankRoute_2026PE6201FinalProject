"""API contract tests for the demo service."""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402


def test_demo_page_renders_core_product_contract():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Route banking enquiries" in page
    assert "INTENDED USE" in page
    assert "EXPLICIT NON-USE" in page
    assert "OpenRouter second opinion" in page


def test_health_exposes_only_key_availability_boolean():
    client = app.test_client()
    payload = client.get("/api/health").get_json()
    assert payload["status"] == "ok"
    assert isinstance(payload["openrouter_key_available"], bool)
    serialized = str(payload).lower()
    assert "bearer " not in serialized
    assert "sk-" not in serialized


def test_route_does_not_echo_original_unredacted_message():
    client = app.test_client()
    response = client.post(
        "/api/route",
        json={"message": "My card 4111 1111 1111 1111 was charged an ATM fee."},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert "original_message" not in payload
    assert "4111" not in payload["redacted_message"]


def test_invalid_payload_fails_closed():
    client = app.test_client()
    response = client.post("/api/route", json={"message": 12})
    assert response.status_code == 400
    assert response.get_json()["type"] == "validation_error"
