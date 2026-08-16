#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_coverage: table rows must match card report_row. FP/FN both ways."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_coverage import coverage_errors, feature_table_rows  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def table_md(rows: list[str]) -> str:
    lines = [
        "## 기능",
        "",
        "| 기능 | 우선 |",
        "|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row} | P1 |")
    lines.append("")
    return "\n".join(lines)


def card(report_row: str) -> dict:
    return {"id": report_row, "name": report_row, "report_row": report_row}


def test_normal_13() -> None:
    rows = [f"기능{i}" for i in range(1, 14)]
    errs = coverage_errors(table_md(rows), [card(r) for r in rows])
    check(not errs, f"13/13 should pass: {errs}")
    check(len(feature_table_rows(table_md(rows))) == 13, "parse 13")


def test_missing_card() -> None:
    rows = [f"기능{i}" for i in range(1, 14)]
    cards = [card(r) for r in rows[:-1]]
    errs = coverage_errors(table_md(rows), cards)
    check(any("기능13" in e for e in errs), f"missing FN: {errs}")


def test_extra_card() -> None:
    rows = [f"기능{i}" for i in range(1, 13)]
    cards = [card(r) for r in rows] + [card("유령")]
    errs = coverage_errors(table_md(rows), cards)
    check(any("유령" in e for e in errs), f"extra FN: {errs}")


def test_duplicate_table_rows_fail() -> None:
    errs = coverage_errors(table_md(["검색", "검색"]), [card("검색")])
    check(any("duplicate table rows" in error and "검색" in error for error in errs), f"dup table FN: {errs}")


def test_duplicate_card_report_row_fail() -> None:
    errs = coverage_errors(table_md(["검색"]), [card("검색"), card("검색")])
    check(
        any("duplicate card report_row" in error and "검색" in error for error in errs),
        f"dup card FN: {errs}",
    )


def test_landscape_skips_table() -> None:
    md = "\n".join(
        [
            "---",
            "report_profile: landscape",
            "---",
            "",
            "# 예 경쟁 지형 조사",
            "",
            "## 솔루션 세그먼트",
            "",
            "표 없음.",
            "",
        ]
    )
    errs = coverage_errors(md, [])
    check(not errs, f"landscape skip FAIL: {errs}")


def test_live_grok_bot() -> None:
    root = Path(__file__).resolve().parents[4] / "data/research/20260814_grok-bot"
    report = root / "report/report.md"
    cards = root / "notes/feature-cards.json"
    if not report.exists() or not cards.exists():
        return
    import json
    from validate_cards import load_cards

    md = report.read_text(encoding="utf-8")
    loaded = load_cards(json.loads(cards.read_text(encoding="utf-8")))
    errs = coverage_errors(md, loaded)
    check(not errs, f"live coverage FAIL: {errs}")
    check(len(feature_table_rows(md)) == 13, feature_table_rows(md))


def main() -> int:
    test_normal_13()
    test_missing_card()
    test_extra_card()
    test_duplicate_table_rows_fail()
    test_duplicate_card_report_row_fail()
    test_landscape_skips_table()
    test_live_grok_bot()
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
