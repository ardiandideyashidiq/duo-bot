from __future__ import annotations

import base64
import json

import pytest

from duo_bot.errors import ConfigError
from duo_bot.jwt import decode_claims, get_subject, mask_id, redact


def make_jwt(payload: dict) -> str:
    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps(payload).encode())
    return f"{header}.{body}.signature"


def test_decode_claims_without_padding():
    token = make_jwt({"sub": "123456", "exp": 9999999999})
    claims = decode_claims(token)
    assert claims["sub"] == "123456"
    assert claims["exp"] == 9999999999


def test_get_subject():
    assert get_subject(make_jwt({"sub": "abc"})) == "abc"


def test_get_subject_requires_sub_claim():
    with pytest.raises(ConfigError):
        get_subject(make_jwt({"aud": "x"}))


def test_decode_rejects_non_jwt():
    with pytest.raises(ConfigError):
        decode_claims("not-a-jwt")


def test_decode_rejects_bad_payload():
    with pytest.raises(ConfigError):
        decode_claims("a.!!!.c")


def test_mask_id():
    assert mask_id("800328722423901") == "***********3901"
    assert mask_id("12") == "12"


def test_redact_secrets():
    jwt = make_jwt({"sub": "abc"})
    text = f"Authorization: Bearer {jwt} and token bot123456:ABCDEFGHIJKLMNOPQRSTUVWX"
    cleaned = redact(text)
    assert jwt not in cleaned
    assert "Bearer ***" in cleaned
    assert "bot***" in cleaned
