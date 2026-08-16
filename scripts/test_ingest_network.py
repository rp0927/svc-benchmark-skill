#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ingest_network: common shapes, fail-closed raw location, and sanitization."""
from __future__ import annotations

import base64
from contextlib import redirect_stdout
from io import StringIO
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ingest_network import (  # noqa: E402
    ingest,
    main as ingest_main,
    raw_source_is_temporary,
    write_session,
)
from network_sanitizer import sanitize_network_document  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def test_clean_har_is_detached():
    har = {"log": {"entries": [{"request": {"url": "https://ex.test/"}, "response": {"status": 200}}]}}
    out = ingest(har)
    check(out["format"] == "har", out["format"])
    check(out["har"] is not har, "HAR must be a detached sanitized copy")


def test_har_five_secret_classes_are_removed() -> None:
    secrets = (
        "query-value-123",
        "auth-value-123",
        "cookie-value-123",
        "api-key-value-123",
        "body-value-123",
        "response-cookie-123",
    )
    har = {
        "log": {
            "entries": [
                {
                    "request": {
                        "method": "POST",
                        "url": f"https://ex.test/status?token={secrets[0]}",
                        "headers": [
                            {"name": "Authorization", "value": f"Bearer {secrets[1]}"},
                            {"name": "Cookie", "value": f"sid={secrets[2]}"},
                            {"name": "X-Api-Key", "value": secrets[3]},
                            {"name": "Accept", "value": "application/json"},
                        ],
                        "queryString": [{"name": "token", "value": secrets[0]}],
                        "cookies": [{"name": "sid", "value": secrets[2]}],
                        "postData": {
                            "mimeType": "application/json",
                            "text": json.dumps({"access_token": secrets[4]}),
                        },
                    },
                    "response": {
                        "status": 200,
                        "headers": [{"name": "Set-Cookie", "value": secrets[5]}],
                        "content": {"text": json.dumps({"refresh_token": secrets[4]})},
                    },
                }
            ]
        }
    }
    out = ingest(har)
    serialized = json.dumps(out, ensure_ascii=False)
    check(all(secret not in serialized for secret in secrets), "HAR sanitizer retained a secret class")
    request = out["har"]["log"]["entries"][0]["request"]
    check(request["url"] == "https://ex.test/status", "HAR URL query was retained")
    check("[REDACTED]" in serialized, "HAR sanitizer did not leave redaction markers")


def test_mixed_case_name_value_keys_are_redacted_idempotently() -> None:
    secrets = (
        "mixed-header-value",
        "mixed-query-value",
        "mixed-cookie-value",
        "mixed-body-value",
    )
    har = {
        "log": {
            "entries": [
                {
                    "request": {
                        "method": "POST",
                        "url": "https://ex.test/status",
                        "headers": [
                            {"NaMe": "Authorization", "VaLuE": secrets[0]},
                            {"NaMe": "Accept", "VaLuE": "application/json"},
                        ],
                        "queryString": [{"NaMe": "token", "VaLuE": secrets[1]}],
                        "cookies": [{"NaMe": "sid", "VaLuE": secrets[2]}],
                        "postData": {
                            "params": [{"NaMe": "access_token", "VaLuE": secrets[3]}]
                        },
                    },
                    "response": {"status": 200, "headers": []},
                }
            ]
        }
    }
    out = ingest(har)
    sanitized = out["har"]
    serialized = json.dumps(sanitized, ensure_ascii=False)
    mixed_header = sanitized["log"]["entries"][0]["request"]["headers"][0]
    check(all(secret not in serialized for secret in secrets), "mixed-case sanitizer retained a value")
    check("[REDACTED]" in serialized, "mixed-case sanitizer omitted redaction markers")
    check(mixed_header.get("VaLuE") == "[REDACTED]", "mixed-case header was not redacted in place")
    check(
        sanitize_network_document(sanitized) == sanitized,
        "mixed-case sanitizer result is not idempotent",
    )


