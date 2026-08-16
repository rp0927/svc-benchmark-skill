# 기능 카드 칸

기능마다 JSON 한 장. 칸 이름은 고정이다. 없는 값은 `null`이고, 이유를 `missing_reason`에 적는다. 삭제한 기능도 카드로 남긴다.

```json
{
  "id": "orbs",
  "name": "Orbs",
  "status": "live",
  "one_liner": "스레드마다 주어지는 원격 머신",
  "job_to_be_done": "노트북이 꺼져도 에이전트가 계속 일하게 한다",
  "ui_surfaces": ["웹 새 스레드", "CLI amp -ox"],
  "tech_spec": ["Debian 12", "분 단위 과금"],
  "impl_spec": ["스레드 ID와 VM 1:1", "5분 유휴 정지"],
  "difficulty": "XL",
  "benchmark_against": "Orca worktree / Codespaces",
  "insight": "일의 단위가 채팅이 아니라 원격 머신이다",
  "recent_push": "2026-08-07 a1 사이즈",
  "first_seen": "2026-06-30",
  "last_changed": "2026-08-07",
  "login_required": true,
  "deleted": false,
  "screenshot": "evidence/screenshots/15-orb-sizes.png",
  "missing_reason": null,
  "evidence": [
    {
      "url": "https://ampcode.com/manual/orbs",
      "observed": "docs+cli",
      "path": "evidence/cli/orb-sizes.txt",
      "note": "사이즈 enum이 CLI와 같음"
    }
  ]
}
```

`status`: `live` | `beta` | `deprecated` | `deleted`

`difficulty`: `S` 수주, `M` 1–2개월, `L` 한 분기, `XL` 분기 이상.

`observed`: `browser` | `cli` | `docs` | `docs+cli` | `docs-only` | `official-image` | `network`

## 증거 게이트

- 카드 파일의 `notes` 디렉터리를 기준으로 패키지 루트를 찾는다.
- `screenshot`이 있으면 패키지 안의 실파일이어야 한다.
- 모든 `evidence` 항목은 빈 값이 아닌 `url`과 `note`를 가진다.
- `browser`는 카드 `screenshot`이 실파일이면 별도 경로 없이 통과한다.
- 스크린샷 없는 `browser`의 `path`는 패키지 안 `evidence/docs`의 `.txt` 또는 `.json` 접근성 트리여야 한다. 같은 경로가 `notes/privacy-exceptions.json`의 `redactions`에 `kind: accessibility-tree`로 등록되어야 하며, 빈 값이 아닌 `markers`가 모두 실파일에 있어야 한다.
- `report/report.md`를 비롯한 다른 패키지 파일은 스크린샷 없는 `browser` 증거를 대신하지 못한다. 접근성 트리가 없으면 관측값을 `docs-only`로 적는다.
- `official-image`는 카드 `screenshot` 또는 해당 항목의 `path`가 실파일이어야 한다.
- `cli`, `docs+cli`, `network`는 해당 항목의 `path`가 실파일이어야 한다.
- 패키지 밖 절대 경로와 상위 디렉터리 이동은 실패한다.

`id`는 런이 바뀌어도 유지한다. `--update`의 비교 키다. 브랜드 명사는 `id`와 `name`에 원문 그대로 둔다. 한국어는 `one_liner`, `job_to_be_done`, `insight`에만 쓴다. 런 전체의 일은 [jtbd-scan.md](jtbd-scan.md)의 `notes/jtbd.json`이다. 이 칸은 기능 한 장의 일만 적는다.

`insight`는 가져올 작업 지시가 아니다. 그 기능이 제품에서 하는 역할 한 줄이다.
