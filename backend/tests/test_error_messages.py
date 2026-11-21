from fastapi.testclient import TestClient

import main
import rag.retriever


class BrokenDatabase:
    """Pretends the database crashed with a message containing secrets."""
    def table(self, *args, **kwargs):
        raise RuntimeError("postgres://admin:secret-password@db.internal")


def test_server_error_does_not_leak_internal_details(monkeypatch):
    monkeypatch.setattr(rag.retriever, "supabase", BrokenDatabase())

    response = TestClient(main.app).get("/rag/stats")

    assert response.status_code == 500
    assert "secret-password" not in response.text