import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from qasccs.webapp.app import app  # noqa: E402

client = TestClient(app)


def test_index_returns_html_form():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<form" in resp.text
    assert 'id="algorithm"' in resp.text


def test_api_risk_valid_request():
    resp = client.post("/api/risk", json={
        "algorithm": "RSA-2048",
        "data_lifetime_years": 10,
        "data_classification": "high",
        "scenario": "moderate",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk"] in ("LOW", "MEDIUM", "HIGH")
    assert body["recommended_mode"] in ("classical", "pqc", "hybrid")
    assert "rationale" in body


def test_api_risk_pqc_algorithm():
    resp = client.post("/api/risk", json={
        "algorithm": "KYBER-768",
        "data_lifetime_years": 20,
        "data_classification": "critical",
    })
    assert resp.status_code == 200
    assert resp.json()["recommended_mode"] in ("pqc", "hybrid")


def test_api_risk_invalid_algorithm_returns_422():
    resp = client.post("/api/risk", json={
        "algorithm": "NOT-A-REAL-ALGORITHM",
        "data_lifetime_years": 10,
    })
    assert resp.status_code == 422


def test_api_risk_missing_required_field_returns_422():
    resp = client.post("/api/risk", json={"algorithm": "RSA-2048"})
    assert resp.status_code == 422


def test_api_risk_out_of_range_lifetime_returns_422():
    resp = client.post("/api/risk", json={"algorithm": "RSA-2048", "data_lifetime_years": 999})
    assert resp.status_code == 422
