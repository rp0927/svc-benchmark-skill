#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed PII and exception-registry audit for a benchmark package."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from network_sanitizer import contains_unsanitized_network_data

EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
SCAN_EXT = {".txt", ".json", ".md", ".csv"}
NETWORK_EXT = {".json", ".jsonl", ".har", ".log", ".txt"}
FORBIDDEN_NETWORK_NAMES = {"raw.json", "hook.json"}
PUBLISHED_HTML_DIRS = {"report", "review", "notes", "sources"}
SKIP_DIR = {"copyedit-runs", ".git"}
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
REQUIRED_EXCEPTION_KEYS = ("html", "allowed_emails", "forbidden_paths", "redactions")


def load_exceptions(root: Path) -> dict:
    path = root / "notes" / "privacy-exceptions.json"
    if not path.exists():
        raise ValueError("privacy exceptions ledger missing")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("privacy exceptions root must be an object")
    missing = [key for key in REQUIRED_EXCEPTION_KEYS if key not in doc]
    if missing:
        raise ValueError("privacy exceptions missing required keys: " + ", ".join(missing))
    return doc


def allowed_email(addr: str, exact: set[str] | None = None) -> bool:
    return addr.lower() in (exact or set())


def iter_scan_files(root: Path) -> list[Path]:
    out: set[Path] = set()
    for name in ("report", "notes", "review", "sources", "evidence"):
        base = root / name
        if not base.exists():
            continue
        extensions = SCAN_EXT | ({".html"} if name in PUBLISHED_HTML_DIRS else set())
        for path in base.rglob("*"):
            rel_parts = path.relative_to(root).parts
            is_network = len(rel_parts) >= 2 and rel_parts[:2] == ("evidence", "network")
            allowed_extension = path.suffix.lower() in extensions or (
                is_network and path.suffix.lower() in NETWORK_EXT
            )
            if path.is_file() and allowed_extension:
                if not any(part in SKIP_DIR for part in path.relative_to(root).parts):
                    out.add(path)
    for path in root.glob("*"):
        if path.is_file() and path.suffix.lower() in SCAN_EXT:
            out.add(path)
    return sorted(out)


def _safe_path(root: Path, value: object, *, inside: Path | None = None) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    rel = Path(value)
    if rel.is_absolute():
        return None
    try:
        base = root.resolve()
        resolved = (base / rel).resolve()
        resolved.relative_to(base)
        if inside is not None:
            resolved.relative_to(inside.resolve())
        return resolved
    except (OSError, ValueError):
        return None


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def html_exception_errors(root: Path, exceptions: dict | None = None) -> list[str]:
    errors: list[str] = []
    docs = root / "evidence" / "docs"
    actual = {
        _relative(root, path.resolve())
        for path in docs.rglob("*")
        if path.is_file() and path.suffix.lower() == ".html"
    } if docs.exists() else set()
    exceptions = exceptions if exceptions is not None else load_exceptions(root)
    raw_items = exceptions.get("html", [])
    if not isinstance(raw_items, list):
        return ["privacy html exceptions must be a list"]

    listed: list[str] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            errors.append(f"html exception[{index}] must be an object")
            continue
        raw_path = item.get("path")
        path = _safe_path(root, raw_path, inside=docs)
        if path is None or path.suffix.lower() != ".html":
            errors.append(f"html exception[{index}] path must be an .html inside evidence/docs")
            continue
        rel = _relative(root, path)
        listed.append(rel)
        if not path.is_file():
            errors.append(f"html exception file missing: {rel}")
        if not str(item.get("reason") or "").strip():
            errors.append(f"html exception missing reason: {rel}")
    if len(listed) != len(set(listed)):
        errors.append("duplicate html exception paths")
    listed_set = set(listed)
    for rel in sorted(actual - listed_set):
        errors.append(f"unlisted third-party html: {rel}")
    for rel in sorted(listed_set - actual):
        errors.append(f"listed html is not an actual file: {rel}")
    return errors


def _allowed_email_contract(exceptions: dict, errors: list[str]) -> set[str]:
    raw = exceptions.get("allowed_emails", [])
    if not isinstance(raw, list):
        errors.append("allowed_emails must be a list")
        return set()
    allowed: list[str] = []
    for index, value in enumerate(raw):
        if not isinstance(value, str) or value != value.strip().lower():
            errors.append(f"allowed_emails[{index}] must be one exact lowercased address")
            continue
        addr = value
        if not EMAIL_RE.fullmatch(addr):
            errors.append(f"allowed_emails[{index}] is not an email address")
        else:
            allowed.append(addr)
    if len(allowed) != len(set(allowed)):
        errors.append("allowed_emails has duplicates")
    return set(allowed)


