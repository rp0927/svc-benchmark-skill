#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_tech: five depth notes, FP/FN both ways."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_tech import (  # noqa: E402
    validate_code,
    validate_impl,
    validate_packets,
    validate_persona,
    validate_perf,
    validate_tech,
)

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def filled_packets() -> dict:
    return {
        "as_of": "2026-08-16",
        "method": "curl-timing",
        "missing_reason": "",
        "flows": [
            {
                "id": "home",
                "method": "GET",
                "host": "ex.test",
                "path": "/",
                "status": 200,
                "ttfb_ms": 10,
                "total_ms": 20,
            }
        ],
    }


def filled_persona() -> dict:
    trial = {
        "persona": "원격으로 일을 맡기는 개발자",
        "job": "노트북이 꺼져도 일이 이어지게 한다",
        "path": ["홈", "문서"],
        "friction": "가격이 로그인 뒤",
        "outcome": "일부",
        "mutation": False,
    }
    other = dict(trial)
    other["persona"] = "문서를 먼저 읽는 구매 담당"
    other["path"] = ["홈", "가격"]
    return {
        "as_of": "2026-08-16",
        "mode": "walkthrough-public",
        "missing_reason": "",
        "trials": [trial, other],
    }


def write_product(root: Path) -> None:
    (root / "notes").mkdir(parents=True)
    (root / "run.json").write_text(json.dumps({"scan": "product"}), encoding="utf-8")
    (root / "notes/packets.json").write_text(json.dumps(filled_packets()), encoding="utf-8")
    (root / "notes/code-surface.json").write_text(
        json.dumps(
            {
                "observed": "docs-only",
                "public_repo": "https://github.com/ex/app",
                "entrypoints": [],
                "client_bundles": [],
                "cli_bins": [],
                "notes": "README",
                "missing_reason": "",
            }
        ),
        encoding="utf-8",
    )
    (root / "notes/impl-methods.json").write_text(
        json.dumps(
            {
                "hosting": "공개 문서",
                "auth": "로그인 게이트",
                "data_path": "",
                "model_routing": "해당 없음",
                "billing_unit": "",
                "missing_reason": "",
            }
        ),
        encoding="utf-8",
    )
    (root / "notes/perf.json").write_text(
        json.dumps(
            {
                "home_ttfb_ms": 10,
                "home_total_ms": 20,
                "api_median_ms": None,
                "stream_first_byte_ms": None,
                "stream_end_ms": None,
                "characteristics": ["첫 바이트가 짧다"],
                "missing_reason": "",
            }
        ),
        encoding="utf-8",
    )
    (root / "notes/persona-trials.json").write_text(json.dumps(filled_persona()), encoding="utf-8")


def test_unit_normal() -> None:
    check(not validate_packets(filled_packets(), allow_shallow=False), "packets normal")
    check(
        not validate_code(
            {"observed": "cli", "cli_bins": ["amp"], "missing_reason": ""},
            allow_shallow=False,
        ),
        "code normal",
    )
    check(
        not validate_impl({"hosting": "헤더", "missing_reason": ""}, allow_shallow=False),
        "impl normal",
    )
    check(
        not validate_perf({"home_ttfb_ms": 12, "missing_reason": ""}, allow_shallow=False),
        "perf normal",
    )
    check(not validate_persona(filled_persona(), allow_shallow=False), "persona normal")


def test_empty_fails() -> None:
    check(
        any("missing_reason" in item for item in validate_packets({"method": "none"}, allow_shallow=False)),
        "packets none FN",
    )
    check(
        any("missing_reason" in item for item in validate_code({"observed": "none"}, allow_shallow=False)),
        "code none FN",
    )
    check(
        any("missing_reason" in item for item in validate_impl({}, allow_shallow=False)),
        "impl empty FN",
    )
    check(
        any("missing_reason" in item or "timing" in item for item in validate_perf({}, allow_shallow=False)),
        "perf empty FN",
    )
    check(
        any("two trials" in item for item in validate_persona({"mode": "walkthrough-public", "trials": []}, allow_shallow=False)),
        "persona count FN",
    )


def test_mutation_banned() -> None:
    data = filled_persona()
    data["trials"][0]["mutation"] = True
    errs = validate_persona(data, allow_shallow=False)
    check(any("persona-trial-as-mutation" in item for item in errs), f"mutation FN: {errs}")


def test_root_product() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_product(root)
        errs = validate_tech(root)
        check(not errs, f"product tech FAIL: {errs}")
        (root / "notes/packets.json").unlink()
        missing = validate_tech(root)
        check(any("packets.json missing" in item for item in missing), f"missing packets FN: {missing}")


def test_landscape_shallow() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_product(root)
        (root / "run.json").write_text(json.dumps({"scan": "landscape"}), encoding="utf-8")
        (root / "notes/segments.json").write_text(json.dumps({"segments": []}), encoding="utf-8")
        skip = {
            "method": "none",
            "observed": "none",
            "mode": "none",
            "missing_reason": "landscape-shallow",
            "flows": [],
            "trials": [],
        }
        (root / "notes/packets.json").write_text(json.dumps(skip), encoding="utf-8")
        (root / "notes/code-surface.json").write_text(json.dumps(skip), encoding="utf-8")
        (root / "notes/impl-methods.json").write_text(
            json.dumps({"missing_reason": "landscape-shallow"}), encoding="utf-8"
        )
        (root / "notes/perf.json").write_text(
            json.dumps({"missing_reason": "landscape-shallow"}), encoding="utf-8"
        )
        (root / "notes/persona-trials.json").write_text(json.dumps(skip), encoding="utf-8")
        errs = validate_tech(root)
        check(not errs, f"landscape shallow FAIL: {errs}")


def main() -> int:
    test_unit_normal()
    test_empty_fails()
    test_mutation_banned()
    test_root_product()
    test_landscape_shallow()
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
