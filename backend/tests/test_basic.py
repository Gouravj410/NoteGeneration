from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_config():
    assert settings.PROJECT_NAME == "StudyForge AI"

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
