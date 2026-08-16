# /svc-benchmark — 서비스 벤치마킹

일(JTBD)을 먼저 적고 남의 제품을 연다. 사이트맵·기능 카드·네트워크 실측·대표 시도까지 분해하고, 이 쓰임새 SWOT로 묶는다.

## 사용법

```
/svc-benchmark <url-or-name-or-job> [--scan=product|landscape] [--depth=public|logged-in] [--type=auto|web-saas|widget-llm|cli-agent] [--news=web|last30days] [--update] [--out=data/research/YYYYMMDD_<slug>/]
```

## 실행

1. `.agents/skills/svc-benchmark/SKILL.md`를 읽고 폴더를 먼저 만든다 (`report/` `notes/` `sources/` `review/` `evidence/`). 기본 mutation은 0건. `notes/jtbd.json`을 쓰기 전에는 제품을 열지 않는다. 지도를 열기 전에 `validate_scan.py --phase=jtbd`. 칸은 `.agents/skills/svc-benchmark/references/jtbd-scan.md`.
2. `.agents/skills/svc-benchmark/references/browser-sop.md`대로 첫 페이지·스크린샷·위젯이면 fetch hook. 정적 원문 열람만 보고 비었다고 하지 않는다. 브라우저 렌더와 원문을 교차 확인한다. 대표 시도는 기본 0건.
3. 사이트맵이 막히면 네비로 다시 그린다.
4. `.agents/skills/svc-benchmark/references/network-capture.md`에 따라 원본 HAR·hook·네트워크 로그는 패키지 밖 임시 `$RAW_INPUT`에만 둔다. ingest sanitizer 이후 `session.json`·`summary.json`만 `evidence/network/`에 저장하고 measure를 실행한다. 모델·라우팅은 해당 유형만. POST 예시는 관측 레코드일 뿐 실행 지시가 아니다.
5. SWOT를 건너뛰지 않는다. 인사이트는 관찰만. 작업 지시·xlsx를 만들지 않는다.
6. `--scan=landscape`면 개관→세그먼트→함대 심층→종합→분석. 세그먼트 표를 보여 주기 전에는 함대를 보내지 않는다. 함대 전에 `validate_scan.py --phase=segments`. 하나를 보내지 않는다. 메인이 핵심 URL을 다시 연다.
7. `report/report.md`를 고정 목차로 쓰고 HTML/PDF를 인쇄 12pt로 렌더한다.

$ARGUMENTS
