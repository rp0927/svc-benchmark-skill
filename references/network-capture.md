# 네트워크 수집

파서(`measure_network.py`)는 ingest가 만든 `session.json`만 읽는다. 브라우저 원본 HAR·hook·네트워크 로그는 패키지 밖 임시 `$RAW_INPUT`에만 둔다. 쿠키·Authorization 값은 저장하지 않는다.

산출:

```text
$RAW_INPUT                         # 패키지 밖 원본 (HAR 또는 단순 JSON)
evidence/network/session.json      # ingest sanitizer 결과 (파서 입력)
evidence/network/summary.json      # 집계
notes/runtime.md                   # 사람용
```

## 1. Chrome DevTools

첫 시도가 끝난 뒤:

1. `list_network_requests` — 필요하면 `resourceTypes: ["xhr","fetch","document"]`
2. XHR/fetch 몇 건은 `get_network_request`로 상태·시간을 보강. 응답 본문 전문은 넣지 않는다
3. 도구 출력을 패키지 밖 `$RAW_INPUT`에 저장
4. ingest → measure

위젯 hook 로그가 있으면 그것도 `$RAW_INPUT`에 두고 ingest한다.

## 2. Orca

```text
orca capture start --json
# 첫 페이지 + 승인된 읽기 전용만
orca network --limit 200 --json > "$RAW_INPUT"
```

`capture start` 없이 `network`를 치면 비어 있을 수 있다. 탭이 없으면 `orca tab create`가 먼저다.

## 3. 공개 GET만 (브라우저 없음)

```bash
python3 "$SKILL/scripts/curl_timing.py" \
  --url "$URL" --out "$RAW_INPUT"
```

헤더만 받고 본문은 버린다. 위젯 POST/스트림은 이 경로로 대체하지 않는다.

## 4. 정규화 + 파서

```bash
RAW_TMP_DIR="${RAW_TMP_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/svc-benchmark-network.XXXXXX")}"
RAW_INPUT="${RAW_INPUT:-$RAW_TMP_DIR/raw.json}"
test -f "$RAW_INPUT"
python3 "$SKILL/scripts/ingest_network.py" \
  "$RAW_INPUT" --out evidence/network/session.json
python3 "$SKILL/scripts/measure_network.py" \
  --har evidence/network/session.json \
  --out notes/runtime.md \
  --json evidence/network/summary.json
```

원본 HAR를 직접 통과시키지 않는다. ingest sanitizer를 거친 `session.json`만 패키지에 둔다.

단순 JSON 한 줄:

```json
{"method":"GET","url":"https://ex.test/status","status":200,"ttfb_ms":120,"total_ms":180}
```

`ttfb_ms`는 첫 바이트, `total_ms`는 스트림 종료. 둘을 같은 숫자로 두지 않는다.
