# 일·지형·SWOT

기능 목록보다 고객이 고용하는 일(JTBD)이 출발점이다. 칸은 여기만 적는다.

출처: Tamara Ceman(일·깊이·SWOT·손 검색), Dmitry Trofimets(개관→세그먼트→심층→종합→분석, 함대).

우리 서비스 기획서의 SWOT·xlsx는 `svc-planning`이다. 여기 SWOT는 관측한 제품 또는 일이다.

## 일

`notes/jtbd.json`을 쓰기 전에는 지도를 그리지 않는다.

```json
{
  "job": "고객이 해내려는 일 한 문장",
  "pain": "실제 고통",
  "hired_solutions": ["이미 쓰는 해법"],
  "customer_evidence": "customer",
  "hypotheses": [{"id": "h1", "claim": "이 일을 이 해법으로 끝낸다", "status": "open"}],
  "question": "need-vs-price",
  "depth": "deep",
  "actors": [
    {"name": "Amp", "url": "https://ampcode.com", "role": "competitor", "job_fit": "같은 일"}
  ]
}
```

`customer_evidence`: `customer` | `proxy-shallow` | `none`

고객이 없으면 얕은 조사로 가설 묶음만 만든다. `none`/`proxy-shallow`면 `hypotheses`가 1건 이상이어야 한다. 그 가설로 대상을 가른다.

`role`: `competitor` 같은 일·같은 해법 / `alternative` 이 쓰임새의 강한 다른 해법 / `out` 이름만 비슷한 곳.

기능 카드의 `job_to_be_done`은 기능 한 장의 일이다. 런의 일은 이 파일이다.

## 깊이

`question`이 깊이를 정한다. `--depth`(public/logged-in)와 섞지 않는다.

| question | 찾는 것 | 조사 |
|---|---|---|
| `landscape` | 경쟁 지형만 | 넓고 얕다. `--scan=landscape` |
| `need-vs-price` | 이 필요가 당신보다 잘 풀리는지, 가격이 되는지의 여부 | 그 세그먼트·제품만 깊게. 기본 `--scan=product` |

얕은 지형에서 가격을 단정하지 않는다. 깊게 보지 않은 제품에 “못한다”를 쓰지 않는다.

## 지형 순서

`--scan=landscape`이거나 대상이 URL이 아닌 일·시장일 때. 순서를 건너뛰지 않는다.

1. 시장 전체 개관 — 손 검색. 가설을 늘리거나 버린다
2. 솔루션 세그먼트 — `notes/segments.json`. 세그먼트는 일·해법으로 나눈다. 브랜드 목록이 아니다
3. 각 세그먼트를 깊게 — `question=need-vs-price`인 세그먼트만 SKILL 1–10. 나머지는 얕은 관측
4. 종합 — 세그먼트 사이 겹침·빈칸
5. 분석 — 가격을 정당화하는 해법이 어디인지. 작업 지시가 아니다

```json
{
  "segments": [
    {
      "id": "remote-agent",
      "name": "원격 머신 에이전트",
      "job": "노트북이 꺼져도 일이 이어지게 한다",
      "products": ["Amp"],
      "depth": "deep"
    }
  ]
}
```

세그먼트 노트는 `notes/segments/<id>.md`.

## 단계 게이트

스크립트는 `--phase`로 더 일찍 막는다. 기본은 `close`.

| phase | 언제 | 막는 것 |
|---|---|---|
| `jtbd` | 지도를 열기 전 | `job`이 비어 있음. `notes/sitemap.md`가 있는데 `job`이 없으면 `map-before-job` |
| `segments` | 함대를 열기 전 | landscape인데 세그먼트 표가 비어 있음. 세그먼트 노트가 있는데 표가 없으면 `fleet-before-segments` |
| `close` | 보고서 마무리 | 위 + SWOT 네 칸 + 보고서 라벨 |

