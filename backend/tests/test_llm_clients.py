from pathlib import Path

import api.ws
import llm
import retrieval.ingest
import retrieval.retriever


def test_shared_clients_have_timeout_and_retries():
    for client in [api.ws.openai_client, retrieval.retriever.openai_client]:
        assert client.timeout == llm.TIMEOUT_S
        assert client.max_retries == llm.MAX_RETRIES
    assert retrieval.ingest.openai_client.timeout == 120.0


def test_every_client_comes_from_llm_module():
    # Guards the policy: a new bare OpenAI(...) would silently get the 600s default again.
    app_dir = Path(__file__).parent.parent / "app"
    offenders = [
        str(path.relative_to(app_dir))
        for path in app_dir.rglob("*.py")
        if path.name != "llm.py" and "OpenAI(" in path.read_text()
    ]
    assert offenders == []
