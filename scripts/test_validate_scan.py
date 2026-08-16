#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_scan: JTBD first, SWOT required, landscape segments. FP/FN both ways."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_scan import (  # noqa: E402
    KNOWN_FAILURES,
    validate_failures,
    validate_jtbd,
    validate_scan,
    validate_swot,
)

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def jtbd(**overrides: object) -> dict:
    data: dict = {
        "job": "노트북이 꺼져도 에이전트가 일하게 한다",
        "pain": "로컬 세션이 끊기면 일이 멈춘다",
        "hired_solutions": ["Amp"],
        "customer_evidence": "customer",
        "hypotheses": [],
        "question": "need-vs-price",
        "depth": "deep",
        "actors": [{"name": "Amp", "url": "https://ampcode.com", "role": "competitor"}],
    }
    data.update(overrides)
    return data


def swot(**overrides: object) -> dict:
    data: dict = {
        "subject": "Amp",
        "job": "노트북이 꺼져도 에이전트가 일하게 한다",
        "strength": "일의 단위가 원격 머신이다",
        "weakness": "로그인 뒤는 열지 못했다",
        "opportunity": "CLI와 웹이 같은 스레드를 쓴다",
        "threat": "구독 한 장의 대안",
    }
    data.update(overrides)
    return data


def write_run(root: Path, *, scan: str = "product", report: str | None = None) -> None:
    (root / "notes").mkdir(parents=True, exist_ok=True)
    (root / "report").mkdir(parents=True, exist_ok=True)
    (root / "run.json").write_text(json.dumps({"scan": scan}), encoding="utf-8")
    (root / "notes/jtbd.json").write_text(json.dumps(jtbd()), encoding="utf-8")
    (root / "notes/swot.json").write_text(json.dumps(swot()), encoding="utf-8")
    if scan == "landscape":
        (root / "notes/segments.json").write_text(
            json.dumps(
                {
                    "segments": [
                        {
                            "id": "remote-agent",
                            "name": "원격 머신 에이전트",
                            "job": "노트북이 꺼져도 일이 이어지게 한다",
                            "depth": "deep",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
    if report is not None:
        (root / "report/report.md").write_text(report, encoding="utf-8")


def test_jtbd_normal() -> None:
    check(not validate_jtbd(jtbd()), "normal jtbd FAIL")


def test_jtbd_missing_job() -> None:
    errs = validate_jtbd(jtbd(job=""))
    check(any("job missing" in item for item in errs), f"job FN: {errs}")


def test_jtbd_hypotheses_required() -> None:
    errs = validate_jtbd(jtbd(customer_evidence="none", hypotheses=[]))
    check(any("hypotheses required" in item for item in errs), f"hyp FN: {errs}")
    ok = validate_jtbd(
        jtbd(
            customer_evidence="proxy-shallow",
            hypotheses=[{"id": "h1", "claim": "얕은 조사로 이 일을 이 해법이 맡는다"}],
        )
    )
    check(not ok, f"hyp FP: {ok}")


def test_swot_four_cells() -> None:
    check(not validate_swot(swot()), "normal swot FAIL")
    errs = validate_swot(swot(threat=""))
    check(any("threat missing" in item for item in errs), f"threat FN: {errs}")


def test_root_product_ok() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_run(root, scan="product")
        errs = validate_scan(root)
        check(not errs, f"product root FAIL: {errs}")


def test_root_missing_jtbd() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_run(root)
        (root / "notes/jtbd.json").unlink()
        errs = validate_scan(root)
        check(any("jtbd.json missing" in item for item in errs), f"missing jtbd FN: {errs}")


def test_landscape_needs_segment() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_run(root, scan="landscape")
        (root / "notes/segments.json").write_text(json.dumps({"segments": []}), encoding="utf-8")
        errs = validate_scan(root)
        check(any("at least one segment" in item for item in errs), f"empty seg FN: {errs}")


def test_insight_swot_labels() -> None:
    body = "\n".join(
        [
            "---",
            'title: "예 서비스 벤치마킹"',
            "source_type: research",
            "cover_note: 사내 공유용 정리 문서",
            "date: 2026-08-16",
            "---",
            "",
            "# 예 서비스 벤치마킹",
            "",
            "## 인사이트",
            "",
            "일의 단위는 원격 머신이다.",
            "",
        ]
    )
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_run(root, report=body)
        errs = validate_scan(root)
        check(any("missing SWOT labels" in item for item in errs), f"label FN: {errs}")
        labeled = body.replace(
            "일의 단위는 원격 머신이다.",
            "| 강점 | 원격 머신 |\n| 약점 | 로그인 |\n| 기회 | 같은 스레드 |\n| 위협 | 구독 대안 |",
        )
        write_run(root, report=labeled)
        ok = validate_scan(root)
        check(not ok, f"label FP: {ok}")


def test_phase_jtbd_skips_swot() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_run(root)
        (root / "notes/swot.json").unlink()
        ok = validate_scan(root, phase="jtbd")
        check(not ok, f"phase jtbd should skip SWOT: {ok}")
        close = validate_scan(root, phase="close")
        check(any("swot.json missing" in item for item in close), f"close still needs SWOT: {close}")


def test_phase_jtbd_empty_job() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_run(root)
        (root / "notes/jtbd.json").write_text(json.dumps(jtbd(job="")), encoding="utf-8")
        errs = validate_scan(root, phase="jtbd")
        check(any("job missing" in item for item in errs), f"phase jtbd empty job FN: {errs}")


def test_map_before_job() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_run(root)
        (root / "notes/jtbd.json").write_text(json.dumps(jtbd(job="")), encoding="utf-8")
        (root / "notes/sitemap.md").write_text("# map\n", encoding="utf-8")
        errs = validate_scan(root, phase="jtbd")
        check(any("map-before-job" in item for item in errs), f"map-before-job FN: {errs}")


def test_phase_segments_empty() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_run(root, scan="landscape")
        (root / "notes/segments.json").write_text(json.dumps({"segments": []}), encoding="utf-8")
        errs = validate_scan(root, phase="segments")
        check(any("at least one segment" in item for item in errs), f"phase segments FN: {errs}")
        (root / "notes/swot.json").unlink()
        still = validate_scan(root, phase="segments")
        check(
            any("at least one segment" in item for item in still),
            f"phase segments lost after SWOT unlink: {still}",
        )
        check(not any("swot.json missing" in item for item in still), f"phase segments wants SWOT: {still}")


def test_fleet_before_segments() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_run(root, scan="landscape")
        (root / "notes/segments.json").write_text(json.dumps({"segments": []}), encoding="utf-8")
        (root / "notes/segments").mkdir(parents=True, exist_ok=True)
        (root / "notes/segments/remote-agent.md").write_text("draft\n", encoding="utf-8")
        errs = validate_scan(root, phase="segments")
        check(any("fleet-before-segments" in item for item in errs), f"fleet-before-segments FN: {errs}")


def test_unknown_phase() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_run(root)
        errs = validate_scan(root, phase="open")
        check(any("unknown phase" in item for item in errs), f"unknown phase FN: {errs}")


def test_failures_catalog() -> None:
    check(not validate_failures({"catalog": list(KNOWN_FAILURES), "events": []}), "catalog normal FAIL")
    errs = validate_failures({"events": [{"id": "not-a-real-failure"}]})
    check(any("unknown" in item for item in errs), f"unknown failure FN: {errs}")


def main() -> int:
    test_jtbd_normal()
    test_jtbd_missing_job()
    test_jtbd_hypotheses_required()
    test_swot_four_cells()
    test_root_product_ok()
    test_root_missing_jtbd()
    test_landscape_needs_segment()
    test_insight_swot_labels()
    test_phase_jtbd_skips_swot()
    test_phase_jtbd_empty_job()
    test_map_before_job()
    test_phase_segments_empty()
    test_fleet_before_segments()
    test_unknown_phase()
    test_failures_catalog()
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
