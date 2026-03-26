import httpx
import pytest
from app.main import app


@pytest.fixture
def client():
    transport = httpx.ASGITransport(app=app)
    with httpx.Client(transport=transport, base_url="http://test") as c:
        yield c


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_returns_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Hello World" in response.text
