#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""collect_surface: sitemap blocked → nav rebuild. Network-free fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from collect_surface import (  # noqa: E402
    parse_nav_hrefs,
    parse_sitemap_locs,
    render_sitemap_md,
    sitemap_blocked,
)

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def test_sitemap_ok():
    xml = """<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://ex.test/a</loc></url>
      <url><loc>https://ex.test/b</loc></url>
    </urlset>"""
    check(not sitemap_blocked(xml, missing=False), "valid sitemap marked blocked")
    locs = parse_sitemap_locs(xml)
    check(locs == ["https://ex.test/a", "https://ex.test/b"], f"locs={locs}")


def test_sitemap_login_html_is_blocked():
    html = "<html><body>Please login</body></html>"
    check(sitemap_blocked(html, missing=False), "login html not blocked")
    check(sitemap_blocked(None, missing=True), "missing sitemap not blocked")


def test_nav_rebuild():
    html = """
    <header><nav>
      <a href="/pricing">Pricing</a>
      <a href="/manual">Manual</a>
    </nav></header>
    <footer><a href="/security">Security</a></footer>
    """
    zones = parse_nav_hrefs(html, base="https://ex.test")
    nav_hrefs = " ".join(zones["nav"])
    check("https://ex.test/pricing" in nav_hrefs, f"nav missing pricing: {zones}")
    check("https://ex.test/manual" in nav_hrefs, f"nav missing manual: {zones}")
    check(any("security" in x.lower() for x in zones["footer"]), f"footer={zones['footer']}")


def test_render_uses_nav_when_blocked():
    html = '<nav><a href="/modes">Modes</a></nav>'
    md = render_sitemap_md(
        sitemap_text="<html>login</html>",
        sitemap_missing=False,
        html_text=html,
        robots_text="User-agent: *\nDisallow: /settings",
        base="https://ex.test",
    )
    check("막혔거나 없다" in md, "blocked notice missing")
    check("Modes" in md or "/modes" in md, "nav not in md")
    check("/settings" in md, "robots disallow missing")


def main() -> int:
    test_sitemap_ok()
    test_sitemap_login_html_is_blocked()
    test_nav_rebuild()
    test_render_uses_nav_when_blocked()
    if FAILURES:
        print("FAIL")
        for f in FAILURES:
            print("-", f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
