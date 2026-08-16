#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare the first feature table in report.md to feature-cards.json."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from validate_cards import load_cards
from validate_report import parse_frontmatter


def feature_table_rows(md: str) -> list[str]:
    lines = md.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("|") and "기능" in line.split("|")[1]:
            start = i
            break
    if start is None:
        return []
    rows: list[str] = []
    for line in lines[start + 1 :]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or re.fullmatch(r":?-{3,}:?", cells[0].replace(" ", "")):
            continue
        if cells[0] and cells[0] != "기능":
            rows.append(cells[0])
    return rows


def card_rows(cards: list[dict]) -> list[str]:
    out: list[str] = []
    for card in cards:
        name = card.get("report_row") or card.get("name")
        if isinstance(name, str) and name.strip():
            out.append(name.strip())
    return out


def coverage_errors(md: str, cards: list[dict]) -> list[str]:
    fm = parse_frontmatter(md)
    if fm and fm.get("report_profile") == "landscape":
        return []
    table = feature_table_rows(md)
    rows = card_rows(cards)
    errors: list[str] = []
    if not table:
        errors.append("report feature table missing")
        return errors
    if not rows:
        errors.append("cards have no report_row/name")
        return errors
    table_count = Counter(table)
    card_count = Counter(rows)
    table_dupes = sorted(name for name, n in table_count.items() if n > 1)
    card_dupes = sorted(name for name, n in card_count.items() if n > 1)
    if table_dupes:
        errors.append("duplicate table rows: " + ", ".join(table_dupes))
    if card_dupes:
        errors.append("duplicate card report_row: " + ", ".join(card_dupes))
    missing = list((table_count - card_count).elements())
    extra = list((card_count - table_count).elements())
    if missing:
        errors.append("cards missing table rows: " + ", ".join(missing))
    if extra:
        errors.append("cards extra vs table: " + ", ".join(extra))
    if table_count != card_count:
        errors.append(f"count table={len(table)} cards={len(rows)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--cards", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        md = args.report.read_text(encoding="utf-8")
        cards = load_cards(json.loads(args.cards.read_text(encoding="utf-8")))
        errors = coverage_errors(md, cards)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    if errors:
        print("FAIL")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"OK {len(feature_table_rows(md))}/{len(card_rows(cards))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
