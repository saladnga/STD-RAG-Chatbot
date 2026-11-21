from fastapi.testclient import TestClient
from starlette.requests import Request

import main
from rate_limiter import client_ip

client = TestClient(main.app)


def test_rag_ask_requires_login():
    assert client.post("/rag/ask", json={"question": "hi"}).status_code == 401


def test_predict_requires_login():
    assert client.post("/predict", json={"text": "itching"}).status_code == 401


def _request(headers):
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": ("10.0.0.1", 1234)})

def test_rate_limit_key_ignores_spoofed_ip():
    # The client typed "6.6.6.6"; the proxy appended the real IP "203.0.113.5".
    assert client_ip(_request({"X-Forwarded-For": "6.6.6.6, 203.0.113.5"})) == "203.0.113.5"


def test_rate_limit_key_without_proxy():
    assert client_ip(_request({})) == "10.0.0.1"