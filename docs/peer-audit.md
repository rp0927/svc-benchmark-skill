# 유사 스킬 현황과 프로세스 재점검

- 날짜: 2026-08-16
- 목적: 잘 되는 이웃 스킬을 기준으로 `svc-benchmark` 프로세스·필수 항목을 다시 잠근다
- 정본 프로세스: `.agents/skills/svc-benchmark/references/process.md`

설치 수나 기억으로 판단하지 않았다. 로컬 SKILL·게이트·실제 벤치 산출물을 읽었다.

## 1. 이웃 스킬 현황

| 스킬 | 상태 | 잘 되는 점 | 벤치에 가져올 점 | 가져오지 않을 점 |
|---|---|---|---|---|
| `svc-planning` | 운영. 스크립트+스모크 | 로컬 선행 점검, 검증 후 생성, ✅⚠️❌🔄, 검증 로그 파일 | Phase 0 로컬 훑기. 생성 전 클레임 등급 | 15항 xlsx를 기본 벤치 목차로 |
| `korea-financial-benchmark` | 운영. 문서형 | 출처 층, 빈칸 사유, 대상 AI 수치 금지 | 수치 1차/2차/힌트. `missing_reason` | 재무 수집 도구 묶음 |
| `doc-autoaudit` | 운영. 게이트 테스트 | 자기보고 불신, fail-closed, 불일치 0 | close에서 매니페스트+감사 파일 | 벤치 본문을 감사 스킬로 대체 |
| `last30days` | 사내+GitHub 포크 | 이름 붙은 실패, doctor, 엔진=스킬 | 실패 id, 사전 점검 한 줄, 즉흥 검색 금지 | 1400줄 SKILL, 소셜 엔진 |
| `korean-prose-editor` | GitHub 공개, CI | 단일 진입점, PROCESS, 버전, 보존 게이트 | 공개 저장소+CI 형태 | 윤문 파이프라인을 벤치에 내장 |
| `competitor-watch` | 운영. 본문 55줄 | 뉴스 7–30일은 얇아서 유지됨 | 경계만. 해체는 벤치 | teardown 템플릿을 되살리지 않음 |
| `deep-research` | 운영. 장문 시장 | 계획 후 루프, 출처 레지스트리 | 지형 개관에서 손 검색 | 제품 해체를 장문 리서치로 |
| Amp / PRizmo / Grok Bot 런 | 산출물 있음 | mutation 0, 실측 경로, 인쇄 CSS | 이름 붙은 실패, 기본 H2 고정 | Amp 초안의 “가져올 것” 절 |

외부 `competitor-teardown`(skills-101)은 설치 수가 적고 보안 경고가 있다. 도구 의존 해체는 쓰지 않는다.

## 2. 실제 벤치가 알려 준 것

- **Amp**: 사이트맵이 로그인 뒤에 있다. 막힌 사실을 남기고 네비로 다시 그렸다. 초안 보고서는 “가져올 것”을 넣었고, 그 절은 이후 계약에서 뺐다.
- **PRizmo**: 정적 원문이 비어도 위젯이 빈 것이 아니다. 모델명은 클라이언트에 없으면 미확인이다.
- **Grok Bot**: 기본 해체가 아니라 `planning-analysis` 목차(23 H2)를 썼다. 라이브 `validate_report` 시험이 그 제목에 묶여 있다. 기본 `benchmark` H2를 바꾸면 그 시험과 새 제품 런이 같이 흔들린다.

## 3. 프로세스에서 부족한 것 / 이미 있는 것

이미 있는 것: 일 먼저, SWOT, 지형 함대, `--phase=jtbd|segments|close`, 실패 이름, 원시 네트워크 패키지 밖, 카드 `missing_reason`, 결정 요약 등급.

부족해서 이번에 프로세스에 올린 것:

1. 로컬 선행물 훑기 (`notes/precheck.json`)
2. 수치 출처 층 (1차 / 2차 / 힌트)
3. 이웃 스킬 경계 표
4. “가져올 것” 절을 다시 넣지 않는다는 명시
5. GitHub에 올릴 수 있는 패키지 형태 (버전, PROCESS, CI)

아직 칸만 있고 코드가 아닌 것: `notes/handoff.md`, `notes/our-job.json`, SKILL 본문 축소.

## 4. 잠근 결정

- 기본 산출은 관측 보고서다. 기획서·재무표가 아니다.
- 기본 목차는 `benchmark` 17 H2. `landscape`와 `planning-analysis`는 프로필이다.
- 새 항목은 노트 JSON 또는 게이트가 있을 때만 필수다.
- `competitor-watch` 해체 모드는 호환용으로 남기고, 새 런은 `/svc-benchmark`로 보낸다.
