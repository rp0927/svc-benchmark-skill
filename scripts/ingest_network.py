#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize HAR / Orca / Chrome / hook / curl dumps into simple session JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from network_sanitizer import (
    is_sensitive_header,
    raw_source_is_temporary,
    sanitize_network_document,
)


def _unwrap(doc: object) -> object:
    if not isinstance(doc, dict):
        return doc
    for key in ("requests", "entries", "items", "network", "rows", "log"):
        if key == "log" and isinstance(doc.get("log"), dict):
            inner = doc["log"]
            if isinstance(inner.get("entries"), list):
                return doc
        val = doc.get(key)
        if isinstance(val, list):
            return val
    data = doc.get("data")
    if isinstance(data, dict):
        return _unwrap(data)
    if isinstance(data, list):
        return data
    return doc


SEC_KEYS = {"time_starttransfer", "time_total"}


def _as_ms(row: dict, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key not in row or row[key] in (None, ""):
            continue
        try:
            n = float(row[key])
        except (TypeError, ValueError):
            continue
        if key in SEC_KEYS:
            return n * 1000.0
        return n
    return None


def _status(row: dict) -> object:
    for key in ("status", "statusCode", "status_code", "http_code"):
        if key in row and row[key] not in (None, ""):
            try:
                return int(row[key])
            except (TypeError, ValueError):
                return row[key]
    return None


def _url(row: dict) -> str:
    for key in ("url", "href", "uri", "url_effective"):
        val = row.get(key)
        if val:
            return str(val)
    req = row.get("request")
    if isinstance(req, dict) and req.get("url"):
        return str(req["url"])
    return ""


def _method(row: dict) -> str:
    for key in ("method", "httpMethod"):
        if row.get(key):
            return str(row[key]).upper()
    req = row.get("request")
    if isinstance(req, dict) and req.get("method"):
        return str(req["method"]).upper()
    return "GET"


def _headers(row: dict, key: str) -> list[str]:
    raw = row.get(key) or []
    names: list[str] = []
    if isinstance(raw, dict):
        raw = [{"name": k} for k in raw]
    elif isinstance(raw, str):
        raw = raw.splitlines()
    if not isinstance(raw, list):
        return names
    for item in raw:
        if isinstance(item, str):
            name = item.partition(":")[0].strip().lower()
        elif isinstance(item, dict):
            name = str(item.get("name") or item.get("Name") or "").lower()
        else:
            continue
        if name and not is_sensitive_header(name):
            names.append(name)
    return names


def _normalize_row(row: object) -> dict | None:
    if not isinstance(row, dict):
        return None
    if "request" in row and "response" in row:
        # HAR entry — leave to measure_network HAR loader via wrapping
        return None
    url = _url(row)
    if not url and not row.get("host"):
        return None
    parsed = urlparse(url) if url else None
    ttfb = _as_ms(row, ("ttfb_ms", "ttfb", "wait", "time_starttransfer"))
    total = _as_ms(row, ("total_ms", "time", "duration", "durationMs", "duration_ms", "time_total"))
    return {
        "method": _method(row),
        "url": url,
        "host": row.get("host") or (parsed.netloc if parsed else ""),
        "path": row.get("path") or (parsed.path if parsed else "/"),
        "status": _status(row),
        "ttfb_ms": ttfb,
        "total_ms": total,
        "type": row.get("type") or row.get("resourceType") or row.get("resource_type"),
        "req_headers": _headers(row, "req_headers") or _headers(row, "requestHeaders"),
        "res_headers": _headers(row, "res_headers") or _headers(row, "responseHeaders"),
    }


def ingest(doc: object) -> dict:
    doc = sanitize_network_document(doc)
    if isinstance(doc, dict) and isinstance(doc.get("log"), dict) and isinstance(
        doc["log"].get("entries"), list
    ):
        return {"format": "har", "har": doc}
    unwrapped = _unwrap(doc)
    if isinstance(unwrapped, dict) and isinstance(unwrapped.get("log"), dict):
        return {"format": "har", "har": unwrapped}
    rows_in: list = []
    if isinstance(unwrapped, list):
        rows_in = unwrapped
    elif isinstance(unwrapped, dict) and _url(unwrapped):
        rows_in = [unwrapped]
    entries: list[dict] = []
    har_entries = 0
    for row in rows_in:
        if isinstance(row, dict) and "request" in row and "response" in row:
            har_entries += 1
            continue
        norm = _normalize_row(row)
        if norm:
            entries.append(norm)
    if har_entries and not entries and isinstance(doc, dict):
        return {"format": "har", "har": doc}
    return {"format": "simple", "entries": entries}


def write_session(ingested: dict, out: Path) -> None:
    ingested = sanitize_network_document(ingested)
    out.parent.mkdir(parents=True, exist_ok=True)
    if ingested["format"] == "har":
        out.write_text(json.dumps(ingested["har"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    out.write_text(json.dumps(ingested["entries"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def package_root_for_output(out: Path) -> Path | None:
    parent = out.resolve().parent
    for candidate in (parent, *parent.parents):
        if candidate.name == "network" and candidate.parent.name == "evidence":
            return candidate.parent.parent
    return None


def raw_source_inside_package(src: Path, out: Path) -> bool:
    package_root = package_root_for_output(out)
    if package_root is None:
        return False
    try:
        src.resolve().relative_to(package_root.resolve())
        return True
    except ValueError:
        return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("src", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    if not raw_source_is_temporary(args.src):
        print("FAIL: raw network input must be under a temporary directory")
        return 1
    if raw_source_inside_package(args.src, args.out):
        print("FAIL: raw network input must be outside the package")
        return 1
    try:
        doc = json.loads(args.src.read_text(encoding="utf-8"))
        ingested = ingest(doc)
        write_session(ingested, args.out)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    n = (
        len(ingested["har"].get("log", {}).get("entries", []))
        if ingested["format"] == "har"
        else len(ingested["entries"])
    )
    print(f"{ingested['format']} {n} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
