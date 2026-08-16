#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""collect_cli: equals-form surfaces, all-fail exit, mixed result JSON."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from collect_cli import main  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def test_surface_equals_help_succeeds() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "cli"
        notes = Path(td) / "cli.md"
        code = main(
            [
                "--bin",
                sys.executable,
                "--surface=--help",
                "--out",
                str(out),
                "--notes",
                str(notes),
            ]
        )
        index = json.loads((out / "index.json").read_text(encoding="utf-8"))
        notes_ok = notes.exists()
    check(code == 0, f"success exit: {code}")
    check(index and index[0]["ok"] is True, f"success index: {index}")
    check(index[0]["cmd"][-1] == "--help", f"surface args: {index[0]['cmd']}")
    check(notes_ok, "notes missing")


def test_all_surfaces_fail_nonzero() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "cli"
        code = main(
            [
                "--bin",
                str(Path(td) / "missing-binary"),
                "--surface=--help",
                "--out",
                str(out),
            ]
        )
        index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    check(code == 1, f"all-fail exit: {code}")
    check(index and index[0]["ok"] is False, f"all-fail index: {index}")


def test_mixed_surfaces_write_json_and_exit_zero() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "cli"
        code = main(
            [
                "--bin",
                sys.executable,
                "--surface=--help",
                "--surface=--not-a-real-cpython-flag",
                "--out",
                str(out),
            ]
        )
        index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    check(code == 0, f"mixed exit: {code}")
    check(len(index) == 2, f"mixed count: {index}")
    check(any(row["ok"] for row in index), f"mixed missing success: {index}")
    check(any(not row["ok"] for row in index), f"mixed missing failure: {index}")


def main_tests() -> int:
    test_surface_equals_help_succeeds()
    test_all_surfaces_fail_nonzero()
    test_mixed_surfaces_write_json_and_exit_zero()
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_tests())
