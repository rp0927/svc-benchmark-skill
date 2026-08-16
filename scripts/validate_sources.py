#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare report D-form URLs to the package source ledger."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

# $0.99 / 5달러 / 0.01달러 / 1,234달러. Exact $0,$0.00,0달러,0.00달러 excluded
# even when a sentence comma follows. 600억 달러 excluded. Invalid commas
# excluded. Do not stop before a real decimal. No Unicode \b.
_END = r"(?![\d]|(?:,\d{1,2}(?!\d))|(?:,\d{3})|\.\d)"
_AMOUNT = (
    rf"(?!0+(?:\.0+)?{_END})"
    r"(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d+)?"
    rf"{_END}"
)
CURRENCY_RE = re.compile(
    rf"\${_AMOUNT}|(?<![0-9억조.,]){_AMOUNT}\s*달러"
)
URL_RE = re.compile(r"^https?://\S+$", re.I)
DFORM_NAMED = re.compile(
    r"^- \*\*([^*]+)\*\* — \[(https?://[^\]\s]+)\]\(\2\)",
    re.M,
)
OUTLET_RE = re.compile(
    r"(?<![A-Za-z0-9])((?:The\s+)?[A-Z][A-Za-z0-9]+(?:[A-Z][A-Za-z0-9]+)*)(?![A-Za-z0-9])"
)
OUTLET_STOP = {
    "API",
    "About",
    "Agent",
    "Allow",
    "Android",
    "Apple",
    "Ask",
    "Auto",
    "Billing",
    "Bots",
    "Chat",
    "Computer",
    "Create",
    "Cursor",
    "General",
    "Get",
    "Grok",
    "Heavy",
    "Introducing",
    "Linux",
    "Mac",
    "Manage",
    "Marketplace",
    "On",
    "Open",
    "Overview",
    "Premium",
    "Review",
    "Routine",
    "Search",
    "Settings",
    "SpaceXAI",
    "Store",
    "SuperGrok",
    "Teach",
    "Teams",
    "This",
    "Ultra",
    "Updates",
    "Usage",
    "Use",
    "Weekly",
    "Windows",
}


def report_cited_urls(md: str) -> list[str]:
    """Return every D-form occurrence; callers need duplicates preserved."""
    return re.findall(r"\[(https?://[^\]\s]+)\]\(\1\)", md)


def ledger_urls(doc: dict) -> list[str]:
    """Use cited when declared, otherwise combine primary and secondary."""
    if "cited" in doc:
        cited = doc.get("cited")
        return [str(item).strip() for item in cited] if isinstance(cited, list) else []
    out: list[str] = []
    for key in ("primary", "secondary"):
        rows = doc.get(key)
        if isinstance(rows, list):
            out.extend(str(item).strip() for item in rows)
    return out


def url_has_userinfo(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.username is not None or parsed.password is not None


def url_host(url: str) -> str:
    parsed = urlparse(url)
    if parsed.username is not None or parsed.password is not None:
        return ""
    return (parsed.hostname or "").lower().rstrip(".")


def _as_list(value: object) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def token_in_text(label: str, text: str) -> bool:
    if not label:
        return False
    pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(label)}(?![A-Za-z0-9])")
    return pattern.search(text) is not None


def _exact_labels(primary: str, aliases: object) -> set[str]:
    labels = {primary} if primary else set()
    labels.update(_as_list(aliases))
    return {item for item in labels if item}


