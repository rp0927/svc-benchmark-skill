# 브라우저 SOP

정적 원문 열람만 보고 페이지가 비었다고 하지 않는다. 위젯·SPA는 브라우저가 1차다. 브라우저 렌더와 원문을 교차 확인한다.

1. 폴더를 만든 뒤 브라우저를 연다. Chrome DevTools가 있으면 그걸 쓴다. 없으면 Orca 내장 브라우저.
2. 첫 URL만 연다. 렌더·경로·위젯 여부를 확인한다. 나머지를 아직 돌지 않는다.
3. 스크린샷을 `evidence/screenshots/01-first.png`에 남긴다. 가능하면 접근성 스냅샷도 남긴다.
4. 읽기 전용 시도는 기본 0건. 사용자의 명시 승인과 `mutations_allowed`에 정확한 액션이 있을 때만 1건 실행한다. 미승인이면 docs-only 또는 기존 화면 관측으로 남긴다. 메시지 전송·결제·로그아웃·삭제·Reset·파괴적 작업·새 worktree는 승인으로도 하지 않는다.
5. 위젯이면 탐색 **전에** fetch hook을 건다. 훅 없이 보낸 호출은 패킷이 빠질 수 있다.
6. 네트워크는 패키지 밖 `$RAW_INPUT`에 두고 `ingest_network.py`로 `evidence/network/session.json`만 남긴다. 방법은 [network-capture.md](network-capture.md).
7. 그다음 나머지 공개 페이지를 돈다. 페이지마다 스크린샷.
8. mute/보내기처럼 보이는 컨트롤은 접근성 이름만 보고 누르지 않는다. `#send` 같은 안정 셀렉터를 먼저 찾는다.

## Chrome

`new_page` 또는 `navigate_page`(url). 위젯이면 `navigate_page`의 `initScript`에 아래 훅을 넣는다.

스크린샷: `take_screenshot` `filePath=evidence/screenshots/01-first.jpeg` `format=jpeg`.

스냅샷: `take_snapshot`.

## Orca

```text
orca capture start --json
orca tab create --url <url> --json
orca wait --load networkidle --json
orca snapshot --json
orca screenshot --format jpeg --json
```

위젯 훅: `orca eval --expression`에 아래 IIFE. 탭이 없으면 `browser_no_tab` — 먼저 `tab create`.

## Fetch hook (위젯)

페이지 다른 스크립트보다 먼저 실행한다. 로그는 `window.__svcBenchLog`. 시크릿 헤더는 넣지 않는다.

```js
(() => {
  if (window.__svcBenchLog) return true;
  const log = [];
  const orig = window.fetch;
  window.fetch = async function (input, init) {
    const started = performance.now();
    const url = typeof input === "string" ? input : (input && input.url) || "";
    const method = (init && init.method) || (input && input.method) || "GET";
    try {
      const res = await orig.apply(this, arguments);
      const ttfb = performance.now() - started;
      const row = { method, url, status: res.status, ttfb_ms: ttfb, total_ms: ttfb };
      log.push(row);
      res.clone().arrayBuffer().then(() => {
        row.total_ms = performance.now() - started;
      }).catch(() => {});
      return res;
    } catch (err) {
      log.push({ method, url, status: 0, ttfb_ms: null, total_ms: performance.now() - started });
      throw err;
    }
  };
  window.__svcBenchLog = log;
  return true;
})()
```

Chrome `evaluate_script`는 같은 본문을 `() => { ...; return true; }`로 감싼다.

로그 회수: `() => window.__svcBenchLog || []` → 패키지 밖 `$RAW_INPUT`. 그다음 `ingest_network.py`로 `evidence/network/session.json`을 만든다. 원본 hook/HAR는 패키지에 두지 않는다.
