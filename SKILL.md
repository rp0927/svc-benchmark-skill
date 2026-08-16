---
name: svc-benchmark
version: "0.2.0"
homepage: https://github.com/rp0927/svc-benchmark-skill
repository: https://github.com/rp0927/svc-benchmark-skill
description: "남의 서비스를 열어 사이트맵·기능 카드·네트워크 실측·대표 시도까지 분해한다. JTBD로 경쟁과 대안을 가른 뒤 SWOT로 정리한다. 트리거 — 서비스 벤치마킹, 기능 해체, teardown, 사이트맵, 최신 기능 검증, JTBD, 경쟁 지형."
---

# svc-benchmark

일(JTBD)을 먼저 적고 남의 제품을 연다. 지도와 기능 카드, 지금 미는 것, 런타임에서 보인 것을 적는다. 통찰은 SWOT로 묶는다. 인사이트는 관찰이다. 작업 지시가 아니다.

`$SKILL`은 이 파일이 있는 디렉터리다.

- 카드: [references/feature-card.md](references/feature-card.md)
- 보고서: [references/report-contract.md](references/report-contract.md)
- 조사 뼈대: [references/jtbd-scan.md](references/jtbd-scan.md)
- 프로세스: [references/process.md](references/process.md)
- 출처 감사: [references/source-audit.md](references/source-audit.md)
- 유형: [references/product-modules.md](references/product-modules.md)
- 안전: [references/safety.md](references/safety.md)
- 런 교훈: [references/run-lessons.md](references/run-lessons.md)
- 브라우저: [references/browser-sop.md](references/browser-sop.md)
- 네트워크: [references/network-capture.md](references/network-capture.md)

## 언제 쓰는가

- 특정 서비스를 벤치마킹할 때
- 일(JTBD) 기준으로 진짜 경쟁과 쓰임새의 강한 대안을 가를 때
- `/svc-planning` 전에 경쟁 제품의 실제 표면이 필요할 때
- `/competitor-watch`의 뉴스 모드가 아니라 제품 해체가 필요할 때

경계:

- `competitor-watch` — 동향·펀딩. teardown은 이 스킬로 넘긴다
- `svc-planning` — 우리 서비스를 기획한다. 우리 SWOT·xlsx는 그쪽. 이 스킬의 SWOT는 관측한 제품/일
- `korea-financial-benchmark` — 재무 수치가 필요하면 위임
- `deep-research` — 시장 장문. 제품 해체가 아니다

## TFG

Level 2. 시작 전에 확인한다. 한 번에 질문 하나만 던지고 권고를 붙인다. 이미 코드로 아는 값은 묻지 않는다.

1. 이해한 요청: 일(JTBD), 대상 URL·이름, `--scan`, 깊이, 유형
2. 출력 형식: `data/research/YYYYMMDD_<slug>/`의 report / notes / sources / review / evidence
3. 예상 규모: 세그먼트·페이지·카드·공개 GET 수
4. 예상 소요
5. 이번 질문: 지형만 볼까요, 필요·가격까지 깊게 볼까요? 권고: URL 한 건이면 `--scan=product`·need-vs-price, 일·시장이면 `--scan=landscape`. 답을 받기 전에는 6–7을 묻지 않는다
6. 누가 읽는 문서인가요? 권고: 사내 공유용 정리 문서
7. 성공 기준은 무엇인가요? 권고: 연 페이지로 확인한 기능·가격만 단정

기본 mutation은 0건. 공개 GET·정적 페이지·기존 화면 열람만 무승인 read-only다.

## 입력

```text
/svc-benchmark <url-or-name-or-job>
  --scan=product
  --depth=public
  --type=auto
  --update
  --news=web
  --out=data/research/YYYYMMDD_<slug>/
```

`--scan`: `product`(기본, 한 제품) / `landscape`(일 기준 지형). 칸은 [jtbd-scan.md](references/jtbd-scan.md)

`--depth`: `public`(기본) / `logged-in`(사용자 세션이 있을 때만). 조사 넓이와 섞지 않는다

`--type`: `web-saas` / `widget-llm` / `cli-agent` / `auto`

`--news`: `web`(기본) / `last30days`(선택 훅. 엔진 출력을 보고서에 복사하지 않음)

`--out`을 생략하면 `data/research/YYYYMMDD_<영문-kebab>/`

금지: [references/safety.md](references/safety.md)

## 시작: 폴더를 먼저 만든다

다른 단계를 시작하기 전에 출력 루트를 만들고 `run.json`을 쓴다. 덤프를 루트에 쌓지 않는다.

프로젝트 루트에서 `PROJECT_ROOT`와 `SKILL`, 절대경로 `OUT`을 정한 뒤 init_run을 실행하고, `cd "$OUT"`한 다음 패키지 상대 경로(notes/report/sources)와 `$PROJECT_ROOT` 공유 명령을 실행한다. 새 worktree는 만들지 않는다.

