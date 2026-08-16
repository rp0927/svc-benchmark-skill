# svc-benchmark 고도화 계획

- 날짜: 2026-08-16
- 범위: 사본 정리 + 외부 인기 스킬 조사 + 채택점 + 단계 계획
- 대상 스킬: `.agents/skills/svc-benchmark/`

설치 수는 2026-08-16 [skills.sh](https://www.skills.sh/) 표시값이다. `npx skills add` 텔레메트리라 고유 사용자 수와 같지 않다. Hacker News에서도 이 순위가 설치 도구 편향을 탄다는 지적이 있다. 아래는 순위가 아니라 **벤치 스킬이 배울 절차**를 고른 목록이다.

## 1. 사본 정리

`.claude/skills/svc-benchmark/references/`는 정본이 아니다. Claude `SKILL.md`는 이미 `.agents`를 가리킨다.

한 번 폴더를 비우다가 심볼릭을 따라 정본이 지워졌다. 세션 rewind·도구 기록으로 9개 참조 파일을 되돌리고, 테스트 13개를 다시 통과시켰다. `browser-sop`·`network-capture`·`product-modules`는 후기 계약(원시 HAR는 패키지 밖, 대표 시도 기본 0건)을 기준으로 재구성했다.

지금 상태:

- 정본: `.agents/skills/svc-benchmark/references/*.md`
- Claude 쪽 `references`는 그 폴더를 가리키는 심볼릭이다. 내용 사본은 없다.

추가로 하지 않은 것: `.claude/skills/svc-benchmark/SKILL.md`는 `$SKILL` 한 줄이 달라야 해서 통째 심볼릭으로 바꾸지 않았다.

## 2. 많이 쓰는 스킬에서 본 것

조회 기준은 skills.sh 리더보드와 Firecrawl(2026-08-03)·The Tool Nerd(2026-05-14) 정리, 그리고 로컬에서 이미 쓰는 `last30days`다.

| 스킬 | 표시 설치 | 하는 일 | 벤치에 넣을 점 |
|---|---:|---|---|
| grill-me (mattpocock) | 865.8K | 계획의 가지를 하나씩 심문한다. 코드로 답할 수 있으면 묻지 않는다 | 일(JTBD)과 깊이 질문을 한 번에 던지지 말고, 권고안을 붙인 뒤 확인한다 |
| frontend-design (anthropics) | 780.8K | 금지 목록 + 방향 확정 후 실행 | 이미 금지 목록이 있다. 방향(지형 vs 가격)을 확인하기 전에는 지도를 그리지 않는 규칙을 더 세게 지킨다 |
| agent-browser (vercel-labs) | 680.3K | 브라우저를 도구로 열어 문서를 읽는다 | 사이트맵이 막히면 브라우저 지도가 1차다. 이미 SOP에 있다. 실패 시 대체 수집기만 선택으로 둔다 |
| caveman | 436.1K | 설명은 줄이고 사실은 남긴다 | 보고서 산문에는 쓰지 않는다. `notes/skill-notes.md`처럼 내부 로그만 짧게 |
| skill-creator (anthropics) | 352.6K | 스킬을 만들 때 평가 항목을 같이 만든다 | 새 절차마다 픽스처 테스트를 같이 넣는다. 이미 게이트가 있다 |
| brainstorming (obra/superpowers) | 326.5K | 설계 승인 전에는 구현 스킬을 부르지 않는다 | `--scan=landscape`에서 세그먼트 표를 보여 주기 전에는 함대를 보내지 않는다 |
| writing-great-skills / writing-skills | 317.5K / 165.7K | 짧은 SKILL + 두꺼운 참조 | 본문 320줄은 경계다. 절차 세부는 참조로만 남긴다 |
| research (mattpocock) | 307.5K | 백그라운드 에이전트가 1차 출처만 따라가 파일 하나에 쓴다 | 함대 노트는 이미 있다. “2차 글을 원문으로 쓰지 않는다”를 세그먼트 프롬프트에 고정한다 |
| last30days (로컬) | (리더보드 밖, 사내 사용) | 엔진이 스킬이다. 즉흥 검색은 실패로 본다. 실패 모드에 이름을 붙인다 | `--news=last30days`는 이미 훅이다. 브라우저·수집기 건강 점검과 이름 붙은 실패를 벤치에도 둔다 |
| seo-audit / copywriting (coreyhaines) | 186.9K / 177.8K | 공유 제품 맥락 파일을 먼저 읽는다 | 우리 제품과 견줄 때만 `notes/our-job.json`을 쓴다. 기획 xlsx는 만들지 않는다 |
| verification-before-completion (superpowers) | 178.2K | 통과를 말하기 전에 명령을 다시 돌린다 | Evidence Gate와 같다. 마무리에서 게이트 출력 요약을 `notes/skill-notes.md`에 남긴다 |
| competitor-teardown (skills-101) | 9.4K | 검색 도구로 지형을 돌린다 | 설치 수가 적고 Socket/Snyk 경고가 있다. 도구 의존 해체는 베끼지 않는다 |

빼 둔 것: find-skills(디렉터리 자체), Azure·Lark 묶음(설치 수는 크지만 벤치와 무관), frontend 미학 스킬, 영상 생성 스킬.

## 3. 지금 벤치가 이미 가진 것

외부 인기 스킬과 겹치는 부분은 다시 만들지 않는다.

- 일 먼저, SWOT 생략 금지, 지형 함대 (`jtbd-scan.md`)
- 결정적 스크립트 + 테스트 13개
- 원시 네트워크는 패키지 밖
- 대표 시도 기본 0건, 파괴 작업 승인으로도 금지
- `last30days`는 `--news` 훅만. 엔진 출력을 보고서에 복사하지 않음

부족한 쪽은 심문 밀도, 실패에 이름 붙이기, 긴 런의 인수인계, 본문 비대, 우리 제품 맥락이다.

## 4. 채택 원칙

1. 인기 스킬의 도구 묶음을 통째 넣지 않는다. 절차만 옮긴다.
2. 한 스킬이 다섯 가지를 하면 라우팅이 깨진다. 벤치는 해체 스킬로 남긴다.
3. 새 단계는 스크립트 또는 노트 칸이 있어야 한다. 문장만 추가하지 않는다.
4. 설치 수보다 실패 기록이 있는 규칙을 우선한다.

## 5. 단계

### 0 — 지금 닫힘

- Claude 참조 사본 제거, 심볼릭만 남김
- 지워진 정본 복구, 테스트 통과

### 1 — 확인과 실패 이름 (2026-08-16 코드 반영)

목적: 일을 대충 정하고 제품을 여는 일을 줄인다.

- TFG 질문 5를 grill 한 줄로 바꿨다. 한 번에 하나만 묻고, 권고안을 붙인다
- `--scan=landscape`는 세그먼트 표(`notes/segments.json`)를 보여 준 뒤에만 함대를 연다
- `notes/failures.json`에 이미 있는 실패를 이름으로 적는다. 예: `sitemap-behind-login`, `static-empty-widget`, `agent-self-report`
- 시작 시 브라우저·수집기 점검을 `preflight` 한 줄로 남긴다. 실패해도 런은 문서만으로 계속할 수 있다
- 공개 패키지는 `https://github.com/rp0927/svc-benchmark-skill`다. last30days에서 합친 것은 이름 붙은 실패·사전 점검 절차다

완료: `validate_scan.py --phase=jtbd|segments|close` 픽스처가 “세그먼트 없이 함대”와 “일 없이 지도”를 막는다.

### 2 — 본문 줄이기

목적: SKILL.md가 인접 작업마다 통째 로드되지 않게 한다.

- 13단계 세부는 참조로만 남긴다. 본문은 라우팅·금지·게이트 명령
- 함대 프롬프트는 `references/fleet-prompt.md` 한 곳

완료: 본문 줄 수가 눈에 띄게 줄고, 시맨틱 패리티 테스트는 그대로 통과한다.

### 3 — 긴 런 인수인계

목적: 지형 조사가 세션을 넘길 때 같은 일을 다시 열지 않는다.

- `notes/handoff.md` 칸: 일, 열린 URL, 남은 세그먼트, 미실행 mutation
- `--update`가 이 파일을 읽는다

완료: 핸드오프만으로 다음 세션이 1단계부터 다시 시작하지 않는다.

### 4 — 우리 제품과 견줄 때만

목적: “우리보다 잘 푸는가”를 추측으로 닫지 않는다.

- 사용자가 우리 제품을 말할 때만 `notes/our-job.json` (일, 가격 질문, 보지 말 것)
- 인사이트에 작업 지시·xlsx를 넣지 않는 규칙은 유지한다

완료: 우리 제품 칸이 없으면 가격 비교 문장을 쓰지 못한다.

### 하지 않는 것

- Firecrawl·belt·inference.sh를 기본 의존으로 넣지 않는다
- caveman을 보고서 문체에 쓰지 않는다
- 기획 15항을 기본 목차로 올리지 않는다. `planning-analysis`가 그 자리다
- 인기 스킬을 벤치 안에 설치하라고 강제하지 않는다. `--news=last30days`처럼 훅만 둔다

## 6. 다음 한 가지

1단계는 코드에 들어갔다. 프로세스 정본은 `references/process.md`, 이웃 스킬 점검은 `peer-audit.md`다. 공개 저장소는 `rp0927/svc-benchmark-skill`이다. 다음은 2단계(SKILL 본문 축소)다.
