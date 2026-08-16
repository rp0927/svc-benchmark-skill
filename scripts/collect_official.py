#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Classify official-source candidates from sitemap.md and home HTML. No network."""
from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_KINDS = ("changelog", "blog", "docs", "press", "support")
OPTIONAL_KINDS = ("rss", "status", "other")
URL_RE = re.compile(r"https?://[^\s)\]>\"']+", re.I)
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)", re.I)

KIND_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("changelog", ("changelog", "change-log", "whats-new", "what's-new", "releases", "release-notes")),
    ("press", ("press", "newsroom", "media-kit", "press-release")),
    ("blog", ("blog", "engineering", "journal", "/stories")),
    ("support", ("support", "help-center", "/help", "/kb", "faq", "knowledge")),
    ("docs", ("docs", "documentation", "manual", "developers", "developer", "/guide", "/reference")),
    ("status", ("/status", "status.", "uptime")),
    ("rss", ("rss", "atom.xml", "feed.xml", "/feed")),
)


class _HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        ad = {k.lower(): (v or "") for k, v in attrs}
        href = ad.get("href", "")
        if href and not href.startswith(("#", "javascript:", "mailto:")):
            self.hrefs.append((href, ad.get("aria-label", "")))


def classify(url: str, label: str = "") -> str:
    blob = f"{url} {label}".lower()
    path = (urlparse(url).path or "").lower().rstrip("/")
    if path == "/pr" or path.startswith("/pr/"):
        return "press"
    for kind, tokens in KIND_RULES:
        if any(token in blob for token in tokens):
            return kind
    return "other"


def extract_urls(*texts: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for text in texts:
        if not text:
            continue
        for label, url in MD_LINK_RE.findall(text):
            if url not in seen:
                seen.add(url)
                found.append((url, label))
        for url in URL_RE.findall(text):
            if url not in seen:
                seen.add(url)
                found.append((url, ""))
        parser = _HrefParser()
        try:
            parser.feed(text)
        except Exception:
            parser.hrefs = []
        for href, label in parser.hrefs:
            if href.startswith("http") and href not in seen:
                seen.add(href)
                found.append((href, label))
    return found


def empty_doc(as_of: str) -> dict:
    return {
        "as_of": as_of,
        "window_days": 90,
        "missing_reason": "",
        "feeds": [
            {"kind": kind, "url": "", "found": False, "missing_reason": ""}
            for kind in REQUIRED_KINDS
        ],
        "items": [],
        "community": [],
    }


def merge_candidates(doc: dict, pairs: list[tuple[str, str]]) -> dict:
    feeds = {item["kind"]: item for item in doc.get("feeds", []) if isinstance(item, dict)}
    for kind in REQUIRED_KINDS:
        feeds.setdefault(kind, {"kind": kind, "url": "", "found": False, "missing_reason": ""})
    extras: list[dict] = []
    for url, label in pairs:
        kind = classify(url, label)
        if kind in REQUIRED_KINDS:
            current = feeds[kind]
            if not current.get("url"):
                current["url"] = url
                current["found"] = True
                current["missing_reason"] = ""
        elif kind in OPTIONAL_KINDS:
            extras.append({"kind": kind, "url": url, "found": True, "missing_reason": ""})
    ordered = [feeds[kind] for kind in REQUIRED_KINDS]
    seen_extra = {item["url"] for item in ordered if item.get("url")}
    for item in extras:
        if item["url"] not in seen_extra:
            ordered.append(item)
            seen_extra.add(item["url"])
    doc["feeds"] = ordered
    return doc


def collect_official(
    *,
    sitemap: Path | None,
    html: Path | None,
    out: Path,
    as_of: str,
) -> dict:
    texts: list[str] = []
    for path in (sitemap, html):
        if path is not None and path.is_file():
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
    if out.is_file():
        try:
            doc = json.loads(out.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                doc = empty_doc(as_of)
        except (OSError, json.JSONDecodeError):
            doc = empty_doc(as_of)
    else:
        doc = empty_doc(as_of)
    if not doc.get("as_of"):
        doc["as_of"] = as_of
    merge_candidates(doc, extract_urls(*texts))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sitemap", type=Path)
    p.add_argument("--html", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--as-of", default="")
    args = p.parse_args(argv)
    from datetime import date

    stamp = args.as_of or date.today().isoformat()
    collect_official(sitemap=args.sitemap, html=args.html, out=args.out, as_of=stamp)
    print(args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