def named_source_catalog(md: str, doc: dict) -> list[dict[str, set[str]]]:
    """Exact label/name plus explicit aliases only. No first-word aliases."""
    entries: list[dict[str, set[str]]] = []

    def add(labels: set[str], hosts: set[str], urls: set[str]) -> None:
        labels = {item for item in labels if item}
        hosts = {item for item in hosts if item}
        urls = {item for item in urls if item}
        if labels or hosts or urls:
            entries.append({"labels": labels, "hosts": hosts, "urls": urls})

    raw = None
    if isinstance(doc, dict):
        for key in ("named", "labels", "sources"):
            if key in doc:
                raw = doc.get(key)
                break
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or item.get("name") or "").strip()
            labels = _exact_labels(label, item.get("aliases") if "aliases" in item else item.get("alias"))
            urls = set(_as_list(item.get("urls") if "urls" in item else item.get("url")))
            hosts = {
                h.lower().lstrip(".").rstrip(".")
                for h in _as_list(item.get("hosts") if "hosts" in item else item.get("host"))
            }
            urls = {url for url in urls if not url_has_userinfo(url)}
            hosts.update(url_host(url) for url in urls)
            add(labels, hosts, urls)
    elif isinstance(raw, dict):
        for label, value in raw.items():
            urls: set[str] = set()
            hosts: set[str] = set()
            aliases: object = None
            if isinstance(value, dict):
                urls.update(_as_list(value.get("urls") if "urls" in value else value.get("url")))
                hosts.update(
                    h.lower().lstrip(".").rstrip(".")
                    for h in _as_list(value.get("hosts") if "hosts" in value else value.get("host"))
                )
                aliases = value.get("aliases") if "aliases" in value else value.get("alias")
            else:
                for item in _as_list(value):
                    if item.startswith("http://") or item.startswith("https://"):
                        urls.add(item)
                    else:
                        hosts.add(item.lower().lstrip(".").rstrip("."))
            urls = {url for url in urls if not url_has_userinfo(url)}
            hosts.update(url_host(url) for url in urls)
            add(_exact_labels(str(label).strip(), aliases), hosts, urls)

    for label, url in DFORM_NAMED.findall(md):
        add({label.strip()}, {url_host(url)}, set() if url_has_userinfo(url) else {url})
    return entries


def paragraph_urls(para: str) -> list[str]:
    found = re.findall(r"https?://[^\s\)\]\>]+", para)
    return [item.rstrip(".,;\"'") for item in found]


def catalog_matches_paragraph(entry: dict[str, set[str]], para_urls: list[str]) -> bool:
    usable = {url for url in entry["urls"] if url and not url_has_userinfo(url)}
    for url in para_urls:
        if url_has_userinfo(url):
            continue
        if url in usable:
            return True
        host = url_host(url)
        if host and host in entry["hosts"]:
            return True
    return False


def currency_errors(md: str, doc: dict) -> list[str]:
    catalog = named_source_catalog(md, doc)
    errors: list[str] = []
    for para in re.split(r"\n\s*\n", md):
        if not CURRENCY_RE.search(para):
            continue
        para_urls = paragraph_urls(para)
        mentioned = [
            entry
            for entry in catalog
            if any(token_in_text(label, para) for label in entry["labels"])
        ]
        if mentioned:
            for _entry in mentioned:
                if not catalog_matches_paragraph(_entry, para_urls):
                    errors.append("mentioned source missing own host/url")
            continue
        outlets = [
            name
            for name in OUTLET_RE.findall(para)
            if name not in OUTLET_STOP and not name.startswith("The ") and len(name) >= 4
        ]
        if outlets:
            errors.append("named-source nonzero currency without matching host/url")
    return errors


def source_errors(md: str, doc: dict) -> list[str]:
    report = report_cited_urls(md)
    ledger = ledger_urls(doc)
    errors: list[str] = []

    if "cited" in doc and not isinstance(doc.get("cited"), list):
        errors.append("sources cited must be a list")
    for key in ("primary", "secondary"):
        if "cited" not in doc and key in doc and not isinstance(doc.get(key), list):
            errors.append(f"sources {key} must be a list")
    if not ledger:
        errors.append("empty source ledger")

    if any(url_has_userinfo(url) for url in report) or any(url_has_userinfo(url) for url in ledger):
        errors.append("source url has userinfo")

    bad_urls = [url for url in ledger if not URL_RE.match(url)]
    if bad_urls:
        errors.append("source ledger has invalid URL entries")

    report_dupes = sorted(url for url, n in Counter(report).items() if n > 1)
    ledger_dupes = sorted(url for url, n in Counter(ledger).items() if n > 1)
    if report_dupes:
        errors.append("duplicate report D-form urls: " + ", ".join(report_dupes))
    if ledger_dupes:
        errors.append("duplicate source ledger urls: " + ", ".join(ledger_dupes))

    report_set = set(report)
    ledger_set = set(ledger)
    missing = sorted(report_set - ledger_set)
    extra = sorted(ledger_set - report_set)
    if missing:
        errors.append("sources missing report urls: " + ", ".join(missing))
    if extra:
        errors.append("sources extra vs report: " + ", ".join(extra))
    if len(report) != len(ledger):
        errors.append(f"count report={len(report)} sources={len(ledger)}")
    errors.extend(currency_errors(md, doc))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        md = args.report.read_text(encoding="utf-8")
        doc = json.loads(args.sources.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ValueError("sources root must be an object")
        errors = source_errors(md, doc)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    count = len(report_cited_urls(md))
    print(f"OK {count}/{count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