def _forbidden_errors(root: Path, exceptions: dict) -> list[str]:
    errors: list[str] = []
    raw = exceptions.get("forbidden_paths", [])
    if not isinstance(raw, list):
        return ["forbidden_paths must be a list"]
    forbidden: list[tuple[str, Path]] = []
    for index, value in enumerate(raw):
        path = _safe_path(root, value)
        if path is None:
            errors.append(f"forbidden_paths[{index}] is not a safe package-relative path")
            continue
        rel = _relative(root, path)
        forbidden.append((rel, path))
        if path.exists():
            errors.append(f"forbidden path present: {rel}")
    if len([rel for rel, _ in forbidden]) != len({rel for rel, _ in forbidden}):
        errors.append("forbidden_paths has duplicates")

    report_dir = root / "report"
    for report in report_dir.rglob("*.md") if report_dir.exists() else []:
        try:
            targets = MD_IMAGE_RE.findall(report.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"unreadable {_relative(root, report)}: {exc}")
            continue
        for rel, _path in forbidden:
            basename = Path(rel).name
            if any(rel in target.replace("\\", "/") or basename in target for target in targets):
                errors.append(f"report embeds forbidden path: {_relative(root, report)}")
    return errors


def _redaction_errors(root: Path, exceptions: dict) -> list[str]:
    errors: list[str] = []
    raw = exceptions.get("redactions", [])
    if not isinstance(raw, list):
        return ["redactions must be a list"]
    seen: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"redactions[{index}] must be an object")
            continue
        path = _safe_path(root, item.get("path"))
        markers = item.get("markers")
        if path is None:
            errors.append(f"redactions[{index}] has an unsafe or empty path")
            continue
        rel = _relative(root, path)
        seen.append(rel)
        if not isinstance(markers, list) or not markers or any(not str(marker).strip() for marker in markers):
            errors.append(f"redaction markers missing: {rel}")
            continue
        if not path.is_file():
            errors.append(f"redaction file missing: {rel}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"unreadable redaction file {rel}: {exc}")
            continue
        missing = [str(marker) for marker in markers if str(marker) not in text]
        if missing:
            errors.append(f"redaction markers absent: {rel}")
    if len(seen) != len(set(seen)):
        errors.append("redactions has duplicate paths")
    return errors


def _parse_network_documents(text: str, suffix: str) -> tuple[list[object], int | None]:
    if suffix.lower() != ".jsonl":
        try:
            return [json.loads(text)], None
        except json.JSONDecodeError:
            return [], 0
    documents: list[object] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            documents.append(json.loads(line))
        except json.JSONDecodeError:
            return [], line_number
    return documents, None


def privacy_errors(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        exceptions = load_exceptions(root)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]
    errors.extend(html_exception_errors(root, exceptions))
    errors.extend(_forbidden_errors(root, exceptions))
    errors.extend(_redaction_errors(root, exceptions))
    allowed = _allowed_email_contract(exceptions, errors)
    for path in iter_scan_files(root):
        rel = _relative(root, path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"unreadable {rel}: {exc}")
            continue
        for match in EMAIL_RE.findall(text):
            if not allowed_email(match, allowed):
                errors.append(f"personal email pattern in {rel}")
        rel_parts = path.relative_to(root).parts
        is_network = len(rel_parts) >= 2 and rel_parts[:2] == ("evidence", "network")
        if is_network:
            if path.name.casefold() in FORBIDDEN_NETWORK_NAMES:
                errors.append(f"forbidden raw network artifact: {rel}")
            network_docs, invalid_line = _parse_network_documents(text, path.suffix)
            if invalid_line is not None:
                if path.suffix.lower() == ".jsonl":
                    errors.append(f"network artifact is not valid JSONL at line {invalid_line}: {rel}")
                else:
                    errors.append(f"network artifact is not valid JSON: {rel}")
                continue
            if any(contains_unsanitized_network_data(doc) for doc in network_docs):
                errors.append(f"network artifact contains unsanitized secret material: {rel}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        errors = privacy_errors(args.root.resolve())
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
