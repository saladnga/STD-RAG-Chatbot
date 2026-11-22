from fastapi.testclient import TestClient

import main
import rag.retriever


def broken_database():
    """Pretends the database crashed with a message containing secrets."""
    raise RuntimeError("postgres://admin:secret-password@db.internal")


def test_server_error_does_not_leak_internal_details(monkeypatch):
    monkeypatch.setattr(rag.retriever, "chunks_collection", broken_database)

    response = TestClient(main.app).get("/rag/stats")

    assert response.status_code == 500
    assert "secret-password" not in response.text