from pathlib import Path

import llm_clients
import rag.ingest_pdf
import rag.retriever
import routers.chat


def test_shared_clients_have_timeout_and_retries():
    for client in [routers.chat.openai_client, rag.retriever.openai_client]:
        assert client.timeout == llm_clients.TIMEOUT_S
        assert client.max_retries == llm_clients.MAX_RETRIES
    assert rag.ingest_pdf.openai_client.timeout == 120.0


def test_every_client_comes_from_llm_clients():
    # Guards the policy: a new bare OpenAI(...) would silently get the 600s default again.
    app_dir = Path(__file__).parent.parent / "app"
    offenders = [
        str(path.relative_to(app_dir))
        for path in app_dir.rglob("*.py")
        if path.name != "llm_clients.py" and "OpenAI(" in path.read_text()
    ]
    assert offenders == []
