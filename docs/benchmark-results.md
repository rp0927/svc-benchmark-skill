# 스킬 벤치마킹 결과

- 조회일: 2026-08-16
- 대상: `svc-benchmark`에 무엇을 넣을지
- 출처: [skills.sh](https://www.skills.sh/) 표시 설치, Firecrawl(2026-08-03), The Tool Nerd(2026-05-14), 로컬 운영 스킬·Amp/PRizmo/Grok Bot 산출물

표시 설치는 `npx skills add` 집계다. 고유 사용자 수가 아니다. 순위가 아니라 **배울 절차**만 골랐다.

## 한 줄

인기 스킬의 도구를 통째 넣지 않는다. 질문은 한 줄씩, 세그먼트 표 전에 함대를 열지 않고, 실패에 이름을 붙인다. 그 세 가지는 이미 코드에 있다.

## 1. 외부 인기 스킬

| 스킬 | 표시 설치 | 하는 일 | 채택 | 지금 상태 |
|---|---:|---|---|---|
| grill-me | 866K | 가지를 하나씩 심문, 코드로 알면 안 묻는다 | 질문 한 줄 + 권고 | TFG 5에 반영 |
| frontend-design | 781K | 금지 목록, 방향 후 실행 | 지형 vs 가격 전에 지도 금지 | `--phase=jtbd` |
| agent-browser | 680K | 브라우저로 문서를 연다 | 사이트맵 막히면 브라우저 1차 | SOP에 있음. 기본 의존 추가 없음 |
| caveman | 436K | 설명 줄이고 사실만 | 내부 로그만 짧게 | 보고서 문체에 안 씀 |
| skill-creator | 353K | 평가 항목을 같이 만든다 | 새 절차마다 픽스처 | 게이트 13개 |
| brainstorming (superpowers) | 327K | 설계 승인 전 구현 금지 | 세그먼트 표 전 함대 금지 | `--phase=segments` |
| writing-skills | 318K / 166K | 짧은 SKILL, 두꺼운 참조 | 본문 축소 | **다음(2단계)** |
| research (mattpocock) | 308K | 1차 출처만 파일에 쓴다 | 2차 글을 원문으로 안 씀 | 함대 프롬프트에 고정 |
| last30days | 리더보드 밖 | 엔진=스킬, 실패에 이름 | 실패 id, 사전 점검 | `failures.json` |
| seo-audit / copywriting | 187K / 178K | 제품 맥락 파일을 먼저 읽는다 | 우리 제품 칸 | **나중(4단계)** `our-job.json` |
| verification-before-completion | 178K | 통과 전에 명령을 다시 돈다 | Evidence Gate | 이미 있음 |
| competitor-teardown | 9.4K | 검색으로 지형 | 없음 | 보안 경고. 베끼지 않음 |

빼 둔 것: find-skills(3.0M, 디렉터리), Azure·Lark, 미학·영상 스킬.

## 2. 사내·이미 쓰는 스킬

| 스킬 | 잘 되는 점 | 벤치에 남긴 것 | 넣지 않은 것 |
|---|---|---|---|
| svc-planning | 로컬 선행, 검증 후 생성, ✅⚠️❌🔄 | `precheck.json`, 결정 요약 등급 | 15항 xlsx를 기본 목차로 |
| korea-financial-benchmark | 출처 층, 빈칸 사유 | 1차/2차/힌트, `missing_reason` | 재무 수집기 |
| doc-autoaudit | 자기보고 불신 | close 감사 파일 | 본문을 감사 스킬로 대체 |
| last30days | 이름 붙은 실패 | `failures.json`, 즉흥 검색 금지 | 1400줄 엔진 |
| korean-prose-editor | 공개 저장소+CI | 이 패키지 형태 | 윤문 파이프라인 내장 |
| competitor-watch | 얇은 뉴스 모드 | 해체는 여기로 | teardown 템플릿 부활 |
| Amp / PRizmo / Grok Bot | mutation 0, 실측 | 실패 이름, 기본 H2 고정 | “가져올 것” 절 |

## 3. 다음에 벤치 런이 달라지는 점

이미 적용됨:

- 시작 때 지형 vs 필요·가격을 한 줄로 묻고 권고를 붙인다
- `job` 없이 사이트맵을 열면 실패 (`map-before-job`)
- 세그먼트 표 없이 함대를 열면 실패 (`fleet-before-segments`)
- SWOT는 마지막에 필수. 인사이트는 관찰만
- `--news=last30days`는 인용 표 훅. 엔진 출력 복사 없음

아직 코드 없음:

- SKILL 본문 축소 (2단계)
- `notes/handoff.md` (3단계)
- `notes/our-job.json` (4단계, 우리 제품과 견줄 때만)

## 4. 넣지 않기로 한 것

Firecrawl·belt를 기본 의존으로 두지 않는다. caveman을 보고서 문체에 쓰지 않는다. 기획 15항을 기본 목차에 올리지 않는다. 인기 스킬을 벤치 안에 설치하라고 강제하지 않는다.