```text
data/research/YYYYMMDD_<slug>/
  run.json
  report/                 # 결정본 md/html/pdf
  notes/                  # 해석·카드·사이트맵·스킬 노트
  sources/                # 감사 원장
  review/                 # 문서 리뷰
  evidence/
    screenshots/
    cli/
    queries/
    network/
    docs/
```

```bash
PROJECT_ROOT="$(pwd)"
SKILL="$PROJECT_ROOT/.agents/skills/svc-benchmark"
OUT="$PROJECT_ROOT/data/research/YYYYMMDD_<slug>"
python3 "$SKILL/scripts/init_run.py" --out "$OUT" \
  --target "<url-or-name-or-job>" --scan product --depth public --type auto
cd "$OUT"
```

시작 직후 로컬 선행물을 훑고 `notes/precheck.json`을 채운다. `notes/failures.json`의 `preflight`에 브라우저·수집기 상태를 한 줄로 적는다. 브라우저가 없어도 문서만으로 런을 이어간다. 순서는 [process.md](references/process.md).

`--update`면 이전 런의 `notes/feature-cards.json`과 `notes/timeline.json`을 읽고 `run.json.prev_run`에 경로를 적는다.

## 13단계

배치 규칙은 `--quick`과 무관하다. 첫 페이지·첫 시도 후 나머지. 병렬은 동시 3개.

`--scan=landscape`면 [jtbd-scan.md](references/jtbd-scan.md)의 개관→세그먼트→심층→종합→분석 순서를 먼저 닫고, 깊게 보는 제품만 아래 1–10을 쓴다. 세그먼트 표(`notes/segments.json`)를 보여 주기 전에는 함대를 보내지 않는다. 하나를 보내지 않는다. 기본 `--scan=product`도 0단계에서 일을 적기 전에는 지도를 그리지 않는다. SWOT는 건너뛰지 않는다.

### 0. 범위와 금지

대상, 일, `--scan`, 깊이, 유형, 출력 경로. `mutations_allowed`는 빈 배열. 일을 `notes/jtbd.json`에 쓰기 전에는 1단계로 가지 않는다. 칸은 [jtbd-scan.md](references/jtbd-scan.md). 고객이 없으면 얕은 조사로 가설만 만들고, 그 가설로 진짜 경쟁과 쓰임새의 강한 대안을 가른다. 난 일은 `notes/failures.json`에 이름으로 적는다. 스킬 단계를 건너뛰고 검색만으로 보고서를 쓰지 않는다.

`job`을 채운 뒤, 지도를 열기 전에:

```bash
python3 "$SKILL/scripts/validate_scan.py" --root . --phase=jtbd
```

`--scan=landscape`면 함대를 열기 전에:

```bash
python3 "$SKILL/scripts/validate_scan.py" --root . --phase=segments
```

기본 mutation은 0건이다. 공개 GET·정적 페이지·기존 화면 열람만 무승인 read-only로 허용한다. 비파괴 POST·폼 제출·유료 추론·로그인·공식 설치는 사용자의 명시 승인과 `run.json` `mutations_allowed`에 정확한 액션이 있을 때만 실행한다. 메시지 전송, 결제, 로그아웃, 삭제, Reset, 그 밖의 파괴적 작업, 새 worktree 생성·사용은 승인이나 `mutations_allowed`로도 허용하지 않는다. 대표 시도·대표 질의는 기본 0건이며 미승인 시 docs-only 또는 기존 결과 관측으로 남긴다.

### 1. 지도

1. `robots.txt`, `sitemap.xml`. 막히면 막힌 사실을 기록한다. 실패가 정상일 수 있다
2. 홈 네비, 푸터, changelog로 IA를 다시 그린다
3. 여러 호스트면 호스트별로 나눈다
4. 공개 / 로그인 필요 / noindex를 가른다

```bash
python3 "$SKILL/scripts/collect_surface.py" \
  --robots evidence/docs/robots.txt \
  --sitemap evidence/docs/sitemap.xml \
  --html evidence/docs/home.html \
  --out notes/sitemap.md
```

산출: `notes/sitemap.md`

### 2. 표면 순회 + 첫 시도

절차는 [references/browser-sop.md](references/browser-sop.md). 정적 원문 열람만 보고 비었다고 하지 않는다. 브라우저 렌더와 원문을 교차 확인한다.

