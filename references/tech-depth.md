# 기술 심층 5칸

기본 보고서 H2는 늘리지 않는다. 아래 노트는 기존 절에 접는다.

| 칸 | 노트 | 보고서 |
|---|---|---|
| 패킷·HTTP 흐름 | `notes/packets.json` | 런타임 실측 |
| 공개 코드·번들·CLI | `notes/code-surface.json` | 문서 표면 + 기능 카드 |
| 구현 방법 | `notes/impl-methods.json` | 기능 카드 `tech_spec`/`impl_spec` + 인사이트 |
| 속도·서비스 특징 | `notes/perf.json` | 런타임 실측 + 결정 요약 |
| 페르소나 사용성 | `notes/persona-trials.json` | 대표 쿼리 (걷기는 질의 전송이 아니다) |

열지 못했으면 `missing_reason`을 남긴다. 빈 칸을 지우고 넘어가지 않는다.

`--scan=landscape`이고 깊은 세그먼트가 없으면 다섯 칸 모두 `missing_reason: landscape-shallow`로 닫을 수 있다. 깊은 제품이 있으면 그 제품 기준으로 채운다.

## 1. 패킷·HTTP 흐름

tcpdump·pcap은 하지 않는다. sanitizer를 거친 HTTP/HTTPS 흐름만 적는다. 원본 HAR를 패키지에 두지 않는다 (`packet-from-raw-har`).

`method`: `har-sanitized` | `curl-timing` | `none`

```json
{
  "as_of": "2026-08-16",
  "method": "har-sanitized",
  "missing_reason": "",
  "flows": [
    {
      "id": "home",
      "method": "GET",
      "host": "example.test",
      "path": "/",
      "status": 200,
      "ttfb_ms": 180,
      "total_ms": 420,
      "content_type": "text/html",
      "auth_gate": false,
      "note": "문서 셸"
    }
  ]
}
```

호스트·메서드·경로·상태·TTFB·전체 왕복·인증 게이트를 칸으로 나눈다. 쿠키·Authorization 값을 적지 않는다.

## 2. 공개 코드

비공개 저장소·난독화된 번들을 원천으로 쓰지 않는다 (`private-code-as-source`). 공개 GitHub, 공식 문서의 예제, 이미 설치된 CLI, 페이지가 내려 주는 공개 JS 파일명만 본다.

`observed`: `docs-only` | `browser` | `cli` | `none`

```json
{
  "as_of": "2026-08-16",
  "missing_reason": "",
  "public_repo": "https://github.com/example/app",
  "entrypoints": ["app/page.tsx"],
  "client_bundles": ["/assets/app.js"],
  "cli_bins": ["example"],
  "observed": "docs-only",
  "notes": "공식 저장소 README에 엔트리만 있다"
}
```

디컴파일·소스맵 강제 수집·인증 우회는 하지 않는다.

## 3. 구현 방법

관측으로 말할 수 있는 층만 적는다. 추측은 `missing_reason` 또는 힌트 층.

칸: `hosting`, `auth`, `data_path`, `model_routing`, `billing_unit`, `evidence`.

예: 호스팅은 Vercel 헤더, 인증은 302 로그인, 일의 단위는 원격 VM, 과금은 분 단위. 모델 ID가 없으면 `model_routing`에 “다이얼만 / 미확인”.

## 4. 속도·특징

`notes/runtime.md`·`summary.json`에서 숫자를 옮긴다. 홈 TTFB, 홈 전체, API 중앙값, 스트림 첫 바이트와 종료를 같은 숫자로 두지 않는다.

`characteristics`는 관측 문장만. 예: “첫 바이트는 빠르고 스트림이 길다”, “가격 페이지가 로그인 뒤에 있다”.

## 5. 페르소나 사용성

채팅·가입·결제를 보내지 않는다 (`persona-trial-as-mutation`). `jtbd.actors` 또는 일에서 페르소나 2명을 고른다. 공개 IA를 그 일의 순서로 걷고 마찰을 적는다.

`mode`: `walkthrough-public` | `approved-readonly` | `none`

```json
{
  "as_of": "2026-08-16",
  "mode": "walkthrough-public",
  "missing_reason": "",
  "trials": [
    {
      "persona": "노트북이 꺼져도 일을 맡기려는 개발자",
      "job": "원격 머신에 일을 붙인다",
      "path": ["홈", "문서/orbs", "가격"],
      "friction": "가격이 로그인 뒤에 있다",
      "outcome": "일부",
      "mutation": false
    }
  ]
}
```

`outcome`: `열림` | `일부` | `막힘` | `문서만`. `mutation`은 항상 `false`. 승인된 읽기 전용 질의는 9단계 `notes/queries.md`로 넘긴다. 위젯의 페르소나 재구성(시스템 프롬프트가 아님)은 [product-modules.md](product-modules.md)이고, 이 칸과 섞지 않는다.

## 게이트

```bash
python3 "$SKILL/scripts/validate_tech.py" --root .
```
