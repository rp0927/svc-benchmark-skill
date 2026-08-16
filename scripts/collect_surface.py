#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild IA from robots/sitemap, or from nav HTML when sitemap is blocked."""
from __future__ import annotations

import argparse
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
LOC_TAG = re.compile(r"\{([^}]+)\}loc$")


class _NavParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._in_nav = 0
        self._in_footer = 0
        self._in_a = False
        self._href = ""
        self._text: list[str] = []
        self._nav_tags = {"nav", "header", "footer"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k.lower(): (v or "") for k, v in attrs}
        role = ad.get("role", "").lower()
        if tag in {"nav", "header"} or role == "navigation":
            self._in_nav += 1
        if tag == "footer" or role == "contentinfo":
            self._in_footer += 1
        if tag == "a" and "href" in ad:
            self._in_a = True
            self._href = ad["href"]
            self._text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"nav", "header"} and self._in_nav:
            self._in_nav -= 1
        if tag == "footer" and self._in_footer:
            self._in_footer -= 1
        if tag == "a" and self._in_a:
            label = " ".join("".join(self._text).split())
            zone = "nav" if self._in_nav else ("footer" if self._in_footer else "body")
            if self._href and not self._href.startswith(("#", "javascript:", "mailto:")):
                self.links.append((zone, self._href if not label else f"{self._href}\t{label}"))
            self._in_a = False
            self._href = ""
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._text.append(data)


def read_text(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def sitemap_blocked(text: str | None, *, missing: bool) -> bool:
    if missing or text is None:
        return True
    low = text[:2000].lower()
    if "<urlset" in low or "<sitemapindex" in low:
        return False
    markers = ("login", "signin", "sign-in", "auth", "unauthorized", "403", "401")
    return any(m in low for m in markers) or "<html" in low


def parse_sitemap_locs(xml_text: str) -> list[str]:
    urls: list[str] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml_text, flags=re.I)
    for el in root.iter():
        if el.tag.lower().endswith("loc") and el.text:
            urls.append(el.text.strip())
    return urls


def parse_nav_hrefs(html_text: str, base: str | None = None) -> dict[str, list[str]]:
    parser = _NavParser()
    parser.feed(html_text)
    out: dict[str, list[str]] = {"nav": [], "footer": [], "body": []}
    seen: set[tuple[str, str]] = set()
    for zone, raw in parser.links:
        href, _, label = raw.partition("\t")
        if href.startswith("/") and base:
            href = urljoin(base.rstrip("/") + "/", href.lstrip("/"))
        key = (zone, href)
        if key in seen:
            continue
        seen.add(key)
        item = href if not label else f"{href} — {label}"
        out[zone].append(item)
    return out


def robots_disallow(text: str | None) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.lower().startswith("disallow:"):
            path = s.split(":", 1)[1].strip()
            if path:
                found.append(path)
    return found


def render_sitemap_md(
    *,
    sitemap_text: str | None,
    sitemap_missing: bool,
    html_text: str | None,
    robots_text: str | None,
    base: str | None,
) -> str:
    lines = ["# 사이트맵", ""]
    blocked = sitemap_blocked(sitemap_text, missing=sitemap_missing)
    if blocked:
        lines.append("공식 sitemap.xml은 막혔거나 없다. 아래는 네비·푸터로 다시 그린 IA다.")
        lines.append("")
        if sitemap_missing:
            lines.append("- 상태: 파일 없음")
        else:
            lines.append("- 상태: 열렸으나 URL 목록이 아님 (로그인/HTML)")
    else:
        locs = parse_sitemap_locs(sitemap_text or "")
        lines.append(f"공식 sitemap.xml에서 {len(locs)}개 loc.")
        lines.append("")
        for loc in locs:
            lines.append(f"- {loc}")
        lines.append("")

    if html_text:
        zones = parse_nav_hrefs(html_text, base=base)
        for zone, title in (("nav", "네비"), ("footer", "푸터"), ("body", "본문 링크")):
            items = zones.get(zone) or []
            if not items:
                continue
            lines.append(f"## {title}")
            lines.append("")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")

    disallow = robots_disallow(robots_text)
    if disallow:
        lines.append("## robots Disallow")
        lines.append("")
        for path in disallow:
            lines.append(f"- {path}")
        lines.append("")

    if base:
        host = urlparse(base).netloc
        if host:
            lines.append(f"기준 호스트: `{host}`")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--robots", type=Path)
    p.add_argument("--sitemap", type=Path)
    p.add_argument("--html", type=Path)
    p.add_argument("--base")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    sitemap_missing = args.sitemap is None or not args.sitemap.is_file()
    md = render_sitemap_md(
        sitemap_text=read_text(args.sitemap),
        sitemap_missing=sitemap_missing,
        html_text=read_text(args.html),
        robots_text=read_text(args.robots),
        base=args.base,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
