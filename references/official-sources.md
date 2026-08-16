# 공식 소스 1패스

지금 미는 것·외부 소식·문서 표면을 **한 번**에 채운다. changelog를 세 번 열지 않는다.

산출 SSOT는 `notes/official-sources.json`이다. 보고서 H2는 그대로다.

| 종류 | 예 | 보고서 |
|---|---|---|
| `changelog` | /changelog, /releases, What’s new | 지금 미는 것, 최신 기능 검증 |
| `blog` | 공식 블로그, 엔지니어링 | 외부 소식 |
| `docs` | docs, manual, developers | 문서 표면 |
| `press` | newsroom, 보도자료 | 외부 소식 |
| `support` | help, FAQ, 기술 지원 | 문서 표면 |
| `rss` / `status` | 피드, 상태 페이지 | 외부 소식 (선택) |

커뮤니티·매체 반응은 `community[]`다. 공식 칸에 넣지 않는다 (`last30days-as-official`). `--news=last30days`여도 엔진 출력을 본문에 복사하지 않는다. 인용 표만.

검색 스니펫을 원문으로 쓰지 않는다 (`official-from-snippet`).

## 순서 (효율)

1. 이미 연 `notes/sitemap.md`와 `evidence/docs/home.html`에서 후보를 뽑는다. 새 검색보다 먼저다.
2. 없는 종류만 공식 호스트에서 한 질의씩 찾는다. `site:{host} changelog`, `blog`, `docs`, `press OR newsroom`, `support OR help`.
3. 종류마다 **첫 페이지 1건**을 연 뒤 나머지를 연다. 공식 항목은 최대 12건, 커뮤니티는 최대 8건.
4. 같은 URL은 다시 열지 않는다.
5. 90일 창. 그보다 오래된 공식 글은 `timeline.json`에만 날짜를 남긴다.
6. `docs`가 제품 자체일 때만 `notes/docs.md`를 추가로 분해한다. 목록만이면 JSON으로 충분하다.

```bash
python3 "$SKILL/scripts/collect_official.py" \
  --sitemap notes/sitemap.md \
  --html evidence/docs/home.html \
  --out notes/official-sources.json
python3 "$SKILL/scripts/validate_official.py" --root .
```

`collect_official.py`는 네트워크를 쓰지 않는다. 이미 받은 지도·홈 HTML만 분류한다.

## 스키마

```json
{
  "as_of": "2026-08-16",
  "window_days": 90,
  "missing_reason": "",
  "feeds": [
    {"kind": "changelog", "url": "https://ex.test/changelog", "found": true, "missing_reason": ""}
  ],
  "items": [
    {
      "id": "ch-2026-08-01",
      "kind": "changelog",
      "title": "Orb sizes",
      "url": "https://ex.test/changelog#orbs",
      "date": "2026-08-01",
      "layer": "primary",
      "used_in": ["지금 미는 것"],
      "note": "공식 릴리스"
    }
  ],
  "community": []
}
```

필수 종류 다섯(`changelog` `blog` `docs` `press` `support`)은 `feeds`에 있어야 한다. 없으면 `found: false`와 `missing_reason`.

`layer`: `primary` 연 공식 페이지 / `secondary` 공식 RSS 요약 / `hint` 검색만.

`--scan=landscape`이고 깊은 세그먼트가 없으면 `missing_reason: landscape-shallow`로 닫는다.

## 보고서에 접기

- **지금 미는 것**: 90일 안 `changelog`·`blog` 한 문장 + 날짜 표
- **외부 소식**: `press` + `community` 인용 표. 연대기 산문 금지. 역사는 `notes/timeline.json`
- **문서 표면**: `docs`·`support` 목록. 뉴스와 한 페이지에 섞지 않는다