SWOT는 `close`에서만 필수다. 일을 정하는 단계에서는 네 칸을 채우지 않아도 된다.

## 함대

지형·AI 주제는 에이전트를 하나만 보내지 않는다. 세그먼트마다 한 명. 동시 3개. 범위는 MECE. `notes/segments.json`을 보여 주기 전에는 보내지 않는다.

```bash
python3 "$SKILL/scripts/validate_scan.py" --root . --phase=segments
```

프롬프트에 복사한다: 담당 `segments[].id`, 출력 `notes/segments/<id>.md`, 일(`job`) 한 문장, `depth`, 미승인 mutation 0건, 열지 않은 사이트에 “못한다” 금지, 자기보고를 완료로 쓰지 말 것. 2차 글을 원문으로 쓰지 않는다.

메인이 각 노트를 읽고 핵심 URL을 다시 연다. 함대 출력을 원문으로 취급하지 않는다.

제품 한 건(`--scan=product`)은 함대 없이 1–10을 쓴다. 페이지 순회 동시 3개는 그대로다.

## 이름 붙은 실패

즉흥 검색으로 스킬 단계를 건너뛰지 않는다. 난 일은 `notes/failures.json` `events`에 이름으로 적는다.

| id | 뜻 |
|---|---|
| `sitemap-behind-login` | 사이트맵이 로그인 뒤에 있다. 막힌 사실을 남기고 네비로 다시 그린다 |
| `static-empty-widget` | 정적 원문이 비어도 위젯 페이지가 빈 것이 아니다 |
| `agent-self-report` | 서브에이전트 자기보고를 원문 확인으로 쓴다 |
| `raw-network-in-package` | 원시 HAR·hook을 `evidence/network/`에 넣는다 |
| `price-from-shallow-scan` | 얕은 지형에서 가격·가능/불가능을 단정한다 |
| `map-before-job` | `job` 없이 지도를 연다 |
| `fleet-before-segments` | 세그먼트 표 없이 함대를 연다 |
| `improvise-without-skill` | 스킬 단계를 건너뛰고 검색만으로 보고서를 쓴다 |
| `persona-trial-as-mutation` | 페르소나 걷기를 채팅·가입·결제로 바꾼다 |
| `private-code-as-source` | 비공개 저장소·디컴파일을 원천으로 쓴다 |
| `packet-from-raw-har` | 원시 HAR를 패키지에 넣거나 pcap을 요구한다 |
| `official-from-snippet` | 검색 스니펫을 공식 원문으로 쓴다 |
| `last30days-as-official` | 커뮤니티 엔진 출력을 공식 changelog로 쓴다 |

시작 직후 `preflight`에 브라우저·수집기 한 줄을 적는다. 브라우저가 없어도 문서만으로 런을 이어간다.

## SWOT

건너뛰지 않는다. 이 쓰임새의 통찰을 묶는 칸이다.

`notes/swot.json`:

```json
{
  "subject": "Amp",
  "job": "노트북이 꺼져도 에이전트가 일하게 한다",
  "strength": "일의 단위가 원격 머신이다",
  "weakness": "로그인 뒤 표면은 열지 못했다",
  "opportunity": "CLI와 웹이 같은 스레드를 쓴다",
  "threat": "같은 일을 구독 한 장으로 파는 대안"
}
```

`--scan=product`면 그 제품 × 일. `--scan=landscape`면 일 × 지형. 네 칸을 비우지 않는다. 계획·바람을 강점에 넣지 않는다.

`benchmark` 보고서는 H2를 늘리지 않고 인사이트에 표를 옮긴다. `landscape`는 H2 `SWOT`.

## 손 검색

가장 정확한 데이터는 연 페이지에서 온다. 검색 스니펫·에이전트 요약을 원문으로 쓰지 않는다. AI 초안은 가설이다. 사람 또는 메인의 손 확인 없이 가격·가능/불가능을 닫지 않는다.
