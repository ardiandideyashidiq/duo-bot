from __future__ import annotations

import json
from typing import ClassVar

import pytest

import duo_bot.client as client_module
from duo_bot.client import DuolingoClient
from duo_bot.errors import Abort, AuthError


class FakeResponse:
    def __init__(self, status: int, payload: dict | None = None, *, text: str | None = None):
        self.status_code = status
        self._payload = payload
        self.headers: dict[str, str] = {}
        self.text = text if text is not None else (json.dumps(payload) if payload else "")

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    instances: ClassVar[list[FakeSession]] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.headers: dict[str, str] = {}
        self.requests: list[tuple[str, str, dict]] = []
        self.responses: list[FakeResponse] = []
        self.closed = False
        FakeSession.instances.append(self)

    def request(self, method: str, url: str, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_client(monkeypatch):
    FakeSession.instances = []
    monkeypatch.setattr(client_module, "Session", FakeSession)
    monkeypatch.setattr(client_module.time, "sleep", lambda _seconds: None)
    client = DuolingoClient("token", impersonate="chrome", timeout=5)
    return client


def test_headers_and_session_options(fake_client):
    session = fake_client._session
    assert session.kwargs["impersonate"] == "chrome"
    assert session.kwargs["timeout"] == 5
    assert session.headers["Authorization"] == "Bearer token"


def test_successful_json(fake_client):
    fake_client._session.responses = [FakeResponse(200, {"ok": True})]
    assert fake_client.request("GET", "/users/1") == {"ok": True}


def test_auth_error_is_not_retried(fake_client):
    fake_client._session.responses = [FakeResponse(401, {"error": "unauthorized"})]
    with pytest.raises(AuthError):
        fake_client.request("GET", "/users/1")
    assert len(fake_client._session.requests) == 1


def test_rate_limit_is_retried(fake_client):
    fake_client._session.responses = [FakeResponse(429, {}), FakeResponse(200, {"ok": True})]
    assert fake_client.request("GET", "/users/1") == {"ok": True}
    assert len(fake_client._session.requests) == 2


def test_server_error_exhausts_retries(fake_client):
    fake_client._session.responses = [FakeResponse(500, {}) for _ in range(3)]
    with pytest.raises(Abort):
        fake_client.request("GET", "/users/1", retries=3)
    assert len(fake_client._session.requests) == 3


def test_client_error_aborts(fake_client):
    fake_client._session.responses = [FakeResponse(400, {}, text="bad request")]
    with pytest.raises(Abort):
        fake_client.request("GET", "/users/1")


def test_non_json_aborts(fake_client):
    fake_client._session.responses = [FakeResponse(200, None, text="<html>")]
    with pytest.raises(Abort):
        fake_client.request("GET", "/users/1")


def test_context_manager_closes(fake_client):
    with fake_client as client:
        assert client is fake_client
    assert fake_client._session.closed
