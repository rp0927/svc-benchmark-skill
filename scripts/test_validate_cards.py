#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_cards: schema and package-local evidence files."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_cards import infer_package_root, load_cards, validate_cards  # noqa: E402

FAILURES: list[str] = []


def card(**over: object) -> dict:
    base = {
        "id": "orbs",
        "name": "Orbs",
        "status": "live",
        "one_liner": "원격 머신",
        "job_to_be_done": "노트북과 분리",
        "insight": "일의 단위가 원격 머신이다",
        "deleted": False,
        "evidence": [
            {"url": "https://example.test/orbs", "observed": "docs", "note": "공식 설명"}
        ],
    }
    base.update(over)
    return base


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def test_schema_basics() -> None:
    cards = [card(), card(id="tab", name="Tab", status="deleted", deleted=True)]
    check(not validate_cards(cards), "normal cards should pass")
    bad = card()
    del bad["job_to_be_done"]
    check(any("job_to_be_done" in error for error in validate_cards([bad])), "missing field FN")
    check(any("duplicate" in error for error in validate_cards([card(), card()])), "duplicate id FN")
    check(any("slug" in error for error in validate_cards([card(id="Orb Size")])), "space id FN")
    check(any("deleted=true" in error for error in validate_cards([card(deleted=True)])), "deleted FN")
    check(any("if_we_build" in error for error in validate_cards([card(if_we_build="x")])), "forbidden FN")


def test_core_reason_and_evidence_text() -> None:
    errors = validate_cards([card(one_liner="", job_to_be_done="", missing_reason=None)])
    check(any("missing_reason" in error for error in errors), f"core FN: {errors}")
    check(not validate_cards([card(one_liner="", job_to_be_done="", missing_reason="미관측")]), "reason FP")
    for key in ("url", "note"):
        row = {"url": "https://example.test", "observed": "docs", "note": "설명"}
        row[key] = ""
        errors = validate_cards([card(evidence=[row])])
        check(any(f"{key} must be non-empty" in error for error in errors), f"{key} FN: {errors}")


def _root() -> tuple[tempfile.TemporaryDirectory, Path, Path]:
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    (root / "notes").mkdir()
    (root / "evidence/screenshots").mkdir(parents=True)
    (root / "evidence/docs").mkdir(parents=True)
    card_path = root / "notes/feature-cards.json"
    return temp, root, card_path


def _write_redactions(root: Path, redactions: list[dict]) -> None:
    (root / "notes/privacy-exceptions.json").write_text(
        json.dumps({"redactions": redactions}), encoding="utf-8"
    )


def test_root_inference_and_screenshot() -> None:
    temp, root, path = _root()
    try:
        check(infer_package_root(path) == root.resolve(), "package root inference")
        (root / "evidence/screenshots/shot.png").write_bytes(b"x")
        good = card(
            screenshot="evidence/screenshots/shot.png",
            evidence=[{"url": "local:app", "observed": "browser", "note": "화면"}],
        )
        check(not validate_cards([good], root), "existing screenshot should satisfy browser")
        bad = card(screenshot="evidence/screenshots/missing.png")
        check(any("screenshot file missing" in error for error in validate_cards([bad], root)), "shot FN")
    finally:
        temp.cleanup()


def test_visual_and_runtime_paths() -> None:
    temp, root, _ = _root()
    try:
        (root / "evidence/docs/tree.txt").write_text(
            "[MASKED_NAME]\n[MASKED_EMAIL]\nbutton\n", encoding="utf-8"
        )
        _write_redactions(
            root,
            [
                {
                    "kind": "accessibility-tree",
                    "path": "evidence/docs/tree.txt",
                    "markers": ["[MASKED_NAME]", "[MASKED_EMAIL]"],
                }
            ],
        )
        visual = card(
            evidence=[
                {
                    "url": "local:app",
                    "observed": "browser",
                    "note": "접근성 트리",
                    "path": "evidence/docs/tree.txt",
                }
            ]
        )
        check(not validate_cards([visual], root), "browser evidence path should pass")
        missing = card(evidence=[{"url": "local:app", "observed": "browser", "note": "화면"}])
        errors = validate_cards([missing], root)
        check(any("otherwise use docs-only" in error for error in errors), f"browser path FN: {errors}")
        docs_only = card(
            evidence=[{"url": "https://example.test/docs", "observed": "docs-only", "note": "문서만"}]
        )
        check(not validate_cards([docs_only], root), "docs-only should not need a file")
        for observed in ("cli", "docs+cli", "network"):
            row = {"url": "local:trace", "observed": observed, "note": "실측"}
            errors = validate_cards([card(evidence=[row])], root)
            check(any("requires an existing evidence.path" in error for error in errors), f"{observed} path FN")
    finally:
        temp.cleanup()


