#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check report.md headings, dry titles, and front-matter sections."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_H2 = (
    "한 줄",
    "결정 요약",
    "키포인트",
    "조사 범위와 한계",
    "정체와 역사",
    "사이트맵",
    "기능 카드",
    "지금 미는 것",
    "외부 소식",
    "문서 표면",
    "런타임 실측",
    "대표 쿼리",
    "최신 기능 검증",
    "인사이트",
    "참고 자료",
    "부록 A. 절차 노트",
    "부록 B. 미실행 mutation",
)

LANDSCAPE_H2 = (
    "한 줄",
    "결정 요약",
    "키포인트",
    "조사 범위와 한계",
    "할 일 (JTBD)",
    "시장 개관",
    "솔루션 세그먼트",
    "세그먼트 관측",
    "종합",
    "분석",
    "SWOT",
    "참고 자료",
    "부록 A. 절차 노트",
    "부록 B. 미실행 mutation",
)

PLANNING_H2 = (
    "1. 핵심 요약",
    "2. 조사 범위와 읽는 법",
    "3. 핵심 컨셉 *",
    "4. 타겟 세그먼트",
    "5. 기능",
    "6. 핵심 기능",
    "7. 경쟁력 *",
    "8. 환경 분석",
    "9. SWOT",
    "10. 개발 기간",
    "11. 자본·운영 비용",
    "12. 사업 모델",
    "13. 목표 *",
    "14. 성공 요인 *",
    "15. 승계 자산",
    "16. 플랫폼·글로벌·확장",
    "17. 미해결 문제",
    "18. 외부 소식 분석",
    "19. 관측 증거",
    "20. 버전과 기준점",
    "21. 이용 시나리오",
    "22. 가상 FGI",
    "23. 참고 자료",
    "부록 A. 화면 별첨",
    "부록 B. 절차 노트",
    "부록 C. 미실행 mutation",
)

PROFILES = {
    "benchmark": REQUIRED_H2,
    "landscape": LANDSCAPE_H2,
    "planning-analysis": PLANNING_H2,
}

FRONTMATTER_KEYS = ("title", "source_type", "cover_note", "date")

NARRATIVE_H2 = re.compile(
    r"^(why|how|what if|the [a-z].{8,}|why we|어떻게 .{2,}하는가|왜 .{2,}인가|"
    r".{0,40}(바꾸는|바꿔 놓는|미래|한 가지|놓치면)\s*$)",
    re.I,
)
SLOGAN_BITS = ("changes the game", "바꾸는 미래", "우리가 놓치면", "반드시 알아야")
TITLE_GENRE = re.compile(r"(벤치마킹|분석|해체|조사|관측)")


def parse_h1(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# ") and not line.startswith("## "):
            return line[2:].strip()
    return ""


def title_contract_errors(title: str, h1: str) -> list[str]:
    errors: list[str] = []
    if not h1:
        errors.append("missing h1")
    elif title and title != h1:
        errors.append(f"title/h1 mismatch: {title!r} vs {h1!r}")
    for label, value in (("title", title), ("h1", h1)):
        if not value:
            continue
        if NARRATIVE_H2.match(value) or any(bit in value.lower() for bit in SLOGAN_BITS):
            errors.append(f"narrative title: {value}")
        if value.endswith("?") or value.endswith("？"):
            errors.append(f"question title: {value}")
        if not TITLE_GENRE.search(value):
            errors.append(f"title is not descriptive: {value}")
    return errors


def parse_h2(text: str) -> list[str]:
    found: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("###"):
            found.append(line[3:].strip())
    return found


def extract_section(text: str, title: str) -> str:
    pat = re.compile(rf"^## {re.escape(title)}\s*$", re.M)
    m = pat.search(text)
    if not m:
        return ""
    rest = text[m.end() :]
    nxt = re.search(r"^## ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    block = text[3:end]
    data: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def validate_report(text: str) -> list[str]:
    errors: list[str] = []
    fm = parse_frontmatter(text)
    profile = "benchmark"
    if fm is None:
        errors.append("missing yaml frontmatter")
    else:
        for key in FRONTMATTER_KEYS:
            if not fm.get(key):
                errors.append(f"frontmatter missing {key}")
        raw_profile = (fm.get("report_profile") or "benchmark").strip()
        if raw_profile not in PROFILES:
            errors.append(f"unknown report_profile: {raw_profile}")
        else:
            profile = raw_profile
        if raw_profile in {"planning-analysis", "landscape"} and not fm.get("summary"):
            errors.append(f"frontmatter missing summary for {raw_profile}")
        errors.extend(title_contract_errors(fm.get("title") or "", parse_h1(text)))
    required = PROFILES.get(profile, REQUIRED_H2)
    h2 = parse_h2(text)
    missing = [title for title in required if title not in h2]
    extra = [title for title in h2 if title not in required]
    duplicates = sorted({title for title in h2 if h2.count(title) > 1})
    for title in missing:
        errors.append(f"missing h2: {title}")
    for title in extra:
        errors.append(f"extra h2: {title}")
    if duplicates:
        errors.append("duplicate h2: " + ", ".join(duplicates))
    if h2 != list(required):
        errors.append(f"h2 sequence must exactly match profile {profile}")
    for title in h2:
        if NARRATIVE_H2.match(title) or any(bit in title.lower() for bit in SLOGAN_BITS):
            errors.append(f"narrative title: {title}")
        if title.endswith("?") or title.endswith("？"):
            errors.append(f"question title: {title}")

    if profile in {"benchmark", "landscape"}:
        summary = extract_section(text, "결정 요약")
        if summary and "|" not in summary:
            errors.append("결정 요약: table missing")
        keys = extract_section(text, "키포인트")
        numbered = re.findall(r"^\s*\d+\.\s+\S", keys, flags=re.M)
        if keys and len(numbered) < 5:
            errors.append(f"키포인트: need 5 numbered items, found {len(numbered)}")
        insight_title = "인사이트" if profile == "benchmark" else None
        insight = extract_section(text, insight_title) if insight_title else (
            extract_section(text, "종합") + extract_section(text, "분석")
        )
        banned = ("P0", "P1", "가져올 것", "베끼지 말 것", "svc_plan", "xlsx")
        label = "인사이트" if profile == "benchmark" else "종합/분석"
        for bit in banned:
            if bit in insight:
                errors.append(f"{label}: work-order language ({bit})")
        one = extract_section(text, "한 줄").strip()
        if one and len(one) > 400:
            errors.append("한 줄: too long")
    else:
        summary = extract_section(text, "1. 핵심 요약")
        if summary and "|" not in summary:
            errors.append("핵심 요약: table missing")
        numbered = re.findall(r"^\s*\d+\.\s+\S", summary, flags=re.M)
        if summary and len(numbered) < 5:
            errors.append(f"핵심 요약: need 5 numbered keypoints, found {len(numbered)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("path", type=Path)
    args = p.parse_args(argv)
    try:
        text = args.path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL: {exc}")
        return 1
    errors = validate_report(text)
    if errors:
        print("FAIL")
        for e in errors:
            print(f"- {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
