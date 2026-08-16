# 출처 감사

금액·요금 주장은 매체 이름을 코드에 고정하지 않는다. 보고서 D형 항목의 **정확 이름**과 `notes/sources.json`의 `named`/`labels`에서 `label` 또는 `name`, 그리고 적어 둔 `aliases`만 쓴다. label의 첫 단어를 별칭으로 만들지 않는다.

본문에서 출처 이름을 찾을 때는 ASCII 영숫자 토큰 경계를 쓴다. `News`는 `BadNews`의 일부가 아니다.

한 통화 문단에 등록 출처가 여러 개 있으면, **각 출처**가 자기 허용 host 또는 직접 URL을 그 문단에 가져야 한다. AlphaNews 주장에 BetaNews URL만 있으면 실패다.

금액 인식은 `$987이라고`, `5달러`, `0.01달러`, `0.99달러`, `1,234달러`처럼 숫자 뒤 non-digit lookaround를 쓴다. Unicode 단어 경계는 쓰지 않는다. 정확한 `$0`·`$0.00`·`0달러`·`0.00달러`만 제외하고 양수 소수는 포함한다. `600억 달러`와 `1,23달러` 같은 잘못된 쉼표는 제외한다. 영문 outlet은 `Wired는`처럼 조사 앞에서도 ASCII 영숫자 경계로 찾는다.

출처 host는 `urlparse().hostname`으로 비교한다. `www.`는 떼지 않는다. 같은 host의 기본 port(`:443`, `:80`)는 허용하고, userinfo가 있는 URL은 원장과 D형이 같더라도 근거로 쓰지 않는다. 하위 도메인·다른 host는 거부한다.

`validate_audit.py`의 HTTP 근거는 `notes/sources.json` 원장 URL과 `report/report.md` D형 URL **양쪽**에 있어야 한다. 합집합으로 통과시키지 않는다. D형에만 있으면 dform-only, 원장에만 있으면 ledger-only로 구분한다. 로컬 파일 근거는 기존과 같다.

`validate_sources.py`가 금액·이름 규칙을 검사한다. D형 인용과 원장 URL의 완전 비교는 그대로다.