1. 첫 페이지만 연다. 렌더·경로·위젯 여부를 확인한다
2. 위젯이면 탐색 전에 fetch hook을 건다
3. 대표 시도는 기본 0건. 승인·`mutations_allowed`가 없으면 보내지 않고 docs-only 또는 기존 화면 관측만 남긴다
4. 승인된 시도가 있으면 그 네트워크를 `evidence/network/`에 남긴다 ([network-capture.md](references/network-capture.md))
5. 나머지 공개 페이지를 돈다. 페이지마다 스크린샷. 가능하면 접근성 스냅샷
6. 마케팅과 제품 UI가 다르면 공식 이미지는 `official-image`
7. 스크린샷은 넣기 전에 줄인다

```bash
bash "$SKILL/scripts/prep_images.sh" evidence/screenshots
```

산출: `evidence/screenshots/`

### 3. 기능 카드

칸은 [references/feature-card.md](references/feature-card.md). 삭제한 기능도 남긴다. 브랜드 명사는 `id`로 고정한다.

```bash
python3 "$SKILL/scripts/validate_cards.py" notes/feature-cards.json
```

산출: `notes/feature-cards.json`

### 4. 지금 미는 것

최근 30–90일 공식 릴리스. 한 문장 전략 + 날짜 표. 6개월 전 리뷰는 날짜를 붙여 할인한다.

### 5. 외부 소식 + 역사

공식 RSS/changelog + 웹 검색 30–90일. `--news=last30days`면 그 스킬을 호출하고 `notes/external.md`에 인용 표만 넣는다.

역사는 `notes/timeline.json`. 본문은 표. 연대기 산문은 쓰지 않는다.

```json
{"date": "2025-12-02", "event": "분사", "source": "https://...", "kind": "spinout"}
```

`kind`: `founding` | `spinout` | `launch` | `delete` | `price` | `incident`

### 6. 문서 표면

changelog와 매뉴얼이 제품이면 한 번 더 분해한다. 뉴스와 가이드를 한 페이지에 섞지 않는다.

산출: `notes/docs.md` (해당할 때만. 헤딩은 보고서에 남긴다)

### 7. 클라이언트 실측

설치형 CLI·TUI·SDK는 이미 설치된 바이너리만 읽기 전용으로 덤프한다. 도움말, 설정 키, 도구 목록은 명령마다 다시 찍는다. 시크릿 값은 보고서에 붙이지 않는다. 공식 설치는 사용자의 명시 승인과 `mutations_allowed`에 정확한 설치 액션이 둘 다 있기 전에는 지시하지 않는다. execute·init·쓰기 명령도 같은 두 게이트가 필요하다.

```bash
python3 "$SKILL/scripts/collect_cli.py" \
  --bin <binary> --surface=--help --out evidence/cli --notes notes/cli.md
```

산출: `notes/cli.md` + `evidence/cli/`

### 8. 런타임 실측

일반 필수. 모델·라우팅은 특수 모듈이다.

**일반 — 모든 유형**

공개 GET과 승인된 호출에서. 미승인 POST는 하지 않는다.

- 호스트, 메서드, 경로, 상태 코드
- TTFB·전체 왕복(ms). 스트림이면 첫 바이트와 종료를 나눈다
- 요청·응답 헤더 이름. 값은 시크릿만 삭제
- 콘텐츠 타입, 페이로드 키 이름 (값 전문은 필요 최소)
- 리다이렉트, CDN, 인증 게이트(302 로그인)

```bash
RAW_TMP_DIR="${RAW_TMP_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/svc-benchmark-network.XXXXXX")}"
RAW_INPUT="${RAW_INPUT:-$RAW_TMP_DIR/raw.json}"
test -f "$RAW_INPUT"
python3 "$SKILL/scripts/ingest_network.py" \
  "$RAW_INPUT" --out evidence/network/session.json
python3 "$SKILL/scripts/measure_network.py" \
  --har evidence/network/session.json \
  --out notes/runtime.md --json evidence/network/summary.json
```

수집 명령은 [references/network-capture.md](references/network-capture.md). HAR도 패키지 밖 `$RAW_INPUT`에 두고 ingest sanitizer를 거쳐 `session.json`으로 저장한다. 원본 HAR를 직접 통과시키지 않는다.

**특수 — `widget-llm` / `cli-agent`만**

모델명 7단, 다이얼→모델 카드, 구독 스왑, 페르소나 재구성. 판정은 [references/product-modules.md](references/product-modules.md). 일반 SaaS는 이 소절을 `해당 없음`으로 둔다.

산출: `notes/runtime.md` + `evidence/network/`

### 9. 대표 쿼리

대표 질의는 기본 0건이다. 승인과 `mutations_allowed`에 정확한 액션이 없으면 실행하지 않고 docs-only 또는 기존 결과 관측으로 남긴다.

승인이 있을 때만 매뉴얼·공식 예제에서 표면이 다른 쿼리를 고른다. 2단계와 같은 표면을 반복하지 않는다.

1. 다음 1건을 실행하고 경로·오류·스레드 ID를 남긴다
2. 정상이면 나머지. 과금 게이트면 오류를 남기고 같은 실패를 반복하지 않는다
3. 쓰기 없으면 “Do not edit any files.”

