# 안전

무조건 금지. 사용자 승인이나 `mutations_allowed`로도 허용하지 않는다.

- 인증 우회, 캡차 우회, WAF 우회
- 메시지 전송
- 결제
- 로그아웃
- 삭제
- Reset
- 그 밖의 파괴적 작업
- 새 worktree 생성·사용
- 가입·권한 변경
- 토큰·쿠키·일회용 로그인 URL을 산출물에 남김
- 대상 AI 화면 수치를 원천 데이터로 인용
- `logged-in`을 사용자 세션 없이 진행

허용 (무승인 read-only):

- 공개 GET
- 정적 페이지
- 이미 열린 화면 열람
- 사용자가 이미 연 세션에서의 읽기 전용 클릭
- 읽기 전용 API 재현. 본문에서 시크릿 필드는 삭제

기본 mutation은 0건이다. `run.json`의 `mutations_allowed`는 기본 `[]`다. 비어 있으면 상태 변경을 하지 않는다.

다음은 사용자의 명시 승인과 `mutations_allowed`에 정확한 액션이 있을 때만 실행한다.

- 비파괴 POST
- 폼 제출
- 유료 추론
- 로그인
- 공식 설치

대표 시도·대표 질의는 기본 0건이다. 미승인이면 실행하지 않고 docs-only 또는 기존 결과 관측으로 남긴다.

네트워크 덤프는 헤더에서 `cookie`, `authorization`, `set-cookie`, `x-api-key`를 지운 뒤에만 `evidence/network/`에 넣는다.
