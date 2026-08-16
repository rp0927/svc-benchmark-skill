# svc-benchmark

남의 서비스를 열어 사이트맵·기능 카드·네트워크 실측까지 분해하는 에이전트 스킬.

[![CI](https://github.com/rp0927/svc-benchmark-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/rp0927/svc-benchmark-skill/actions/workflows/ci.yml)
v0.3.0 · [MIT License](LICENSE) · Python 3.9 이상

기능 목록이 아니라 고객이 고용하는 일(JTBD)에서 시작한다. 진짜 경쟁과 쓰임새의 강한 대안을 가른 뒤, 관측한 제품 또는 일을 SWOT로 묶는다. 인사이트는 관찰이다. 작업 지시나 기획 xlsx가 아니다.

## 이런 작업에 적합하다

| 사용 사례 | 하는 일 |
|---|---|
| 제품 한 건 해체 | 공개 표면, 카드, 런타임, 최신 클레임 검증 |
| 일 기준 경쟁 지형 | 개관 → 세그먼트 → 깊은 곳만 해체 → 종합 → 분석 |
| 기획 전 관측 | `/svc-planning`에 넣기 전에 실제 화면을 연다 |

## 제공하지 않는 것

- 우리 서비스 기획서 (그건 `svc-planning`)
- 공시·재무 수치 수집 (그건 `korea-financial-benchmark`)
- 7–30일 뉴스 모니터링 (그건 `competitor-watch`)
- 대상 서비스에 메시지를 보내거나 결제·삭제·계정 변경을 하는 일

## 네트워크와 자격 증명

이 스킬은 대상 서비스의 **공개 페이지**를 읽고, 사용자가 승인한 공개 GET만 호출한다. 기본 mutation은 0건이다. API 키를 요구하지 않는다. 로그인 뒤 표면은 사용자가 이미 연 세션이 있을 때만 본다. 원시 HAR·hook 로그는 산출 패키지 밖에 두고, 저장본은 sanitizer를 거친다.

선택 훅 `--news=last30days`는 별도 스킬이다. 그 엔진 출력을 이 보고서에 복사하지 않는다.

## 설치

에이전트 스킬 디렉터리에 이 저장소를 두거나, 워크스페이스 `.agents/skills/svc-benchmark`로 복사한다.

```bash
git clone https://github.com/rp0927/svc-benchmark-skill.git
```

42workspace 런타임 정본은 모노레포의 `.agents/skills/svc-benchmark/`다. 이 저장소는 같은 스킬의 공개 패키지다. 개선분은 여기 올린 뒤 워크스페이스로 맞춘다.

## 테스트

```bash
bash scripts/run_tests.sh
```

순수 Python 표준 라이브러리. 네트워크 없음. 워크스페이스 dual-tree 시험(`test_skill_step12_gates.py`)은 이 저장소 CI에서 건너뛴다.

## 문서

- [SKILL.md](SKILL.md) — 라우팅·금지·게이트 명령
- [references/process.md](references/process.md) — 실행 프로세스와 필수 산출
- [references/tech-depth.md](references/tech-depth.md) — 패킷·코드·구현·속도·페르소나
- [references/jtbd-scan.md](references/jtbd-scan.md) — 일·지형·실패 이름
- [docs/benchmark-results.md](docs/benchmark-results.md) — 인기 스킬·사내 스킬 벤치 결과
- [docs/peer-audit.md](docs/peer-audit.md) — 이웃 스킬 현황 점검
- [docs/upgrade-plan.md](docs/upgrade-plan.md) — 고도화 단계 0–4