산출: `notes/queries.md` + `evidence/queries/`

### 10. 최신 기능 검증

changelog가 “방금 냈다”고 한 것만. 9와 섞지 않는다.

클레임 → 명령 또는 URL → 관측 → 판정

`열림` / `일부` / `막힘` / `문서만`

산출: `notes/latest-verify.md`

### 11. 인사이트

관찰만 적는다. P0 작업 목록, “가져올 것”, svc-planning xlsx를 만들지 않는다. 쓰기 규칙은 [references/report-contract.md](references/report-contract.md). 이 쓰임새 SWOT를 `notes/swot.json`에 쓰고 인사이트 표로 옮긴다. 칸은 [jtbd-scan.md](references/jtbd-scan.md). 건너뛰지 않는다. `--scan=landscape`면 종합·분석을 먼저 닫고 SWOT로 묶는다.

### 12. 마무리

1. `notes/`를 모아 `report/report.md`를 쓴다
2. 패키지 상대 경로 게이트와 `$PROJECT_ROOT` 공유 게이트:

```bash
python3 "$SKILL/scripts/validate_report.py" report/report.md
python3 "$SKILL/scripts/validate_scan.py" --root .
python3 "$SKILL/scripts/validate_cards.py" notes/feature-cards.json
python3 "$SKILL/scripts/validate_coverage.py" --report report/report.md --cards notes/feature-cards.json
python3 "$SKILL/scripts/validate_sources.py" --report report/report.md --sources notes/sources.json
python3 "$SKILL/scripts/validate_privacy.py" --root .
python3 "$SKILL/scripts/validate_audit.py" --root .
python3 "$PROJECT_ROOT/.agents/skills/doc-autoaudit/scripts/audit_gate.py" \
  sources/audit-fact.json sources/audit-visual.json \
  --manifest sources/audit-manifest.json
```

`report_profile`이 `planning-analysis`면 기획 15항 목차를 검사한다. `landscape`면 지형 목차이고 coverage는 건너뛴다. 기본은 `benchmark`.
3. 한국어 산문이면 `korean-prose-editor`. 한다체 분석은 `purpose=explainer` (report 팩의 합니다체와 충돌)
4. 렌더

```bash
node "$PROJECT_ROOT/.agents/skills/_output-rules/convert.js" \
  report/report.md report/ \
  --mode=research \
  --css="$SKILL/assets/print-large.css" \
  --pdf-config="$SKILL/assets/pdf-config-report.json"
python3 "$PROJECT_ROOT/.agents/scripts/validate-pdf-output.py" report/report.html
```

5. 절차가 틀린 지점은 `notes/skill-notes.md`

폰트: CSS는 12pt. SUIT를 쓰면 절대경로 + `!important`. `{{FONT_DIR}}`는 치환되지 않는다.

## 게이트

- Evidence Gate: 연 페이지 또는 fetch 원문 없이 완료 선언 금지
- 일(JTBD) 없이 기능 목록으로 시작 금지. 지도 전에 `--phase=jtbd`, 함대 전에 `--phase=segments`
- SWOT 생략 금지. 에이전트 자기보고를 원문 확인으로 쓰지 않는다. 실패는 `notes/failures.json`에 이름으로 적는다
- 스크린샷 없는 카드는 `evidence.observed=docs-only`
- “경쟁사는 X를 못한다”는 해당 사이트 확인 전 금지
- 한국어 산문에 korean-prose 게이트
- mutation 목록을 부록 B에 남긴다. 기본은 0건. 메시지·결제·로그아웃·삭제·Reset·파괴적 작업·새 worktree는 승인으로도 실행하지 않는다
- 일회용 로그인 URL·토큰은 덤프에서 지운다
- `--update`는 `id` diff만 본문에 쓴다. 전체를 다시 쓰지 않는다

## 테스트

```bash
python3 "$SKILL/scripts/test_init_run.py"
python3 "$SKILL/scripts/test_collect_surface.py"
python3 "$SKILL/scripts/test_validate_cards.py"
python3 "$SKILL/scripts/test_validate_report.py"
python3 "$SKILL/scripts/test_measure_network.py"
python3 "$SKILL/scripts/test_ingest_network.py"
python3 "$SKILL/scripts/test_validate_coverage.py"
python3 "$SKILL/scripts/test_validate_sources.py"
python3 "$SKILL/scripts/test_validate_privacy.py"
python3 "$SKILL/scripts/test_validate_audit.py"
python3 "$SKILL/scripts/test_validate_scan.py"
python3 "$SKILL/scripts/test_collect_cli.py"
python3 "$SKILL/scripts/test_skill_step12_gates.py"
```

순수 python/stdlib. 네트워크 없음.
