#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create the svc-benchmark run folder before any collection."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from validate_scan import KNOWN_FAILURES

DIRS = (
    "report",
    "notes",
    "notes/segments",
    "sources",
    "review",
    "evidence/screenshots",
    "evidence/cli",
    "evidence/queries",
    "evidence/network",
    "evidence/docs",
)
SCANS = ("product", "landscape")
LAYOUT = ["report", "notes", "sources", "review", "evidence"]


def _templates(as_of: str, *, scan: str) -> dict[str, dict]:
    question = "landscape" if scan == "landscape" else "need-vs-price"
    depth = "shallow" if scan == "landscape" else "deep"
    return {
        "notes/jtbd.json": {
            "job": "",
            "pain": "",
            "hired_solutions": [],
            "customer_evidence": "none",
            "hypotheses": [],
            "question": question,
            "depth": depth,
            "actors": [],
        },
        "notes/swot.json": {
            "subject": "",
            "job": "",
            "strength": "",
            "weakness": "",
            "opportunity": "",
            "threat": "",
        },
        "notes/segments.json": {"segments": []},
        "notes/precheck.json": {
            "existing_runs": [],
            "local_research": [],
            "reuse": "none",
        },
        "notes/failures.json": {
            "catalog": list(KNOWN_FAILURES),
            "preflight": {
                "as_of": as_of,
                "browser": "",
                "collector": "",
                "ok": None,
            },
            "events": [],
        },
        "notes/packets.json": {
            "as_of": as_of,
            "method": "none",
            "missing_reason": "",
            "flows": [],
        },
        "notes/code-surface.json": {
            "as_of": as_of,
            "missing_reason": "",
            "public_repo": "",
            "entrypoints": [],
            "client_bundles": [],
            "cli_bins": [],
            "observed": "none",
            "notes": "",
        },
        "notes/impl-methods.json": {
            "as_of": as_of,
            "missing_reason": "",
            "hosting": "",
            "auth": "",
            "data_path": "",
            "model_routing": "",
            "billing_unit": "",
            "evidence": [],
        },
        "notes/perf.json": {
            "as_of": as_of,
            "missing_reason": "",
            "home_ttfb_ms": None,
            "home_total_ms": None,
            "api_median_ms": None,
            "stream_first_byte_ms": None,
            "stream_end_ms": None,
            "characteristics": [],
            "evidence": [],
        },
        "notes/persona-trials.json": {
            "as_of": as_of,
            "mode": "none",
            "missing_reason": "",
            "trials": [],
        },
        "notes/sources.json": {
            "as_of": as_of,
            "primary": [],
            "secondary": [],
            "cited": [],
            "excluded": [],
        },
        "notes/privacy-exceptions.json": {
            "as_of": as_of,
            "html": [],
            "allowed_emails": [],
            "forbidden_paths": [],
            "redactions": [],
        },
        "sources/audit-manifest.json": {
            "doc": "report/report.md",
            "as_of": as_of,
            "core_required": [],
            "claims": [],
        },
        "sources/audit-fact.json": {"items": []},
        "sources/audit-visual.json": {"items": []},
    }


def _write_if_absent(path: Path, payload: dict) -> None:
    if path.exists():
        return
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def init_run(
    out: Path,
    *,
    target: str,
    depth: str = "public",
    type_name: str = "auto",
    scan: str = "product",
    prev_run: Path | None = None,
    as_of: str | None = None,
) -> dict:
    if scan not in SCANS:
        raise ValueError(f"unknown scan: {scan}")
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for rel in DIRS:
        (out / rel).mkdir(parents=True, exist_ok=True)
    stamp = as_of or date.today().isoformat()
    for rel, body in _templates(stamp, scan=scan).items():
        _write_if_absent(out / rel, body)
    payload = {
        "as_of": stamp,
        "target": target,
        "scan": scan,
        "depth": depth,
        "type": type_name,
        "prev_run": str(prev_run.resolve()) if prev_run else None,
        "mutations_allowed": [],
        "layout": list(LAYOUT),
    }
    (out / "run.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--depth", default="public")
    p.add_argument("--type", dest="type_name", default="auto")
    p.add_argument("--scan", choices=SCANS, default="product")
    p.add_argument("--prev-run")
    args = p.parse_args(argv)
    prev = Path(args.prev_run) if args.prev_run else None
    init_run(
        Path(args.out),
        target=args.target,
        depth=args.depth,
        type_name=args.type_name,
        scan=args.scan,
        prev_run=prev,
    )
    print(Path(args.out).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