def test_browser_rejects_non_tree_fallbacks() -> None:
    temp, root, _ = _root()
    try:
        (root / "report").mkdir()
        (root / "report/report.md").write_text("[MASKED]\n", encoding="utf-8")
        _write_redactions(
            root,
            [
                {
                    "kind": "accessibility-tree",
                    "path": "report/report.md",
                    "markers": ["[MASKED]"],
                }
            ],
        )
        report_fallback = card(
            evidence=[
                {
                    "url": "local:app",
                    "observed": "browser",
                    "path": "report/report.md",
                    "note": "보고서 파일",
                }
            ]
        )
        errors = validate_cards([report_fallback], root)
        check(any("accessibility tree" in error for error in errors), f"report fallback FN: {errors}")

        (root / "evidence/docs/note.txt").write_text("[MASKED]\n", encoding="utf-8")
        _write_redactions(
            root,
            [
                {
                    "kind": "text-redaction",
                    "path": "evidence/docs/note.txt",
                    "markers": ["[MASKED]"],
                }
            ],
        )
        arbitrary = card(
            evidence=[
                {
                    "url": "local:app",
                    "observed": "browser",
                    "path": "evidence/docs/note.txt",
                    "note": "임의 문서",
                }
            ]
        )
        errors = validate_cards([arbitrary], root)
        check(any("accessibility tree" in error for error in errors), f"arbitrary file FN: {errors}")
    finally:
        temp.cleanup()


def test_browser_requires_registered_present_markers() -> None:
    temp, root, _ = _root()
    try:
        tree = root / "evidence/docs/tree.txt"
        tree.write_text("[MASKED_NAME]\n", encoding="utf-8")
        row = {
            "url": "local:app",
            "observed": "browser",
            "path": "evidence/docs/tree.txt",
            "note": "접근성 트리",
        }
        _write_redactions(root, [])
        errors = validate_cards([card(evidence=[row])], root)
        check(any("accessibility tree" in error for error in errors), f"unregistered tree FN: {errors}")
        _write_redactions(
            root,
            [
                {
                    "kind": "accessibility-tree",
                    "path": "evidence/docs/tree.txt",
                    "markers": ["[MASKED_NAME]", "[MASKED_EMAIL]"],
                }
            ],
        )
        errors = validate_cards([card(evidence=[row])], root)
        check(any("accessibility tree" in error for error in errors), f"absent marker FN: {errors}")
        _write_redactions(
            root,
            [
                {
                    "kind": "accessibility-tree",
                    "path": "evidence/docs/tree.txt",
                    "markers": [],
                }
            ],
        )
        errors = validate_cards([card(evidence=[row])], root)
        check(any("accessibility tree" in error for error in errors), f"empty markers FN: {errors}")
    finally:
        temp.cleanup()


def test_load_and_live() -> None:
    check(len(load_cards({"cards": [card()]})) == 1, "wrapped cards")
    root = HERE.parents[4] / "data/research/20260814_grok-bot"
    path = root / "notes/feature-cards.json"
    if not path.exists():
        return
    cards = load_cards(json.loads(path.read_text(encoding="utf-8")))
    errors = validate_cards(cards, infer_package_root(path))
    check(not errors, f"live cards FAIL: {errors}")
    check(len(cards) == 13, f"live card count {len(cards)}")


def main() -> int:
    test_schema_basics()
    test_core_reason_and_evidence_text()
    test_root_inference_and_screenshot()
    test_visual_and_runtime_paths()
    test_browser_rejects_non_tree_fallbacks()
    test_browser_requires_registered_present_markers()
    test_load_and_live()
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
