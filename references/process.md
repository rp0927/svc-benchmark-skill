# 실행 프로세스

이 파일이 프로세스 정본이다. SKILL.md는 라우팅·금지·게이트 명령만 둔다. 칸 정의는 [jtbd-scan.md](jtbd-scan.md), 목차는 [report-contract.md](report-contract.md).

기준 런: Amp(2026-08-14), PRizmo(2026-08-13), Grok Bot(2026-08-14). 잘 된 이웃 스킬: `svc-planning`, `korea-financial-benchmark`, `doc-autoaudit`, `last30days`, `korean-prose-editor`.

## 한 줄

남의 제품을 열어 관측을 남긴다. 우리 기획서와 재무 표는 만들지 않는다.

## 흐름

```text
0  로컬 선행물 훑기
1  질문 확정 (지형 vs 필요·가격) + 폴더 + 사전 점검
2  일(JTBD) 기록 → --phase=jtbd
3  수집
     product   : 지도 → 표면 → 카드 → 지금 미는 것 → 소식 → 문서 → 런타임 → 쿼리 → 최신
     landscape : 개관 → 세그먼트 표 → --phase=segments → 함대 → 메인 재확인 → 종합 → 분석
4  SWOT
5  report.md + close 게이트 + 렌더
```

단계를 건너뛰고 검색만으로 보고서를 쓰지 않는다. 함대 자기보고를 원문으로 쓰지 않는다.

## 0. 로컬 선행물

인터넷보다 이 워크스페이스를 먼저 본다. `svc-planning` Phase 0.5와 같다.

```bash
ls data/research | rg -i "<대상|일 키워드>"
rg -il "<대상>" data/research data/wiki/articles 2>/dev/null | head -8
```

같은 대상의 이전 벤치가 있으면 `--update`인지 신규인지 사용자에게 고르게 한다. 재무 수치가 필요하면 `korea-financial-benchmark`로 넘긴다. 우리 서비스 SWOT·xlsx는 `svc-planning`이다.

`notes/precheck.json`에 찾은 경로와 `reuse`를 적는다. 0건이면 `reuse: none`.

## 1. 질문과 폴더

한 번에 질문 하나만 던지고 권고를 붙인다.

- URL 한 건 → `--scan=product`, `question=need-vs-price`
- 일·시장 → `--scan=landscape`, `question=landscape`

`--depth`는 로그인 여부다. 조사 넓이와 섞지 않는다.

`init_run.py` 직후 `notes/failures.json` `preflight`에 브라우저·수집기 한 줄을 적는다. 브라우저가 없어도 문서만으로 이어간다.

## 2. 일

`notes/jtbd.json`의 `job`이 비어 있으면 지도를 열지 않는다.

```bash
python3 "$SKILL/scripts/validate_scan.py" --root . --phase=jtbd
```

고객이 없으면 가설 1건 이상. 그 가설로 `competitor` / `alternative` / `out`을 가른다.

## 3. 수집

기본 mutation은 0건. 대표 시도·대표 질의도 기본 0건.

제품 한 건은 SKILL 1–10. 사이트맵이 로그인 뒤면 `sitemap-behind-login`을 남기고 네비로 다시 그린다. 정적 원문이 비어도 위젯을 빈 제품으로 보지 않는다 (`static-empty-widget`).

지형은 세그먼트 표를 보여 준 뒤에만 함대를 연다. 동시 3명. 2차 글을 원문으로 쓰지 않는다.

```bash
python3 "$SKILL/scripts/validate_scan.py" --root . --phase=segments
```

수치는 출처 층으로 적는다. 대상 서비스 AI 화면 숫자는 원천이 아니다.

| 층 | 쓰는 곳 | 예 |
|---|---|---|
| 1차 | 단정 | 연 페이지, 공식 문서, 승인된 GET |
| 2차 | 할인 | changelog 인용, 리뷰 |
| 힌트 | 단정 금지 | 검색 스니펫, 에이전트 요약, 대상 AI 답변 |

빈칸은 지우고 넘어가지 않는다. `missing_reason`을 남긴다.

## 4. SWOT

건너뛰지 않는다. 관측한 제품 또는 일이다. 계획·바람을 강점에 넣지 않는다. 위협이 읽기 편하면 아직 아니다.

`notes/swot.json` 네 칸 → 보고서 표. `benchmark`는 인사이트 절, `landscape`는 H2 `SWOT`.

## 5. 보고서와 닫기

결정본은 `report/report.md`. 프로필 목차는 [report-contract.md](report-contract.md). 기본 `benchmark` H2는 바꾸지 않는다.

인사이트에 P0 작업 목록, “가져올 것”, 기획 xlsx를 넣지 않는다. Amp 초안의 그 절은 버린 계약이다.

```bash
python3 "$SKILL/scripts/validate_scan.py" --root . --phase=close
```

나머지 close 명령은 SKILL 12단계. 게이트 출력 요약을 `notes/skill-notes.md`에 남긴다.

## 필수 산출

| 경로 | product | landscape | 비면제 조건 |
|---|---|---|---|
| `run.json` | 필수 | 필수 | `scan`, `mutations_allowed=[]` |
| `notes/precheck.json` | 필수 | 필수 | 0건이면 `reuse: none` |
| `notes/jtbd.json` | 필수 | 필수 | `job` 비면제. 고객 없으면 가설 |
| `notes/swot.json` | 필수 | 필수 | 네 칸 |
| `notes/failures.json` | 필수 | 필수 | `preflight` + 난 일의 `events` |
| `notes/segments.json` | 선택 | 필수 | 함대 전 1건 이상 |
| `notes/sitemap.md` | 필수 | 깊은 제품만 | `job` 이후 |
| `notes/feature-cards.json` | 필수 | 깊은 제품만 | 빈칸에 `missing_reason` |
| `notes/sources.json` | 필수 | 필수 | 인용 URL |
| `notes/skill-notes.md` | 권고 | 권고 | 게이트 요약 |
| `report/report.md` | 필수 | 필수 | 프로필 목차 |
| `sources/audit-manifest.json` | 필수 | 필수 | claim→출처 |
| `evidence/` | 관측한 것만 | 관측한 것만 | 원시 HAR는 패키지 밖 |
| `notes/handoff.md` | 세션이 넘길 때만 | 같음 | 아직 칸만 예정 |
| `notes/our-job.json` | 우리 제품과 견줄 때만 | 같음 | 없으면 가격 비교 문장 금지 |

## 넣지 않는 것

- 기본 목차에 기획 15항. 자리는 `planning-analysis`와 `svc-planning`
- 인사이트에 작업 지시
- Firecrawl·belt를 기본 의존으로
- caveman 문체를 보고서 산문에
- `competitor-watch` 뉴스 모드를 해체로 대체하기
- last30days 엔진 출력을 본문에 복사하기

## 이웃 스킬

| 스킬 | 이 스킬과의 경계 |
|---|---|
| `svc-planning` | 우리 서비스 기획 xlsx. 벤치 인사이트에서 호출하지 않는다 |
| `competitor-watch` | 7–30일 동향. 제품 해체는 여기로 넘긴다 |
| `korea-financial-benchmark` | 공시·재무 수치 |
| `last30days` | `--news=last30days` 훅. 인용 표만 |
| `doc-autoaudit` | 보고서 팩트·시각 게이트 |
| `korean-prose-editor` | 한국어 산문 윤문 |
