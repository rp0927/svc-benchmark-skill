#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed JTBD / SWOT / segment notes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validate_report import extract_section, parse_frontmatter

SCANS = {"product", "landscape"}
PHASES = {"jtbd", "segments", "close"}
CUSTOMER = {"customer", "proxy-shallow", "none"}
QUESTION = {"landscape", "need-vs-price"}
DEPTH = {"shallow", "deep"}
ROLES = {"competitor", "alternative", "out"}
SWOT_KEYS = ("strength", "weakness", "opportunity", "threat")
SWOT_LABELS = ("강점", "약점", "기회", "위협")
KNOWN_FAILURES = (
    "sitemap-behind-login",
    "static-empty-widget",
    "agent-self-report",
    "raw-network-in-package",
    "price-from-shallow-scan",
    "map-before-job",
    "fleet-before-segments",
    "improvise-without-skill",
    "persona-trial-as-mutation",
    "private-code-as-source",
    "packet-from-raw-har",
    "official-from-snippet",
    "last30days-as-official",
)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _scan_of(root: Path, report: str) -> str:
    run_path = root / "run.json"
    if run_path.is_file():
        try:
            data = _load_json(run_path)
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict):
            scan = _text(data.get("scan"))
            if scan in SCANS:
                return scan
    fm = parse_frontmatter(report) if report else None
    if fm and fm.get("report_profile") == "landscape":
        return "landscape"
    return "product"


