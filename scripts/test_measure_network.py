#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""measure_network: HAR + simple JSON, secret headers dropped, timings kept."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import sys
import tempfile
from unittest.mock import patch
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from measure_network import (  # noqa: E402
    load_entries,
    main as measure_main,
    percentile_nearest_rank,
    redact_headers,
    render_md,
    summarize,
)

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def test_redact():
    names = redact_headers(
        [
            {"name": "Content-Type", "value": "application/json"},
            {"name": "Authorization", "value": "Bearer SECRET"},
            {"name": "cookie", "value": "sid=1"},
        ]
    )
    check(names == ["content-type"], f"redact={names}")


def test_simple_json():
    rows = [
        {
            "method": "POST",
            "url": "https://api.ex.test/talk/send",
            "status": 200,
            "ttfb_ms": 120,
            "total_ms": 740,
            "req_headers": ["content-type", "authorization"],
        },
        {
            "method": "GET",
            "url": "https://cdn.ex.test/app.js",
            "status": 200,
            "ttfb_ms": 40,
            "total_ms": 90,
        },
    ]
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "t.json"
        path.write_text(json.dumps(rows), encoding="utf-8")
        entries = load_entries(path)
    check(len(entries) == 2, f"n={len(entries)}")
    check(entries[0]["host"] == "api.ex.test", entries[0])
    check("authorization" not in entries[0]["req_headers"], entries[0]["req_headers"])
    s = summarize(entries)
    check(s["count"] == 2, s)
    check(s["total_ms"]["median"] == 415, s["total_ms"])
    check(s["total_ms"]["p90"] == 740, s["total_ms"])
    check(s["slowest"][0]["url"].endswith("/talk/send"), s["slowest"])


def test_p90_two_samples_is_not_the_min():
    # Regression: int(n*0.9)-1 picked index 0 for n=2, so p90 < median.
    check(percentile_nearest_rank([104.82, 277.108], 90) == 277.108, "n=2 p90")
    check(percentile_nearest_rank([90, 740], 90) == 740, "n=2 p90 fixture")
    check(percentile_nearest_rank([10], 90) == 10, "n=1 p90")
    check(percentile_nearest_rank([], 90) is None, "empty p90")
    s = summarize(
        [
            {"method": "GET", "url": "https://a.test/", "host": "a.test", "path": "/", "status": 200, "ttfb_ms": 241.23, "total_ms": 277.108},
            {"method": "GET", "url": "https://b.test/", "host": "b.test", "path": "/", "status": 200, "ttfb_ms": 70.305, "total_ms": 104.82},
        ]
    )
    check(s["total_ms"]["median"] == 190.964, s["total_ms"])
    check(s["total_ms"]["p90"] == 277.108, s["total_ms"])
    check(s["total_ms"]["p90"] >= s["total_ms"]["median"], "p90 must be >= median")


def test_har_shape():
    har = {
        "log": {
            "entries": [
                {
                    "time": 210,
                    "timings": {"wait": 80},
                    "request": {
                        "method": "GET",
                        "url": "https://ex.test/pricing",
                        "headers": [{"name": "Cookie", "value": "a=1"}],
                    },
                    "response": {"status": 200, "headers": [], "content": {"mimeType": "text/html"}},
                }
            ]
        }
    }
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "t.har"
        path.write_text(json.dumps(har), encoding="utf-8")
        entries = load_entries(path)
    check(entries[0]["ttfb_ms"] == 80, entries)
    check(entries[0]["total_ms"] == 210, entries)
    check("cookie" not in entries[0]["req_headers"], entries[0]["req_headers"])


def test_har_query_and_sensitive_header_values_do_not_reach_summary() -> None:
    secrets = ("har-query-123", "har-auth-123", "har-cookie-123")
    har = {
        "log": {
            "entries": [
                {
                    "time": 50,
                    "timings": {"wait": 20},
                    "request": {
                        "method": "GET",
                        "url": f"https://ex.test/status?token={secrets[0]}",
                        "headers": [
                            {"name": "Authorization", "value": secrets[1]},
                            {"name": "Accept", "value": "application/json"},
                        ],
                    },
                    "response": {
                        "status": 200,
                        "headers": [{"name": "Set-Cookie", "value": secrets[2]}],
                    },
                }
            ]
        }
    }
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "t.har"
        path.write_text(json.dumps(har), encoding="utf-8")
        summary = summarize(load_entries(path))
    serialized = json.dumps(summary, ensure_ascii=False)
    check(all(secret not in serialized for secret in secrets), "HAR summary retained a secret")
    check(summary["entries"][0]["url"] == "https://ex.test/status", "HAR summary retained a query")
    check(summary["entries"][0]["req_headers"] == ["accept"], "HAR summary retained a sensitive header")


def test_simple_multiline_headers_and_query_are_removed() -> None:
    secrets = ("simple-query-123", "simple-auth-123", "simple-cookie-123")
    rows = [
        {
            "url": f"https://ex.test/status?api_key={secrets[0]}",
            "req_headers": f"Authorization: Bearer {secrets[1]}\nAccept: application/json",
            "res_headers": f"Set-Cookie: sid={secrets[2]}\nContent-Type: application/json",
            "total_ms": 10,
        }
    ]
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "t.json"
        path.write_text(json.dumps(rows), encoding="utf-8")
        entries = load_entries(path)
    serialized = json.dumps(entries, ensure_ascii=False)
    check(all(secret not in serialized for secret in secrets), "simple measurement retained a secret")
    check(entries[0]["url"] == "https://ex.test/status", "simple measurement retained a query")
    check(entries[0]["req_headers"] == ["accept"], f"request headers={entries[0]['req_headers']}")
    check(entries[0]["res_headers"] == ["content-type"], f"response headers={entries[0]['res_headers']}")


def test_measure_cli_rejects_non_temporary_raw_but_accepts_session() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        raw = root / "raw.json"
        session = root / "session.json"
        output = root / "runtime.md"
        raw.write_text(
            json.dumps([{"url": "https://ex.test/status?token=raw-value-123"}]),
            encoding="utf-8",
        )
        session.write_text(
            json.dumps([{"url": "https://ex.test/status", "req_headers": []}]),
            encoding="utf-8",
        )
        with patch("measure_network.raw_source_is_temporary", return_value=False):
            with redirect_stdout(StringIO()):
                raw_result = measure_main(["--har", str(raw), "--out", str(output)])
                session_result = measure_main(["--har", str(session), "--out", str(output)])
        check(raw_result == 1, "measure CLI accepted non-temporary raw input")
        check(session_result == 0, "measure CLI rejected a sanitized session")


def test_empty():
    s = summarize([])
    check(s["count"] == 0 and s["total_ms"]["median"] is None, s)


def test_render_does_not_force_model_none():
    md = render_md(summarize([]))
    check("해당 없음" not in md, "must not overwrite model section")
    check("모델·라우팅 소절은 이 파일이 쓰지 않는다" in md, md)


def main() -> int:
    test_redact()
    test_simple_json()
    test_p90_two_samples_is_not_the_min()
    test_har_shape()
    test_har_query_and_sensitive_header_values_do_not_reach_summary()
    test_simple_multiline_headers_and_query_are_removed()
    test_measure_cli_rejects_non_temporary_raw_but_accepts_session()
    test_empty()
    test_render_does_not_force_model_none()
    if FAILURES:
        print("FAIL")
        for f in FAILURES:
            print("-", f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
