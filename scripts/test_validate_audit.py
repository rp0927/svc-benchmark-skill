#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_audit: dynamic core and figure bridge contracts."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_audit import audit_errors  # noqa: E402

FAILURES: list[str] = []
CORE_IDS = ["must-keep-files", "account-boundary"]
FIGURE_IDS = ["diagram-alpha", "visual-proof-9"]


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def _write_pkg(
    root: Path,
    *,
    core_ids: list[str] | None = None,
    claims: list[dict] | None = None,
    omit_core: bool = False,
    mismatch: bool = False,
    report_figure: bool = True,
    visual_figure: bool = True,
    bridges: bool = True,
    extra_bridge: bool = False,
) -> Path:
    (root / "report").mkdir()
    (root / "sources").mkdir()
    (root / "evidence/docs").mkdir(parents=True)
    (root / "evidence/screenshots").mkdir(parents=True)
    (root / "evidence/docs/note.txt").write_text("evidence\n", encoding="utf-8")
    (root / "evidence/screenshots/01.jpg").write_bytes(b"x")
    core_ids = list(CORE_IDS if core_ids is None else core_ids)
    claims = list(
        [{"id": "fact-alpha", "type": "citation"}]
        + [{"id": cid, "type": "figure"} for cid in FIGURE_IDS]
        if claims is None
        else claims
    )
    (root / "sources/audit-manifest.json").write_text(
        json.dumps({"core_required": core_ids, "claims": claims}), encoding="utf-8"
    )
    fact_items = [] if omit_core else [
        {
            "claim_id": cid,
            "verdict": "mismatch" if mismatch else "match",
            "evidence": ["evidence/docs/note.txt"],
        }
        for cid in core_ids
    ]
    (root / "sources/audit-fact.json").write_text(json.dumps({"items": fact_items}), encoding="utf-8")
    caption = "A1. 화면"
    report = f"![{caption}](../evidence/screenshots/01.jpg)\n" if report_figure else "본문만 있음.\n"
    (root / "report/report.md").write_text(report, encoding="utf-8")
    items: list[dict] = []
    if visual_figure:
        items.append(
            {
                "id": "occurrence-any-id",
                "path": "../evidence/screenshots/01.jpg",
                "caption": caption,
                "observed": "화면 한 장",
                "verdict": "match",
            }
        )
    figure_ids = [str(claim.get("id")) for claim in claims if claim.get("type") == "figure"]
    if bridges:
        for cid in figure_ids:
            items.append(
                {
                    "claim_id": cid,
                    "role": "bridge",
                    "supporting": ["occurrence-any-id"],
                    "observed": "연결 확인",
                    "verdict": "match",
                }
            )
    if extra_bridge:
        items.append(
            {
                "claim_id": "not-in-manifest",
                "role": "bridge",
                "supporting": ["occurrence-any-id"],
                "observed": "남는 연결",
                "verdict": "match",
            }
        )
    (root / "sources/audit-visual.json").write_text(json.dumps({"items": items}), encoding="utf-8")
    return root


def run_case(**kwargs: object) -> tuple[list[str], dict]:
    temp = tempfile.TemporaryDirectory()
    root = _write_pkg(Path(temp.name), **kwargs)
    result = audit_errors(root)
    temp.cleanup()
    return result


def test_arbitrary_ids_positive() -> None:
    errors, stats = run_case()
    check(not errors, f"generic audit should pass: {errors}")
    check(stats["core"] == "2/2" and stats["bridge"] == "2/2", str(stats))
    check(stats["occurrence"] == "1/1" and stats["mismatch"] == 0, str(stats))


def test_missing_core_fails() -> None:
    errors, _ = run_case(omit_core=True)
    check(any("core missing" in error for error in errors), f"core FN: {errors}")


def test_mismatch_fails() -> None:
    errors, stats = run_case(mismatch=True)
    check(stats["mismatch"] == 2, f"mismatch count: {stats}")
    check(any("mismatch" in error for error in errors), f"mismatch FN: {errors}")


def test_empty_contracts_fail_closed() -> None:
    errors, _ = run_case(core_ids=[])
    check(any("core_required" in error for error in errors), f"empty core FN: {errors}")
    errors, _ = run_case(claims=[])
    check(any("claims" in error for error in errors), f"empty claims FN: {errors}")