def _hypothesis_ok(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    return bool(_text(item.get("claim")))


def _actor_errors(actors: object) -> list[str]:
    if not isinstance(actors, list):
        return ["jtbd.actors must be a list"]
    errors: list[str] = []
    for index, item in enumerate(actors):
        if not isinstance(item, dict):
            errors.append(f"jtbd.actors[{index}] is not an object")
            continue
        if not _text(item.get("name")):
            errors.append(f"jtbd.actors[{index}].name missing")
        role = _text(item.get("role"))
        if role and role not in ROLES:
            errors.append(f"jtbd.actors[{index}].role unknown: {role}")
    return errors


def _segment_errors(raw: object) -> list[str]:
    if not isinstance(raw, dict):
        return ["segments.json must be an object"]
    segments = raw.get("segments")
    if not isinstance(segments, list):
        return ["segments.segments must be a list"]
    if not segments:
        return ["landscape needs at least one segment"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(segments):
        if not isinstance(item, dict):
            errors.append(f"segments[{index}] is not an object")
            continue
        sid = _text(item.get("id"))
        if not sid:
            errors.append(f"segments[{index}].id missing")
        elif sid in seen:
            errors.append(f"duplicate segment id: {sid}")
        else:
            seen.add(sid)
        if not _text(item.get("name")):
            errors.append(f"segments[{index}].name missing")
        depth = _text(item.get("depth"))
        if depth and depth not in DEPTH:
            errors.append(f"segments[{index}].depth unknown: {depth}")
    return errors


def validate_jtbd(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["jtbd.json must be an object"]
    errors: list[str] = []
    if not _text(data.get("job")):
        errors.append("jtbd.job missing")
    evidence = _text(data.get("customer_evidence")) or "none"
    if evidence not in CUSTOMER:
        errors.append(f"jtbd.customer_evidence unknown: {evidence}")
    question = _text(data.get("question"))
    if question and question not in QUESTION:
        errors.append(f"jtbd.question unknown: {question}")
    depth = _text(data.get("depth"))
    if depth and depth not in DEPTH:
        errors.append(f"jtbd.depth unknown: {depth}")
    hyps = data.get("hypotheses")
    if hyps is None:
        hyps = []
    if not isinstance(hyps, list):
        errors.append("jtbd.hypotheses must be a list")
        hyps = []
    if evidence in {"none", "proxy-shallow"} and not any(_hypothesis_ok(item) for item in hyps):
        errors.append("jtbd.hypotheses required when customers are absent")
    errors.extend(_actor_errors(data.get("actors") or []))
    return errors


def validate_swot(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["swot.json must be an object"]
    errors: list[str] = []
    if not _text(data.get("job")):
        errors.append("swot.job missing")
    for key in SWOT_KEYS:
        if not _text(data.get(key)):
            errors.append(f"swot.{key} missing")
    return errors


def _fleet_notes(root: Path) -> list[Path]:
    folder = root / "notes" / "segments"
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.iterdir() if path.is_file() and path.suffix == ".md")


def _job_text(data: object) -> str:
    if not isinstance(data, dict):
        return ""
    return _text(data.get("job"))


def validate_failures(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["failures.json must be an object"]
    errors: list[str] = []
    catalog = data.get("catalog")
    if catalog is not None:
        if not isinstance(catalog, list):
            errors.append("failures.catalog must be a list")
        else:
            for index, item in enumerate(catalog):
                name = _text(item)
                if name not in KNOWN_FAILURES:
                    errors.append(f"failures.catalog[{index}] unknown: {item}")
    events = data.get("events")
    if events is None:
        events = []
    if not isinstance(events, list):
        return errors + ["failures.events must be a list"]
    for index, item in enumerate(events):
        if not isinstance(item, dict):
            errors.append(f"failures.events[{index}] is not an object")
            continue
        fid = _text(item.get("id"))
        if not fid:
            errors.append(f"failures.events[{index}].id missing")
        elif fid not in KNOWN_FAILURES:
            errors.append(f"failures.events[{index}].id unknown: {fid}")
    return errors


def validate_report_swot(text: str, profile: str) -> list[str]:
    if not text:
        return []
    if profile == "landscape":
        body = extract_section(text, "SWOT")
        label = "SWOT"
    elif profile == "planning-analysis":
        body = extract_section(text, "9. SWOT")
        label = "9. SWOT"
    else:
        body = extract_section(text, "인사이트")
        label = "인사이트"
    if not body:
        return []
    missing = [name for name in SWOT_LABELS if name not in body]
    if missing:
        return [f"{label}: missing SWOT labels: {', '.join(missing)}"]
    return []


def validate_scan(root: Path, phase: str = "close") -> list[str]:
    if phase not in PHASES:
        return [f"unknown phase: {phase}"]
    errors: list[str] = []
    report_path = root / "report" / "report.md"
    report = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
    fm = parse_frontmatter(report) if report else None
    profile = (fm or {}).get("report_profile") or "benchmark"
    scan = _scan_of(root, report)

    jtbd_path = root / "notes" / "jtbd.json"
    jtbd_data: object | None = None
    if not jtbd_path.is_file():
        errors.append("notes/jtbd.json missing")
    else:
        try:
            jtbd_data = _load_json(jtbd_path)
            errors.extend(validate_jtbd(jtbd_data))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"notes/jtbd.json: {exc}")

    sitemap = root / "notes" / "sitemap.md"
    if sitemap.is_file() and not _job_text(jtbd_data):
        errors.append("map-before-job: notes/sitemap.md exists without jtbd.job")

    need_segments = phase in {"segments", "close"} and scan == "landscape"
    seg_path = root / "notes" / "segments.json"
    if need_segments:
        if not seg_path.is_file():
            errors.append("notes/segments.json missing")
        else:
            try:
                errors.extend(_segment_errors(_load_json(seg_path)))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"notes/segments.json: {exc}")

    if _fleet_notes(root):
        if not seg_path.is_file():
            fleet_blocked = True
        else:
            try:
                fleet_blocked = bool(_segment_errors(_load_json(seg_path)))
            except (OSError, json.JSONDecodeError):
                fleet_blocked = True
        if fleet_blocked:
            errors.append(
                "fleet-before-segments: notes/segments/*.md exists without a filled segments.json"
            )

    if phase == "close":
        swot_path = root / "notes" / "swot.json"
        if not swot_path.is_file():
            errors.append("notes/swot.json missing")
        else:
            try:
                errors.extend(validate_swot(_load_json(swot_path)))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"notes/swot.json: {exc}")
        errors.extend(validate_report_swot(report, profile))
        fail_path = root / "notes" / "failures.json"
        if fail_path.is_file():
            try:
                errors.extend(validate_failures(_load_json(fail_path)))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"notes/failures.json: {exc}")
    return errors


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--phase", choices=sorted(PHASES), default="close")
    args = p.parse_args(argv)
    root = args.root
    if not root.is_dir():
        print(f"FAIL: not a directory: {root}")
        return 1
    errors = validate_scan(root, phase=args.phase)
    if errors:
        print("FAIL")
        for item in errors:
            print(f"- {item}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
