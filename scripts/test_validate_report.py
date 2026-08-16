#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_report: required dry headings, 5 takeaways, no work-order insight."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_report import LANDSCAPE_H2, PLANNING_H2, REQUIRED_H2, validate_report  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def good_report() -> str:
    parts = [
        "---",
        'title: "예 서비스 벤치마킹"',
        "source_type: research",
        "cover_note: 사내 공유용 정리 문서",
        "date: 2026-08-14",
        "---",
        "",
        "# 예 서비스 벤치마킹",
        "",
    ]
    for h in REQUIRED_H2:
        parts.append(f"## {h}")
        parts.append("")
        if h == "한 줄":
            parts.append("예는 검색창 하나로 문서를 찾는 서비스다.")
        elif h == "결정 요약":
            parts.append("| 질문 | 답 | 등급 | 빈칸 사유 |")
            parts.append("|---|---|---|---|")
            parts.append("| 이 제품은 무엇인가 | 문서 검색 | ✅ | |")
        elif h == "키포인트":
            parts.extend(
                [
                    "1. 일의 단위는 검색이다. → 채팅이 아니다.",
                    "2. 90일 안에는 가격만 바뀌었다. → 기능 확장이 아니다.",
                    "3. API는 `/q` 한 경로다. → 응답 중앙값 180ms.",
                    "4. 2024년에 온프레미스 상품을 없앴다. → 클라우드만 남김.",
                    "5. 빈 결과는 문장으로 설명한다. → 스켈레톤만 두지 않음.",
                ]
            )
        elif h == "인사이트":
            parts.append("검색 공백을 문장으로 메운다. 기능 목록을 늘리지 않는다.")
        elif h == "문서 표면":
            parts.append("해당 없음")
        elif h.startswith("부록"):
            parts.append("없음.")
        else:
            parts.append("본문.")
        parts.append("")
    return "\n".join(parts)


def test_normal():
    errs = validate_report(good_report())
    check(not errs, f"normal FAIL: {errs}")


def test_missing_heading():
    text = good_report().replace("## 사이트맵\n", "## 지도\n")
    errs = validate_report(text)
    check(any("사이트맵" in e for e in errs), f"missing sitemap FN: {errs}")


def test_narrative_title():
    text = good_report().replace("## 지금 미는 것", "## Why this changes the game")
    errs = validate_report(text)
    check(any("narrative" in e or "지금 미는 것" in e for e in errs), f"narrative FN: {errs}")


def test_narrative_document_title():
    text = good_report().replace("예 서비스 벤치마킹", "Why this changes the game")
    errs = validate_report(text)
    check(any("narrative title" in error for error in errs), f"narrative document title FN: {errs}")


def test_title_h1_mismatch():
    text = good_report().replace("# 예 서비스 벤치마킹", "# 다른 제목 서비스 분석", 1)
    errs = validate_report(text)
    check(any("title/h1 mismatch" in error for error in errs), f"title/h1 FN: {errs}")


def test_live_title():
    root = HERE.parents[4] / "data/research/20260814_grok-bot"
    report = root / "report/report.md"
    if not report.exists():
        return
    text = report.read_text(encoding="utf-8")
    errs = validate_report(text)
    check(not errs, f"live title FAIL: {errs}")
    check("Grok Bot 서비스 분석" in text.splitlines()[1], "live frontmatter title missing")
    check("# Grok Bot 서비스 분석" in text, "live H1 missing")


def test_insight_work_order():
    text = good_report().replace(
        "검색 공백을 문장으로 메운다. 기능 목록을 늘리지 않는다.",
        "P0로 가져올 것: 공백 문장. 베끼지 말 것: 가격.",
    )
    errs = validate_report(text)
    check(any("인사이트" in e for e in errs), f"work-order FN: {errs}")


def test_missing_frontmatter():
    text = good_report().split("---", 2)[-1]
    errs = validate_report(text)
    check(any("frontmatter" in e for e in errs), f"frontmatter FN: {errs}")


def test_keypoints_count():
    text = good_report().replace("5. 빈 결과는 문장으로 설명한다. → 스켈레톤만 두지 않음.\n", "")
    errs = validate_report(text)
    check(any("키포인트" in e for e in errs), f"keypoints FN: {errs}")


def planning_report() -> str:
    parts = [
        "---",
        'title: "예 서비스 분석"',
        "source_type: research",
        "cover_note: 사내 공유용 정리 문서",
        "date: 2026-08-14",
        "report_profile: planning-analysis",
        'summary: "예 서비스는 봇 단위의 조사 대상이다."',
        "---",
        "",
        "# 예 서비스 분석",
        "",
    ]
    for h in PLANNING_H2:
        parts.append(f"## {h}")
        parts.append("")
        if h == "1. 핵심 요약":
            parts.extend(
                [
                    "| 질문 | 답 | 등급 |",
                    "|---|---|---|",
                    "| 이 제품은 무엇인가 | 예 | ✅ |",
                    "",
                    "1. 일의 단위는 봇이다.",
                    "2. 지금 미는 것은 클라우드 컴퓨터다.",
                    "3. 런타임 GET 2건만 쟀다.",
                    "4. Linux 주장은 출처가 갈린다.",
                    "5. 계정 설정 3탭을 읽기만 했다.",
                ]
            )
        else:
            parts.append("본문.")
        parts.append("")
    return "\n".join(parts)