def test_nonstandard_token_secret_session_headers_are_redacted() -> None:
    secrets = (
        "nonstandard-token-value",
        "nonstandard-secret-value",
        "nonstandard-session-value",
    )
    har = {
        "log": {
            "entries": [
                {
                    "request": {
                        "url": "https://ex.test/status",
                        "headers": [
                            {"NaMe": "X-Custom-ToKeN", "VaLuE": secrets[0]},
                            {"NaMe": "x-Client-SeCrEt", "VaLuE": secrets[1]},
                            {"NaMe": "XTraceSeSsIoNId", "VaLuE": secrets[2]},
                            {"NaMe": "Accept", "VaLuE": "application/json"},
                        ],
                    },
                    "response": {"status": 200, "headers": []},
                }
            ]
        }
    }
    sanitized = ingest(har)["har"]
    headers = sanitized["log"]["entries"][0]["request"]["headers"]
    serialized = json.dumps(sanitized, ensure_ascii=False)
    check(all(secret not in serialized for secret in secrets), "nonstandard header retained a value")
    check(
        [item["VaLuE"] for item in headers[:3]] == ["[REDACTED]"] * 3,
        f"nonstandard headers were not fully redacted: {headers[:3]}",
    )
    check(headers[3]["VaLuE"] == "application/json", "ordinary header value was changed")
    check(
        sanitize_network_document(sanitized) == sanitized,
        "nonstandard header sanitization is not idempotent",
    )


def test_hook_list():
    out = ingest([{"method": "POST", "url": "https://ex.test/talk", "status": 201, "ttfb_ms": 80, "total_ms": 700}])
    check(out["format"] == "simple", out)
    check(out["entries"][0]["path"] == "/talk", out["entries"])
    check(out["entries"][0]["total_ms"] == 700, out["entries"])


def test_orca_wrapped():
    doc = {
        "ok": True,
        "requests": [
            {"method": "GET", "url": "https://cdn.ex.test/app.js", "status": 200, "durationMs": 40},
        ],
    }
    out = ingest(doc)
    check(len(out["entries"]) == 1, out)
    check(out["entries"][0]["host"] == "cdn.ex.test", out["entries"])
    check(out["entries"][0]["total_ms"] == 40, out["entries"])


def test_curl_seconds():
    out = ingest(
        [{"url": "https://ex.test/", "status": 200, "time_starttransfer": 0.12, "time_total": 0.4}]
    )
    row = out["entries"][0]
    check(abs(row["ttfb_ms"] - 120) < 0.01, row)
    check(abs(row["total_ms"] - 400) < 0.01, row)


def test_redact_headers():
    out = ingest(
        [
            {
                "url": "https://ex.test/q",
                "req_headers": [{"name": "Authorization", "value": "Bearer x"}, {"name": "Accept", "value": "*/*"}],
            }
        ]
    )
    names = out["entries"][0]["req_headers"]
    check(names == ["accept"], names)


def test_simple_query_and_string_headers_are_removed() -> None:
    secrets = ("simple-query-123", "simple-auth-123", "simple-body-123")
    out = ingest(
        [
            {
                "url": f"https://ex.test/status?access_token={secrets[0]}",
                "requestHeaders": f"Authorization: Bearer {secrets[1]}\nAccept: application/json",
                "responseHeaders": "Set-Cookie: sid=hidden\nContent-Type: application/json",
                "body": f"token: {secrets[2]}",
            }
        ]
    )
    serialized = json.dumps(out, ensure_ascii=False)
    row = out["entries"][0]
    check(row["url"] == "https://ex.test/status", "simple URL query was retained")
    check(row["req_headers"] == ["accept"], f"simple request headers={row['req_headers']}")
    check(row["res_headers"] == ["content-type"], f"simple response headers={row['res_headers']}")
    check(all(secret not in serialized for secret in secrets), "simple sanitizer retained a secret")


