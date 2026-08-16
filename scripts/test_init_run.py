#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_run creates dirs/layout/templates and keeps existing files."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from init_run import DIRS, LAYOUT, init_run  # noqa: E402
from validate_scan import KNOWN_FAILURES  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def _schema_sources(doc: dict) -> None:
    check(isinstance(doc.get("as_of"), str) and doc["as_of"], "sources.as_of")
    for key in ("primary", "secondary", "cited", "excluded"):
        check(isinstance(doc.get(key), list), f"sources.{key}")


def _schema_privacy(doc: dict) -> None:
    check(isinstance(doc.get("as_of"), str) and doc["as_of"], "privacy.as_of")
    for key in ("html", "allowed_emails", "forbidden_paths", "redactions"):
        check(isinstance(doc.get(key), list), f"privacy.{key}")


def _schema_manifest(doc: dict) -> None:
    check(doc.get("doc") == "report/report.md", f"manifest.doc {doc.get('doc')}")
    check(isinstance(doc.get("as_of"), str) and doc["as_of"], "manifest.as_of")
    check(isinstance(doc.get("core_required"), list), "manifest.core_required")
    check(isinstance(doc.get("claims"), list), "manifest.claims")


def test_dirs_layout_templates() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "20260814_example"
        payload = init_run(out, target="https://ex.test", depth="public", type_name="web-saas")
        check(payload["mutations_allowed"] == [], f"mutations {payload['mutations_allowed']}")
        check(payload.get("scan") == "product", f"scan {payload.get('scan')}")
        check((out / "run.json").is_file(), "run.json missing")
        for rel in DIRS:
            check((out / rel).is_dir(), f"missing {rel}")
        data = json.loads((out / "run.json").read_text(encoding="utf-8"))
        check(data["layout"] == LAYOUT, f"layout {data['layout']}")
        check(data.get("scan") == "product", f"run.scan {data.get('scan')}")
        jtbd = json.loads((out / "notes/jtbd.json").read_text(encoding="utf-8"))
        swot = json.loads((out / "notes/swot.json").read_text(encoding="utf-8"))
        segs = json.loads((out / "notes/segments.json").read_text(encoding="utf-8"))
        fails = json.loads((out / "notes/failures.json").read_text(encoding="utf-8"))
        check(jtbd.get("question") == "need-vs-price", f"jtbd.question {jtbd.get('question')}")
        check(isinstance(swot.get("strength"), str), "swot.strength")
        check(segs.get("segments") == [], f"segments {segs}")
        check(fails.get("catalog") == list(KNOWN_FAILURES), f"failures.catalog {fails.get('catalog')}")
        check(fails.get("events") == [], f"failures.events {fails.get('events')}")
        check(isinstance(fails.get("preflight"), dict), "failures.preflight")
        precheck = json.loads((out / "notes/precheck.json").read_text(encoding="utf-8"))
        check(precheck.get("reuse") == "none", f"precheck.reuse {precheck.get('reuse')}")
        check(isinstance(precheck.get("existing_runs"), list), "precheck.existing_runs")
        sources = json.loads((out / "notes/sources.json").read_text(encoding="utf-8"))
        privacy = json.loads((out / "notes/privacy-exceptions.json").read_text(encoding="utf-8"))
        manifest = json.loads((out / "sources/audit-manifest.json").read_text(encoding="utf-8"))
        fact = json.loads((out / "sources/audit-fact.json").read_text(encoding="utf-8"))
        visual = json.loads((out / "sources/audit-visual.json").read_text(encoding="utf-8"))
        _schema_sources(sources)
        _schema_privacy(privacy)
        _schema_manifest(manifest)
        check(fact.get("items") == [], f"fact {fact}")
        check(visual.get("items") == [], f"visual {visual}")


def test_preserves_existing() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "20260814_example"
        init_run(out, target="https://ex.test")
        marker = {"as_of": "keep-me", "primary": ["https://kept.test"], "secondary": [], "cited": [], "excluded": []}
        (out / "notes/sources.json").write_text(json.dumps(marker), encoding="utf-8")
        fact_keep = {"items": [{"claim_id": "keep", "verdict": "match", "observed": "x"}]}
        (out / "sources/audit-fact.json").write_text(json.dumps(fact_keep), encoding="utf-8")
        init_run(out, target="https://other.test")
        sources = json.loads((out / "notes/sources.json").read_text(encoding="utf-8"))
        fact = json.loads((out / "sources/audit-fact.json").read_text(encoding="utf-8"))
        check(sources == marker, f"sources overwritten: {sources}")
        check(fact == fact_keep, f"fact overwritten: {fact}")


def test_landscape_scan() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "20260816_landscape"
        payload = init_run(out, target="코딩 에이전트 고용", scan="landscape")
        check(payload["scan"] == "landscape", f"payload scan {payload['scan']}")
        jtbd = json.loads((out / "notes/jtbd.json").read_text(encoding="utf-8"))
        check(jtbd.get("question") == "landscape", f"landscape question {jtbd.get('question')}")
        check(jtbd.get("depth") == "shallow", f"landscape depth {jtbd.get('depth')}")
        try:
            init_run(out, target="x", scan="wide")
            check(False, "invalid scan did not raise")
        except ValueError as exc:
            check("unknown scan" in str(exc), f"invalid scan {exc}")


def main() -> int:
    test_dirs_layout_templates()
    test_preserves_existing()
    test_landscape_scan()
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
