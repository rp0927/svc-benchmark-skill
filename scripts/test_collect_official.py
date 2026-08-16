#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""collect_official classifies sitemap/home links without network."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from collect_official import classify, collect_official, extract_urls  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def test_classify() -> None:
    check(classify("https://ex.test/changelog") == "changelog", "changelog")
    check(classify("https://ex.test/blog/hello") == "blog", "blog")
    check(classify("https://ex.test/docs/api") == "docs", "docs")
    check(classify("https://ex.test/newsroom/pr") == "press", "press")
    check(classify("https://ex.test/pr/launch") == "press", "pr path")
    check(classify("https://ex.test/support/faq") == "support", "support")
    check(classify("https://ex.test/pricing") == "other", "pricing is not press")


def test_extract_and_merge() -> None:
    sitemap = "\n".join(
        [
            "- [Changelog](https://ex.test/changelog)",
            "- https://ex.test/docs/start",
            "- [Careers](https://ex.test/jobs)",
        ]
    )
    html = '<footer><a href="https://ex.test/newsroom">Press</a></footer>'
    pairs = extract_urls(sitemap, html)
    urls = {url for url, _ in pairs}
    check("https://ex.test/changelog" in urls, "md link")
    check("https://ex.test/docs/start" in urls, "bare url")
    check("https://ex.test/newsroom" in urls, "html href")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sm = root / "sitemap.md"
        hm = root / "home.html"
        sm.write_text(sitemap, encoding="utf-8")
        hm.write_text(html, encoding="utf-8")
        out = root / "official-sources.json"
        doc = collect_official(sitemap=sm, html=hm, out=out, as_of="2026-08-16")
        feeds = {item["kind"]: item for item in doc["feeds"]}
        check(feeds["changelog"]["found"] is True, "changelog found")
        check(feeds["docs"]["found"] is True, "docs found")
        check(feeds["press"]["found"] is True, "press found")
        check(feeds["blog"]["found"] is False, "blog still open")
        check(out.is_file(), "wrote json")
        first = json.loads(out.read_text(encoding="utf-8"))
        first["feeds"][0]["url"] = "https://kept.test/changelog"
        first["feeds"][0]["found"] = True
        out.write_text(json.dumps(first), encoding="utf-8")
        again = collect_official(sitemap=sm, html=hm, out=out, as_of="2026-08-16")
        kept = next(item for item in again["feeds"] if item["kind"] == "changelog")
        check(kept["url"] == "https://kept.test/changelog", f"overwrite {kept}")


def main() -> int:
    test_classify()
    test_extract_and_merge()
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
