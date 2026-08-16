#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_official: five required kinds, caps, community not primary."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_official import validate_official, validate_official_doc  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def filled() -> dict:
    kinds = ("changelog", "blog", "docs", "press", "support")
    return {
        "as_of": "2026-08-16",
        "window_days": 90,
        "missing_reason": "",
        "feeds": [
            {"kind": kind, "url": f"https://ex.test/{kind}", "found": True, "missing_reason": ""}
            for kind in kinds
        ],
        "items": [
            {
                "id": "ch1",
                "kind": "changelog",
                "title": "Ship",
                "url": "https://ex.test/changelog#1",
                "date": "2026-08-01",
                "layer": "primary",
            }
        ],
        "community": [{"title": "thread", "url": "https://reddit.com/r/x", "layer": "hint"}],
    }


def test_normal() -> None:
    check(not validate_official_doc(filled(), allow_shallow=False), "normal")


def test_missing_kind() -> None:
    data = filled()
    data["feeds"] = [item for item in data["feeds"] if item["kind"] != "press"]
    errs = validate_official_doc(data, allow_shallow=False)
    check(any("press" in item for item in errs), f"press FN: {errs}")


def test_not_found_needs_reason() -> None:
    data = filled()
    data["feeds"][1] = {"kind": "blog", "url": "", "found": False, "missing_reason": ""}
    errs = validate_official_doc(data, allow_shallow=False)
    check(any("blog" in item and "missing_reason" in item for item in errs), f"reason FN: {errs}")


def test_community_primary() -> None:
    data = filled()
    data["community"][0]["layer"] = "primary"
    errs = validate_official_doc(data, allow_shallow=False)
    check(any("last30days-as-official" in item for item in errs), f"community FN: {errs}")


def test_root_and_shallow() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "notes").mkdir()
        (root / "run.json").write_text(json.dumps({"scan": "product"}), encoding="utf-8")
        (root / "notes/official-sources.json").write_text(json.dumps(filled()), encoding="utf-8")
        check(not validate_official(root), "product root")
        (root / "notes/official-sources.json").unlink()
        miss = validate_official(root)
        check(any("missing" in item for item in miss), f"missing FN: {miss}")
        (root / "run.json").write_text(json.dumps({"scan": "landscape"}), encoding="utf-8")
        (root / "notes/segments.json").write_text(json.dumps({"segments": []}), encoding="utf-8")
        (root / "notes/official-sources.json").write_text(
            json.dumps({"missing_reason": "landscape-shallow", "feeds": []}),
            encoding="utf-8",
        )
        check(not validate_official(root), "landscape shallow")


def main() -> int:
    test_normal()
    test_missing_kind()
    test_not_found_needs_reason()
    test_community_primary()
    test_root_and_shallow()
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
