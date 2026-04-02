from fastapi.testclient import TestClient

from app.db.init_db import init_db
from app.main import app


client = TestClient(app)


def test_podcast_list_endpoint():
    init_db()
    response = client.get("/api/v1/podcasts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
