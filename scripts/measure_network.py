#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize HAR or timing JSON. Strip secrets. Report hosts, paths, status, ms."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from urllib.parse import urlparse

from network_sanitizer import (
    contains_unsanitized_network_data,
    header_name,
    is_sensitive_header,
    raw_source_is_temporary,
    sanitize_network_document,
    sanitize_url,
)


def _header_name(item: object) -> str:
    return header_name(item)


def redact_headers(headers: object) -> list[str]:
    names: list[str] = []
    if isinstance(headers, dict):
        headers = [{"name": name} for name in headers]
    elif isinstance(headers, str):
        headers = headers.splitlines()
    if not isinstance(headers, list):
        return names
    for item in headers:
        name = _header_name(item)
        if name and not is_sensitive_header(name):
            names.append(name)
    return names


def _ms(value: object) -> float | None:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n


def entries_from_har(doc: dict) -> list[dict]:
    doc = sanitize_network_document(doc)
    if not isinstance(doc, dict):
        return []
    log = doc.get("log") if isinstance(doc.get("log"), dict) else doc
    raw = log.get("entries") if isinstance(log, dict) else None
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for ent in raw:
        if not isinstance(ent, dict):
            continue
        req = ent.get("request") if isinstance(ent.get("request"), dict) else {}
        res = ent.get("response") if isinstance(ent.get("response"), dict) else {}
        timings = ent.get("timings") if isinstance(ent.get("timings"), dict) else {}
        url = str(sanitize_url(req.get("url") or ""))
        parsed = urlparse(url)
        wait = _ms(timings.get("wait"))
        total = _ms(ent.get("time"))
        out.append(
            {
                "method": str(req.get("method") or "GET"),
                "url": f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                "host": parsed.netloc,
                "path": parsed.path or "/",
                "status": res.get("status"),
                "ttfb_ms": wait,
                "total_ms": total,
                "type": (ent.get("_resourceType") or res.get("content", {}).get("mimeType")
                         if isinstance(res.get("content"), dict) else None),
                "req_headers": redact_headers(req.get("headers")),
                "res_headers": redact_headers(res.get("headers")),
            }
        )
    return out


def entries_from_simple(doc: object) -> list[dict]:
    doc = sanitize_network_document(doc)
    rows = doc if isinstance(doc, list) else (doc.get("entries") if isinstance(doc, dict) else None)
    if not isinstance(rows, list):
        return []
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = str(sanitize_url(row.get("url") or ""))
        parsed = urlparse(url) if url else None
        host = row.get("host") or (parsed.netloc if parsed else "")
        path = row.get("path") or (parsed.path if parsed else "/")
        out.append(
            {
                "method": str(row.get("method") or "GET"),
                "url": url or f"{host}{path}",
                "host": host,
                "path": path or "/",
                "status": row.get("status"),
                "ttfb_ms": _ms(row.get("ttfb_ms") if "ttfb_ms" in row else row.get("ttfb")),
                "total_ms": _ms(row.get("total_ms") if "total_ms" in row else row.get("time")),
                "type": row.get("type"),
                "req_headers": redact_headers(row.get("req_headers")),
                "res_headers": redact_headers(row.get("res_headers")),
            }
        )
    return out


