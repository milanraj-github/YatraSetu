from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test GET / returns 200 and expected welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "SMARTBUS Backend is running"}


def test_health_endpoint():
    """Test GET /api/v1/health returns 200 and expected health payload."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "smartbus-backend",
    }
