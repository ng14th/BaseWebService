"""Tests for app/api/health/views.py and app/api/router.py"""
import pytest
from fastapi.testclient import TestClient

from app.api.application import get_app


@pytest.fixture
def client():
    with TestClient(get_app()) as c:
        yield c


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"] == {"status": "healthy"}


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "my-app service is running"}