def percentile_nearest_rank(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile. p in 0–100. p90 of 2 samples is the larger one."""
    if not values:
        return None
    xs = sorted(values)
    n = len(xs)
    if n == 1 or p <= 0:
        return xs[0]
    if p >= 100:
        return xs[-1]
    rank = max(1, math.ceil((p / 100.0) * n))
    return xs[min(rank, n) - 1]


def load_entries(path: Path) -> list[dict]:
    doc = sanitize_network_document(json.loads(path.read_text(encoding="utf-8")))
    if isinstance(doc, dict) and (doc.get("log") or "entries" in doc and isinstance(doc.get("entries"), list)
                                  and doc.get("entries") and isinstance(doc["entries"][0], dict)
                                  and "request" in doc["entries"][0]):
        return entries_from_har(doc)
    if isinstance(doc, dict) and isinstance(doc.get("log"), dict):
        return entries_from_har(doc)
    return entries_from_simple(doc)


def summarize(entries: list[dict]) -> dict:
    entries = entries_from_simple(entries)
    totals = [e["total_ms"] for e in entries if e.get("total_ms") is not None]
    ttfbs = [e["ttfb_ms"] for e in entries if e.get("ttfb_ms") is not None]
    hosts: dict[str, int] = {}
    paths: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for e in entries:
        hosts[e["host"] or "(none)"] = hosts.get(e["host"] or "(none)", 0) + 1
        key = f"{e['method']} {e['path']}"
        paths[key] = paths.get(key, 0) + 1
        st = str(e.get("status") if e.get("status") is not None else "?")
        statuses[st] = statuses.get(st, 0) + 1
    slow = sorted(
        [e for e in entries if e.get("total_ms") is not None],
        key=lambda e: e["total_ms"] or 0,
        reverse=True,
    )[:5]
    return {
        "count": len(entries),
        "hosts": hosts,
        "paths": paths,
        "statuses": statuses,
        "total_ms": {
            "n": len(totals),
            "median": statistics.median(totals) if totals else None,
            "p90": percentile_nearest_rank(totals, 90),
            "max": max(totals) if totals else None,
        },
        "ttfb_ms": {
            "n": len(ttfbs),
            "median": statistics.median(ttfbs) if ttfbs else None,
            "max": max(ttfbs) if ttfbs else None,
        },
        "slowest": [
            {"method": e["method"], "url": e["url"], "status": e.get("status"), "total_ms": e.get("total_ms")}
            for e in slow
        ],
        "entries": entries,
    }


def render_md(summary: dict) -> str:
    lines = ["# 런타임 실측", ""]
    if summary["count"] == 0:
        lines.append("관측된 호출 없음.")
        lines.append("")
        lines.append("모델·라우팅 소절은 이 파일이 쓰지 않는다. `widget-llm`/`cli-agent`는 에이전트가 `notes/runtime.md`에 이어 붙인다.")
        lines.append("")
        return "\n".join(lines)
    t = summary["total_ms"]
    f = summary["ttfb_ms"]
    lines.append(f"호출 {summary['count']}건.")
    if t["median"] is not None:
        lines.append(
            f"왕복 중앙값 {t['median']:.0f} ms, p90 {t['p90']:.0f} ms, 최대 {t['max']:.0f} ms."
        )
    if f["median"] is not None:
        lines.append(f"TTFB 중앙값 {f['median']:.0f} ms, 최대 {f['max']:.0f} ms.")
    lines.append("")
    lines.append("## 호스트")
    lines.append("")
    for host, n in sorted(summary["hosts"].items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- `{host}` — {n}건")
    lines.append("")
    lines.append("## 경로")
    lines.append("")
    for path, n in sorted(summary["paths"].items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- `{path}` — {n}건")
    lines.append("")
    lines.append("## 상태")
    lines.append("")
    for st, n in sorted(summary["statuses"].items()):
        lines.append(f"- {st}: {n}")
    lines.append("")
    if summary["slowest"]:
        lines.append("## 느린 호출")
        lines.append("")
        lines.append("| 메서드 | URL | 상태 | ms |")
        lines.append("|---|---|---:|---:|")
        for e in summary["slowest"]:
            lines.append(f"| {e['method']} | `{e['url']}` | {e['status']} | {e['total_ms']:.0f} |")
        lines.append("")
    lines.append("쿠키·Authorization 값은 저장하지 않았다.")
    lines.append("")
    lines.append("모델·라우팅 소절은 이 파일이 쓰지 않는다. `widget-llm`/`cli-agent`는 에이전트가 `notes/runtime.md`에 이어 붙인다.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--har", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--json", dest="json_out", type=Path)
    args = p.parse_args(argv)
    source_doc = json.loads(args.har.read_text(encoding="utf-8"))
    if contains_unsanitized_network_data(source_doc) and not raw_source_is_temporary(args.har):
        print("FAIL: unsanitized network input must be under a temporary directory")
        return 1
    entries = load_entries(args.har)
    summary = summarize(entries)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_md(summary), encoding="utf-8")
    if args.json_out:
        dump = dict(summary)
        # keep entries in json for later, already redacted
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(dump, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