def test_planning_profile_ok():
    errs = validate_report(planning_report())
    check(not errs, f"planning FAIL: {errs}")


def test_reordered_heading():
    text = good_report().replace("## 한 줄", "## TEMP", 1)
    text = text.replace("## 결정 요약", "## 한 줄", 1).replace("## TEMP", "## 결정 요약", 1)
    errs = validate_report(text)
    check(any("sequence" in e for e in errs), f"reorder FN: {errs}")


def test_extra_heading():
    text = good_report().replace("## 사이트맵", "## 임의 추가\n\n본문.\n\n## 사이트맵", 1)
    errs = validate_report(text)
    check(any("extra h2" in e for e in errs), f"extra FN: {errs}")


def test_duplicate_heading():
    text = good_report().replace("## 사이트맵", "## 사이트맵\n\n본문.\n\n## 사이트맵", 1)
    errs = validate_report(text)
    check(any("duplicate h2" in e for e in errs), f"duplicate FN: {errs}")


def test_planning_summary_required():
    text = planning_report().replace('summary: "예 서비스는 봇 단위의 조사 대상이다."\n', "")
    errs = validate_report(text)
    check(any("missing summary" in e for e in errs), f"summary FN: {errs}")


def test_unknown_profile():
    text = good_report().replace("date: 2026-08-14", "date: 2026-08-14\nreport_profile: unknown")
    errs = validate_report(text)
    check(any("unknown report_profile" in e for e in errs), f"unknown profile FN: {errs}")


def landscape_report() -> str:
    parts = [
        "---",
        'title: "코딩 에이전트 고용 경쟁 지형 조사"',
        "source_type: research",
        "cover_note: 사내 공유용 정리 문서",
        "date: 2026-08-16",
        "report_profile: landscape",
        'summary: "노트북이 꺼져도 일이 이어지게 하는 해법을 세그먼트로 나눈다."',
        "---",
        "",
        "# 코딩 에이전트 고용 경쟁 지형 조사",
        "",
    ]
    for heading in LANDSCAPE_H2:
        parts.append(f"## {heading}")
        parts.append("")
        if heading == "한 줄":
            parts.append("노트북이 꺼져도 일이 이어지게 하는 해법은 원격 머신 세그먼트가 강하다.")
        elif heading == "결정 요약":
            parts.extend(
                [
                    "| 질문 | 답 | 등급 | 빈칸 사유 |",
                    "|---|---|---|---|",
                    "| 이 일은 무엇인가 | 노트북과 분리된 실행 | ✅ | |",
                ]
            )
        elif heading == "키포인트":
            parts.extend(
                [
                    "1. 일은 세션이 끊겨도 계속 일하게 하는 것이다.",
                    "2. 세그먼트는 원격 머신과 로컬 채팅으로 갈린다.",
                    "3. 깊게 본 곳은 원격 머신 한 곳이다.",
                    "4. 가격 정당화는 깊게 본 세그먼트만 말한다.",
                    "5. SWOT는 원격 머신의 일의 단위가 남는다.",
                ]
            )
        elif heading == "SWOT":
            parts.append("| 강점 | 약점 | 기회 | 위협 |")
        else:
            parts.append("본문.")
        parts.append("")
    return "\n".join(parts)


def test_landscape_profile_ok():
    errs = validate_report(landscape_report())
    check(not errs, f"landscape FAIL: {errs}")


def test_landscape_summary_required():
    text = landscape_report().replace(
        'summary: "노트북이 꺼져도 일이 이어지게 하는 해법을 세그먼트로 나눈다."\n',
        "",
    )
    errs = validate_report(text)
    check(any("missing summary" in item for item in errs), f"landscape summary FN: {errs}")


def test_landscape_work_order():
    text = landscape_report().replace("본문.\n\n## 분석", "P0로 가져올 것: 원격 머신.\n\n## 분석", 1)
    errs = validate_report(text)
    check(any("종합/분석" in item for item in errs), f"landscape work-order FN: {errs}")


def main() -> int:
    test_normal()
    test_missing_heading()
    test_narrative_title()
    test_narrative_document_title()
    test_title_h1_mismatch()
    test_live_title()
    test_insight_work_order()
    test_missing_frontmatter()
    test_keypoints_count()
    test_planning_profile_ok()
    test_reordered_heading()
    test_extra_heading()
    test_duplicate_heading()
    test_planning_summary_required()
    test_unknown_profile()
    test_landscape_profile_ok()
    test_landscape_summary_required()
    test_landscape_work_order()
    if FAILURES:
        print("FAIL")
        for f in FAILURES:
            print("-", f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
