# PHASE 09. TV 마음나무·SSE 자동 재연결

이 문서는 VS Code Codex에 그대로 붙여넣어 사용할 수 있는 Phase 작업 지시서다.  
모든 작업은 `docs/codex-common-rules.md`를 우선 기준으로 삼는다.


## 목표

TV 전용 화면 `/display/:eventSlug`와 SSE 기반 키워드 집계 스트림을 구현한다.  
TV에는 개인 결과, 점수, 위험 플래그, 원문 문장을 표시하지 않고, 익명화·정제된 키워드와 참여자 수만 표시한다. SSE 연결이 끊겨도 마지막 데이터를 유지하고 자동 재연결해야 한다.

## 작업 전 확인 사항

```txt
- Phase 08에서 keywords가 저장되는지 확인한다.
- docs/11-tv-display-policy.md를 반드시 읽는다.
- TV에는 원문을 표시하지 않는다는 원칙을 확인한다.
- SSE가 끊길 수 있고 자동 재연결되어야 한다는 현장 운영 기준을 확인한다.
```

## 참조 문서

```txt
- docs/codex-common-rules.md
- docs/03-system-architecture.md
- docs/05-api-spec.md
- docs/06-frontend-structure.md
- docs/07-backend-structure.md
- docs/10-llm-keyword-policy.md
- docs/11-tv-display-policy.md
- docs/13-security-privacy-policy.md
- docs/15-testing-operation-checklist.md
```

## 수정 또는 생성할 파일

```txt
api/app/
├── api/routes/display.py
├── schemas/display.py
├── services/display_aggregate.py
├── services/sse.py
└── repositories/display.py

api/tests/
├── test_display_aggregate.py
└── test_display_api_privacy.py

web/src/
├── api/display.ts
├── routes/DisplayRoutes.tsx
├── pages/display/DisplayPage.tsx
├── hooks/useDisplaySse.ts
├── hooks/useDisplaySnapshot.ts
├── components/display/TreeWordCloud.tsx
├── components/display/TopKeywordsPanel.tsx
├── components/display/ParticipantCount.tsx
├── components/display/ConnectionStatusBadge.tsx
└── components/display/DisplayNotice.tsx
```

## 구현 내용

### 1. TV 표시 데이터 집계

집계 API 예시:

```http
GET /api/events/{eventSlug}/display/snapshot
```

SSE endpoint:

```http
GET /api/events/{eventSlug}/stream
```

snapshot/SSE payload에는 다음만 포함한다.

```json
{
  "eventSlug": "fire-expo-2026",
  "participantCount": 120,
  "completedCount": 90,
  "topMindSignalKeywords": [
    { "text": "긴장", "weight": 12 }
  ],
  "topSupportKeywords": [
    { "text": "응원", "weight": 18 }
  ],
  "treeKeywords": [
    { "text": "쉼", "weight": 20, "category": "recovery" }
  ],
  "generatedAt": "2026-05-13T00:00:00Z"
}
```

반환 금지:

```txt
- mind_card body
- reply body
- answers
- scale_scores
- risk_flags
- session id
- resume token
- safety_status 상세
- admin moderation data
```

### 2. 집계 기준

키워드 포함 기준:

```txt
- keywords.status=active
- source가 public_restriction 대상이 아니어야 함
- source safety_status=safe 우선
- hidden/excluded 키워드는 제외
```

참여자 수 기준:

```txt
participantCount:
- event 기준 생성된 세션 수 또는 동의 완료 세션 수 중 문서 기준에 맞게 선택

completedCount:
- completion_codes issued/redeemed 또는 sessions.completed 기준
```

선택 기준을 코드 주석 또는 문서에 명시한다.

### 3. SSE 스트림

구현 기준:

```txt
- text/event-stream 형식으로 전송한다.
- 일정 주기로 snapshot을 전송한다.
- 변경 감지가 어렵다면 MVP에서는 3~5초 interval polling 기반 SSE도 허용한다.
- keepalive/ping 이벤트를 보낼 수 있다.
- 클라이언트 연결 종료 시 generator가 정리된다.
```

사용 가능 방식:

```txt
- FastAPI StreamingResponse
- 또는 sse-starlette
```

단, dependency를 추가하면 이유를 보고한다.

### 4. TV 화면

라우트:

```txt
/display/:eventSlug
```

화면 구성:

```txt
- 중앙: 나무 잎 형태 워드클라우드
- 우측 또는 하단: 참여자 수, TOP 키워드
- 하단: “본 이벤트는 진단이나 치료가 아닌 체험입니다” 안내
- 하단: “TV에는 원문이 아닌 익명 키워드만 표시됩니다” 안내
- 작은 배지: 연결 상태
```

워드클라우드 구현 기준:

```txt
- MVP에서는 정확한 나무 형태 알고리즘보다 안정적 표시를 우선한다.
- 잎 모양 배치가 어렵다면 CSS 기반 tree canopy layout으로 시작한다.
- 텍스트가 겹쳐 읽기 어려운 경우 간단한 flex/wrap layout으로 fallback한다.
```

### 5. SSE 자동 재연결과 마지막 데이터 유지

`useDisplaySse` 구현 기준:

```txt
- EventSource로 stream endpoint에 연결한다.
- 연결이 끊기면 자동 재연결한다.
- 재연결 중에도 마지막 snapshot을 계속 표시한다.
- 장시간 실패 시 ConnectionStatusBadge에 “연결 재시도 중”을 작게 표시한다.
- 초기 로딩 또는 SSE 실패 시 snapshot API를 polling fallback으로 사용할 수 있다.
```

금지:

```txt
- 연결 실패 시 TV 화면을 빈 화면으로 만들지 않는다.
- SSE 재연결 중 기존 키워드를 삭제하지 않는다.
```

### 6. 테스트

필수 테스트:

```txt
- display snapshot이 원문 body를 포함하지 않는다.
- 위험/비공개/숨김 키워드가 집계에서 제외된다.
- active 키워드는 집계에 포함된다.
- SSE endpoint가 event-stream content type으로 응답한다.
- 프론트 hook이 마지막 snapshot을 유지한다.
- 연결 상태 배지가 표시된다.
```

## 금지 사항

```txt
- TV에 마음카드 원문 또는 응원 문장 원문을 표시하지 않는다.
- TV에 개인 결과, 척도 점수, 위험 플래그, 세션 정보를 표시하지 않는다.
- WebSocket으로 임의 변경하지 않는다. MVP 기준은 SSE다.
- 관리자 검수 기능을 구현하지 않는다. Phase 10 범위다.
- display 화면에 관리자 로그인 또는 관리자 기능을 섞지 않는다.
```

## 완료 기준

```txt
- /display/:eventSlug 화면이 동작한다.
- snapshot API가 익명 키워드와 참여자 수만 반환한다.
- SSE stream이 주기적으로 snapshot을 전송한다.
- TV 화면은 SSE 연결이 끊겨도 마지막 데이터를 유지한다.
- 자동 재연결 또는 polling fallback이 동작한다.
- 원문/점수/위험 플래그가 TV payload에 포함되지 않는다.
- 관련 테스트가 통과한다.
```

## 테스트 방법

```bash
cd api
pytest tests/test_display_aggregate.py tests/test_display_api_privacy.py
```

프론트엔드:

```bash
cd web
npm run build
npm run test -- --run
```

수동 확인:

```txt
1. keywords가 있는 이벤트 준비
2. /display/{eventSlug} 접속
3. TV 화면에 키워드와 참여자 수 표시 확인
4. API 서버를 잠시 중단
5. 화면이 빈 화면이 되지 않고 마지막 데이터 유지 확인
6. API 서버 재시작 후 자동 갱신 확인
```

## 작업 후 보고 형식

```txt
작업 후 다음 형식으로 보고한다.

1. 변경 파일 목록
   - 경로
   - 변경 이유

2. 구현 내용 요약
   - 이번 Phase에서 완료한 기능
   - docs 기준과 맞춘 부분

3. 실행 및 테스트 결과
   - 실행한 명령
   - 성공/실패 여부
   - 실패 시 원인과 남은 조치

4. TODO 및 남은 작업
   - 임시 구현이 있다면 이유와 위치
   - 다음 Phase에서 이어서 해야 할 사항

5. 범위 준수 확인
   - 현재 Phase 범위 밖 기능을 구현하지 않았는지
   - 기술 스택을 임의 변경하지 않았는지
   - 실제 API Key 또는 운영 Secret을 코드에 넣지 않았는지
```