def test_url_userinfo_is_removed_without_breaking_ipv6(tmp: Path) -> None:
    secrets = ("ui-SECRET-000", "name-SECRET-001")
    ingested = ingest(
        [
            {
                "url": f"https://user:{secrets[0]}@ex.test/a",
                "status": 200,
            },
            {
                "url": f"https://{secrets[1]}:{secrets[0]}@[2001:db8::1]:8443/b?token=x#frag",
                "status": 200,
            },
        ]
    )
    urls = [entry["url"] for entry in ingested["entries"]]
    dest = tmp / "userinfo-session.json"
    write_session(ingested, dest)
    serialized = dest.read_text(encoding="utf-8")
    check(
        urls == ["https://ex.test/a", "https://[2001:db8::1]:8443/b"],
        f"URL host, port, or path changed: {urls}",
    )
    check(all(secret not in serialized for secret in secrets), "session retained URL userinfo")
    check(
        sanitize_network_document(ingested) == ingested,
        "URL userinfo sanitization is not idempotent",
    )


def test_write_simple(tmp: Path) -> None:
    secrets = ("write-query-123", "write-auth-123", "write-body-123")
    ingested = {
        "format": "simple",
        "entries": [
            {
                "url": f"https://ex.test/a?token={secrets[0]}",
                "path": "/a",
                "req_headers": f"Authorization: Bearer {secrets[1]}",
                "body": f"secret={secrets[2]}",
            }
        ],
    }
    dest = tmp / "session.json"
    write_session(ingested, dest)
    serialized = dest.read_text(encoding="utf-8")
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    check(isinstance(loaded, list) and loaded[0]["path"] == "/a", loaded)
    check(all(secret not in serialized for secret in secrets), "write_session retained raw values")
    check(loaded[0]["url"] == "https://ex.test/a", "write_session retained a query")


def test_har_response_body_is_fully_redacted(tmp: Path) -> None:
    secret = "base64-response-secret"
    encoded = base64.b64encode(json.dumps({"access_token": secret}).encode()).decode()
    har = {
        "log": {
            "entries": [
                {
                    "request": {"url": "https://ex.test/status", "headers": []},
                    "response": {
                        "status": 200,
                        "headers": [],
                        "content": {
                            "mimeType": "application/json",
                            "encoding": "base64",
                            "text": encoded,
                        },
                    },
                }
            ]
        }
    }
    ingested = ingest(har)
    content = ingested["har"]["log"]["entries"][0]["response"]["content"]
    dest = tmp / "base64-session.json"
    write_session(ingested, dest)
    serialized = dest.read_text(encoding="utf-8")
    check(content["text"] == "[REDACTED]", f"HAR response body was retained: {content}")
    check(content["mimeType"] == "application/json", "HAR response metadata was removed")
    check(encoded not in serialized and secret not in serialized, "encoded response remained in session")
    check(
        sanitize_network_document(ingested["har"]) == ingested["har"],
        "response-body sanitization is not idempotent",
    )


def test_raw_input_must_be_temporary_and_outside_package(tmp: Path) -> None:
    package = tmp / "package"
    inside = package / "raw.json"
    outside = tmp / "capture" / "raw.json"
    out = package / "evidence" / "network" / "session.json"
    inside.parent.mkdir(parents=True)
    outside.parent.mkdir(parents=True)
    payload = json.dumps([{"url": "https://ex.test/status"}])
    inside.write_text(payload, encoding="utf-8")
    outside.write_text(payload, encoding="utf-8")

    with redirect_stdout(StringIO()):
        inside_result = ingest_main([str(inside), "--out", str(out)])
        outside_result = ingest_main([str(outside), "--out", str(out)])
    check(inside_result == 1, "package-local raw input was accepted")
    check(outside_result == 0, "temporary external raw input was rejected")
    check(raw_source_is_temporary(outside), "temporary input was not recognized")
    check(not raw_source_is_temporary(HERE / "not-a-capture.json"), "workspace input was treated as temporary")


def main() -> int:
    test_clean_har_is_detached()
    test_har_five_secret_classes_are_removed()
    test_mixed_case_name_value_keys_are_redacted_idempotently()
    test_nonstandard_token_secret_session_headers_are_redacted()
    test_hook_list()
    test_orca_wrapped()
    test_curl_seconds()
    test_redact_headers()
    test_simple_query_and_string_headers_are_removed()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        test_url_userinfo_is_removed_without_breaking_ipv6(tmp)
        test_write_simple(tmp)
        test_har_response_body_is_fully_redacted(tmp)
        test_raw_input_must_be_temporary_and_outside_package(tmp)
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
