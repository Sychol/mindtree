# PHASE 03. 이벤트·익명 세션·필수 동의 API

이 문서는 VS Code Codex에 그대로 붙여넣어 실행할 수 있는 구현 지시서다.

## 목표

참가자가 QR 또는 URL로 이벤트에 접속했을 때 필요한 초기 API를 구현한다.

이 Phase에서는 다음 기능을 구현한다.

```txt
- 공개 이벤트 설정 조회
- 익명 세션 생성 또는 복구
- 세션 상태 조회
- 필수 동의 저장
- created → consented 상태 전이
```

완료 후에는 참가자 프론트엔드가 이벤트 진입, 세션 생성/복구, 동의 저장을 호출할 수 있어야 한다.

## 작업 전 확인 사항

Codex는 먼저 아래를 수행한다.

```txt
1. 현재 api/ 구조와 Phase 01~02 구현 결과를 확인한다.
2. docs/codex-common-rules.md를 읽는다.
3. docs/04-data-model.md에서 events, sessions, consent_logs를 확인한다.
4. docs/05-api-spec.md에서 Public Event API와 Session API를 확인한다.
5. docs/08-session-state.md를 읽는다.
6. docs/13-security-privacy-policy.md의 익명 세션 원칙을 확인한다.
```

## 참조 문서

```txt
docs/codex-common-rules.md
docs/04-data-model.md
docs/05-api-spec.md
docs/08-session-state.md
docs/13-security-privacy-policy.md
```

## 수정 또는 생성할 파일

상황에 따라 아래 파일을 생성 또는 보완한다.

```txt
api/app/api/router.py
api/app/api/routes/events.py
api/app/api/routes/sessions.py
api/app/schemas/events.py
api/app/schemas/sessions.py
api/app/services/events.py
api/app/services/sessions.py
api/app/repositories/events.py
api/app/repositories/sessions.py
api/app/repositories/consent.py
api/app/core/security.py
api/tests/test_public_event_api.py
api/tests/test_session_api.py
```

## 구현 내용

### 1. 공개 이벤트 설정 조회 API

아래 API를 구현한다.

```http
GET /api/events/{eventSlug}/public
```

응답은 `docs/05-api-spec.md`를 따른다.

필수 응답 항목:

```txt
- event.slug
- event.name
- event.status
- event.description
- event.consentVersion
- event.settings.displayEnabled
- event.settings.maxMindCardsPerSession
- notices.notDiagnosis
- notices.anonymousKeywordDisplay
```

구현 기준:

```txt
- eventSlug로 events.slug를 조회한다.
- event가 없으면 EVENT_NOT_FOUND를 반환한다.
- draft 또는 archived 이벤트는 공개 진입을 제한한다.
- closed 이벤트의 정책은 docs 기준에 맞춰 명확히 처리한다.
- TV나 관리자용 민감 설정은 반환하지 않는다.
```

### 2. 익명 세션 생성 또는 복구 API

아래 API를 구현한다.

```http
POST /api/events/{eventSlug}/sessions
```

요청 예시:

```json
{
  "resumeToken": "client-generated-token-if-exists",
  "clientMeta": {
    "device": "mobile",
    "timezone": "Asia/Seoul"
  }
}
```

응답 예시:

```json
{
  "session": {
    "id": "uuid",
    "eventSlug": "fire-expo-2026",
    "status": "created",
    "lastStep": "landing"
  },
  "resumeToken": "new-client-resume-token"
}
```

구현 기준:

```txt
- resumeToken이 없으면 서버가 새 resumeToken을 생성해 반환한다.
- resumeToken이 있으면 hash를 계산해 기존 세션을 찾는다.
- DB에는 원문 resumeToken을 저장하지 않는다.
- session에는 resume_token_hash 또는 anonymous_key_hash만 저장한다.
- 동일 token으로 재호출하면 기존 세션을 반환한다.
- 세션 생성/복구는 중복 호출에 안전해야 한다.
```

해시 구현 기준:

```txt
- 원문 token을 저장하지 않는다.
- settings의 secret 또는 별도 salt를 사용해 HMAC 또는 안전한 hash를 사용한다.
- local 환경에서도 deterministic하게 동작해야 한다.
```

### 3. 세션 상태 조회 API

아래 API를 구현한다.

```http
GET /api/sessions/{sessionId}
```

응답은 `docs/05-api-spec.md`의 `session`과 `progress` 구조를 따른다.

구현 기준:

```txt
- sessionId로 세션을 조회한다.
- progress는 DB 상태를 기준으로 계산한다.
- 프론트엔드 lastStep만 믿지 않는다.
- 완료 코드 발급 여부, 카드 수, 응원 작성 여부 등은 실제 테이블 기준으로 계산한다.
```

Phase 03에서는 아직 질문/카드/응원 테이블 데이터가 없을 수 있다. 이 경우 progress 필드는 기본 false 또는 0으로 반환하고, 이후 Phase에서 보완한다.

### 4. 필수 동의 저장 API

아래 API를 구현한다.

```http
POST /api/sessions/{sessionId}/consent
```

요청 예시:

```json
{
  "consentVersion": "v1",
  "acceptedItems": {
    "eventIsNotDiagnosis": true,
    "anonymousKeywordDisplay": true,
    "cardMayBeShownAnonymously": true,
    "noIdentifyingInfo": true,
    "adminModeration": true
  }
}
```

구현 기준:

```txt
- 필수 동의 항목이 모두 true인지 검증한다.
- consent_logs에 기록한다.
- 중복 호출 시 기존 동의 기록을 재사용하거나 idempotent하게 처리한다.
- session.status를 created에서 consented로 전이한다.
- 이미 consented 이후 상태이면 역전이하지 않는다.
- ip와 user_agent는 원문 저장하지 않고 필요 시 hash만 저장한다.
```

### 5. 세션 상태 전이 기본 규칙

Phase 03에서 구현할 전이는 다음이다.

```txt
created → consented
```

구현 기준:

```txt
- 상태 전이는 service layer에서 처리한다.
- repository는 단순 조회/저장 역할로 제한한다.
- 프론트엔드 요청이 임의 status 값을 보내도 그대로 반영하지 않는다.
```

### 6. 테스트

필수 테스트:

```txt
- 공개 이벤트 조회 성공
- 없는 이벤트 조회 시 EVENT_NOT_FOUND
- 세션 생성 성공
- 같은 resumeToken으로 세션 복구 성공
- DB에 원문 resumeToken이 저장되지 않음
- 필수 동의 저장 성공
- 필수 항목 누락 시 BAD_REQUEST
- 동의 후 session.status가 consented가 됨
```

## 금지 사항

```txt
- 문항 조회, 응답 저장, 점수화 API를 구현하지 않는다.
- 마음신호 요약, 마음카드, 응원 문장 API를 구현하지 않는다.
- 관리자 API를 구현하지 않는다.
- 원문 resumeToken, raw session key, IP, user agent를 그대로 저장하지 않는다.
- 프론트엔드가 보낸 status 값을 그대로 DB에 반영하지 않는다.
- LLM 관련 기능을 구현하지 않는다.
```

## 완료 기준

```txt
- GET /api/events/{eventSlug}/public 동작
- POST /api/events/{eventSlug}/sessions 동작
- GET /api/sessions/{sessionId} 동작
- POST /api/sessions/{sessionId}/consent 동작
- 세션 복구가 hash 기반으로 동작
- 동의 저장 후 created → consented 상태 전이 동작
- 관련 테스트 통과
```

## 테스트 방법

```bash
cd api
pytest
```

수동 확인 예시:

```bash
curl http://localhost:8000/api/events/fire-expo-2026/public

curl -X POST http://localhost:8000/api/events/fire-expo-2026/sessions \
  -H 'Content-Type: application/json' \
  -d '{"clientMeta":{"device":"mobile","timezone":"Asia/Seoul"}}'
```

필요 시 테스트용 이벤트 seed가 없으면 테스트 fixture 또는 local seed를 만든다. 단, seed 구현이 커지면 최소 범위로 제한하고 TODO를 남긴다.

## 작업 후 보고 형식

```md
## 작업 요약
- 공개 이벤트 조회, 익명 세션 생성/복구, 세션 상태 조회, 동의 저장 API를 구현했다.

## 변경 파일
- api/app/api/routes/events.py: 공개 이벤트 API 추가
- api/app/api/routes/sessions.py: 세션 및 동의 API 추가
- ...

## 실행 방법
- cd api && pytest
- uvicorn app.main:app --reload

## 테스트 결과
- ...

## 남은 작업 / TODO
- 문항 조회와 응답 저장은 Phase 04에서 구현 필요
- 참가자 프론트엔드는 Phase 05에서 구현 필요

## 주의 사항
- 원문 resumeToken은 DB에 저장하지 않고 hash만 저장하도록 구현함
```
