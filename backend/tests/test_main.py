from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_frontend():
    static_dir = Path(__file__).parent.parent / "static"
    if not static_dir.exists():
        pytest.skip("Static frontend not built")
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

