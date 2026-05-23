from __future__ import annotations

import hashlib
import re

from singer_core.auth import generate_auth_headers


def test_returns_all_required_keys() -> None:
    result = generate_auth_headers("key", "secret")
    expected_keys = {
        "X-Auth-Key",
        "X-Auth-Timestamp",
        "X-Auth-Nonce",
        "X-Auth-Signature",
    }
    assert set(result.keys()) == expected_keys


def test_auth_key_value_matches_input() -> None:
    result = generate_auth_headers("my_key", "my_secret")
    assert result["X-Auth-Key"] == "my_key"


def test_timestamp_is_millisecond_format() -> None:
    result = generate_auth_headers("key", "secret")
    ts = result["X-Auth-Timestamp"]
    assert re.fullmatch(r"\d{13}", ts), f"Timestamp not 13-digit: {ts}"


def test_nonce_is_uuid_format() -> None:
    result = generate_auth_headers("key", "secret")
    nonce = result["X-Auth-Nonce"]
    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    assert re.fullmatch(uuid_pattern, nonce), f"Nonce not UUID: {nonce}"


def test_signature_is_md5_hex() -> None:
    result = generate_auth_headers("key", "secret")
    sig = result["X-Auth-Signature"]
    assert re.fullmatch(r"[0-9a-f]{32}", sig), f"Signature not MD5 hex: {sig}"


def test_signature_computed_correctly() -> None:
    result = generate_auth_headers("key", "secret")
    raw = "key" + "secret" + result["X-Auth-Timestamp"] + result["X-Auth-Nonce"]
    expected = hashlib.md5(raw.encode()).hexdigest()
    assert result["X-Auth-Signature"] == expected


def test_different_calls_produce_different_signatures() -> None:
    r1 = generate_auth_headers("key", "secret")
    r2 = generate_auth_headers("key", "secret")
    assert r1["X-Auth-Signature"] != r2["X-Auth-Signature"]
    assert r1["X-Auth-Nonce"] != r2["X-Auth-Nonce"]