def test_empty_report_figures_fail_closed() -> None:
    errors, _ = run_case(report_figure=False, visual_figure=False, bridges=False)
    check(any("no figures" in error for error in errors), f"empty report figure FN: {errors}")


def test_missing_visual_occurrence_fails() -> None:
    errors, _ = run_case(visual_figure=False, bridges=False)
    check(any("not in visual audit" in error or "occurrence" in error for error in errors), f"figure FN: {errors}")


def test_missing_and_extra_bridges_fail() -> None:
    errors, _ = run_case(bridges=False)
    check(any("bridge missing" in error for error in errors), f"missing bridge FN: {errors}")
    errors, _ = run_case(extra_bridge=True)
    check(any("bridge extras" in error for error in errors), f"extra bridge FN: {errors}")


def _http_core_pkg(root: Path, url: str, *, dform: bool, ledger: bool) -> None:
    _write_pkg(root, core_ids=["only-core"])
    report = root / "report" / "report.md"
    figure = report.read_text(encoding="utf-8")
    if dform:
        report.write_text(
            figure + f"\n- **Docs** — [{url}]({url})<br><i>함의: t.</i>\n",
            encoding="utf-8",
        )
    (root / "notes").mkdir(exist_ok=True)
    if ledger:
        (root / "notes" / "sources.json").write_text(
            json.dumps({"cited": [url]}),
            encoding="utf-8",
        )
    (root / "sources" / "audit-fact.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "claim_id": "only-core",
                        "verdict": "match",
                        "evidence": [url, "evidence/docs/note.txt"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_unregistered_http_url_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _write_pkg(Path(td), core_ids=["only-core"])
        (root / "sources" / "audit-fact.json").write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "claim_id": "only-core",
                            "verdict": "match",
                            "evidence": ["https://nonexistent.invalid/core"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        errors, stats = audit_errors(root)
    check(
        any("unregistered url evidence" in error for error in errors),
        f"unregistered URL FN: {errors}",
    )
    check(stats["core"] != "1/1", f"nonexistent.invalid must not pass core 1/1: {stats}")


def test_dform_only_http_fails() -> None:
    url = "https://example.test/docs"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _http_core_pkg(root, url, dform=True, ledger=False)
        errors, stats = audit_errors(root)
    check(any("dform-only url evidence" in error for error in errors), f"dform-only FN: {errors}")
    check(stats["core"] != "1/1", f"dform-only must not pass core 1/1: {stats}")


def test_ledger_only_http_fails() -> None:
    url = "https://example.test/docs"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _http_core_pkg(root, url, dform=False, ledger=True)
        errors, stats = audit_errors(root)
    check(any("ledger-only url evidence" in error for error in errors), f"ledger-only FN: {errors}")
    check(stats["core"] != "1/1", f"ledger-only must not pass core 1/1: {stats}")


def test_http_in_both_registries_positive() -> None:
    url = "https://example.test/docs"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _http_core_pkg(root, url, dform=True, ledger=True)
        errors, stats = audit_errors(root)
    check(not errors, f"both-registry HTTP should pass: {errors}")
    check(stats["core"] == "1/1", str(stats))


def test_live_package() -> None:
    root = HERE.parents[4] / "data/research/20260814_grok-bot"
    if not root.exists():
        return
    errors, stats = audit_errors(root)
    check(not errors, f"live audit FAIL: {errors}")
    check(stats["core"] == "7/7", str(stats))
    check(stats["occurrence"] == "17/17", str(stats))
    check(stats["bridge"] == "4/4", str(stats))
    check(stats["mismatch"] == 0, str(stats))


def main() -> int:
    test_arbitrary_ids_positive()
    test_missing_core_fails()
    test_mismatch_fails()
    test_empty_contracts_fail_closed()
    test_empty_report_figures_fail_closed()
    test_missing_visual_occurrence_fails()
    test_missing_and_extra_bridges_fail()
    test_unregistered_http_url_fails()
    test_dform_only_http_fails()
    test_ledger_only_http_fails()
    test_http_in_both_registries_positive()
    test_live_package()
    if FAILURES:
        print("FAIL")
        for item in FAILURES:
            print("-", item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
