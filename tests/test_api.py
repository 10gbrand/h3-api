"""Tests for H3 API endpoints."""

import pytest
from fastapi.testclient import TestClient

from h3_api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "endpoints" in data


def test_health(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_hexbin_invalid_bbox(client):
    """Test hexbin with invalid bbox."""
    response = client.get("/hexbin?bbox=invalid")
    assert response.status_code == 400


def test_hexbin_valid_bbox(client):
    """Test hexbin with valid bbox (may return empty if no data)."""
    response = client.get("/hexbin?bbox=11.0,55.0,14.0,58.0&res=7")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data


def test_cell_invalid(client):
    """Test cell endpoint with invalid cell."""
    response = client.get("/hexbin/cell/invalid")
    assert response.status_code == 400


def test_cell_valid(client):
    """Test cell endpoint with valid cell ID."""
    # Valid H3 cell for Stockholm area
    response = client.get("/hexbin/cell/871f24a81ffffff")
    assert response.status_code == 200
    data = response.json()
    assert "cell_id" in data
    assert "resolution" in data
    assert "center" in data
    assert "boundary" in data


def test_viewport(client):
    """Test viewport endpoint."""
    response = client.get("/hexbin/viewport?bbox=18.0,59.0,18.1,59.1&res=9")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
