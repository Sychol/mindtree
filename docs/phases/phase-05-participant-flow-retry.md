# PHASE 05. 참가자 모바일 플로우와 네트워크 재시도

이 문서는 VS Code Codex에 그대로 붙여넣어 실행할 수 있는 구현 지시서다.

## 목표

참가자 모바일 웹의 기본 흐름을 구현한다.

이 Phase의 핵심은 박람회장 네트워크 불안정 상황에서도 참가자가 가능한 한 끊기지 않고 문항 응답을 진행할 수 있게 만드는 것이다.

구현 범위는 다음이다.

```txt
- QR/URL 진입 라우트
- 이벤트 설정 조회
- 익명 세션 생성/복구
- 필수 동의 화면
- 1~77번 문항 전체 선로딩
- 문항 응답 로컬 진행 상태 관리
- 응답 제출 실패 시 재시도
- 세션 재접속 복구
```

## 작업 전 확인 사항

Codex는 먼저 아래를 수행한다.

```txt
1. 현재 web/ 구조와 Phase 00 산출물을 확인한다.
2. 현재 api/에서 Phase 03~04 API가 구현되어 있는지 확인한다.
3. docs/codex-common-rules.md를 읽는다.
4. docs/05-api-spec.md에서 이벤트, 세션, 문항, 응답 API를 확인한다.
5. docs/06-frontend-structure.md를 읽는다.
6. docs/08-session-state.md를 읽는다.
7. docs/15-testing-operation-checklist.md에서 네트워크 실패 테스트 항목을 확인한다.
```

## 참조 문서

```txt
docs/codex-common-rules.md
docs/05-api-spec.md
docs/06-frontend-structure.md
docs/08-session-state.md
docs/13-security-privacy-policy.md
docs/15-testing-operation-checklist.md
```

## 수정 또는 생성할 파일

상황에 따라 아래 파일을 생성 또는 보완한다.

```txt
web/package.json
web/vite.config.ts
web/tsconfig.json
web/src/main.tsx
web/src/App.tsx
web/src/routes/ParticipantRoutes.tsx
web/src/pages/participant/LandingPage.tsx
web/src/pages/participant/ConsentPage.tsx
web/src/pages/participant/QuestionsPage.tsx
web/src/pages/participant/QuestionReviewPage.tsx
web/src/pages/participant/SubmitResultPage.tsx
web/src/components/participant/QuestionRenderer.tsx
web/src/components/participant/ProgressHeader.tsx
web/src/components/common/RetryNotice.tsx
web/src/lib/apiClient.ts
web/src/lib/storage.ts
web/src/hooks/useEventSession.ts
web/src/hooks/usePreloadedQuestions.ts
web/src/hooks/useQuestionProgress.ts
web/src/hooks/useSubmitWithRetry.ts
web/src/types/api.ts
web/src/types/session.ts
web/src/types/questions.ts
web/src/styles/global.css
```

기존 React/Vite 구조가 있으면 삭제하지 말고 보완한다.

## 구현 내용

### 1. React/Vite/TypeScript 기반 확인

웹 앱은 React, Vite, TypeScript 기준으로 구현한다.

구현 기준:

```txt
- Next.js로 변경하지 않는다.
- 상태 관리 라이브러리는 필요 최소한만 사용한다.
- 별도 대형 UI 라이브러리를 임의로 추가하지 않는다.
- 모바일 화면을 우선한다.
```

### 2. 참가자 라우트 구조

기본 라우트 예시는 다음이다.

```txt
/:eventSlug
/:eventSlug/consent
/:eventSlug/questions
/:eventSlug/questions/review
/:eventSlug/submit-result
```

Phase 06 이후 추가될 라우트는 placeholder 링크 또는 TODO로 남긴다.

```txt
/:eventSlug/summary
/:eventSlug/cards/new
/:eventSlug/cards/select
/:eventSlug/replies/new
/:eventSlug/complete
```

이 Phase에서 마음신호 요약, 카드, 응원, 완료 화면을 구현하지 않는다.

### 3. 이벤트 설정 조회와 세션 생성/복구

진입 시 아래 순서로 처리한다.

```txt
1. eventSlug로 공개 이벤트 설정 조회
2. localStorage 또는 sessionStorage에서 resumeToken 확인
3. POST /api/events/{eventSlug}/sessions 호출
4. 서버가 반환한 resumeToken 저장
5. GET /api/sessions/{sessionId}로 progress 확인
6. 세션 상태에 따라 적절한 화면으로 이동
```

저장소 기준:

```txt
- resumeToken은 브라우저 재접속 복구를 위해 저장 가능하다.
- 문항 응답 임시값은 최소 범위로 저장한다.
- 완료 후 민감한 임시 응답값은 삭제한다.
```

### 4. 필수 동의 화면

동의 화면은 Phase 03 API를 사용한다.

필수 동의 항목:

```txt
- 본 이벤트는 진단이나 치료가 아닌 체험형 마음 점검입니다.
- TV에는 원문이 아닌 익명 키워드만 표시됩니다.
- 마음카드는 익명 상태로 다른 참가자에게 보일 수 있습니다.
- 실명, 소속, 연락처, 구체적 장소, 날짜, 사건명은 입력하지 않습니다.
- 관리자는 개인정보, 위기 표현, 부적절 표현을 수정·숨김·삭제할 수 있습니다.
```

구현 기준:

```txt
- 모든 필수 항목이 체크되어야 다음 단계로 이동한다.
- 동의 저장 실패 시 체크 상태를 유지하고 재시도 버튼을 제공한다.
- 동의 성공 후 questions 라우트로 이동한다.
```

### 5. 1~77번 문항 전체 선로딩

문항 화면 진입 시 아래 API를 한 번 호출한다.

```http
GET /api/events/{eventSlug}/questions
```

구현 기준:

```txt
- 받은 문항 전체를 프론트 상태에 저장한다.
- 문항 이동은 로컬 상태 기준으로 처리한다.
- 각 문항 이동마다 서버에 저장하지 않는다.
- 전체 제출 시점에만 answers/bulk API를 호출한다.
- 문항 수, 현재 위치, 진행률을 보여준다.
```

### 6. 질문 렌더링

`QuestionRenderer`는 API에서 받은 `questionType`에 따라 렌더링한다.

지원 타입:

```txt
single_select
multi_select
likert
text
number
```

구현 기준:

```txt
- required 문항은 미응답 상태로 다음 단계 이동을 제한한다.
- text 응답은 길이 제한을 둔다.
- 개인정보 입력 금지 안내를 text 입력 근처에 표시한다.
- 점수화 계산은 프론트에서 하지 않는다.
```

### 7. 로컬 진행 상태와 재접속 복구

구현 기준:

```txt
- 현재 question index를 저장한다.
- 임시 응답값을 저장한다.
- eventSlug와 sessionId 기준으로 저장 key를 분리한다.
- 브라우저 새로고침 후 현재 단계와 입력값을 복구한다.
- 완료 후 임시 응답값을 삭제한다.
```

민감 데이터 저장 주의:

```txt
- 원문 마음카드/응원문장은 이 Phase에서 다루지 않는다.
- 문항 응답 임시 저장은 현장 네트워크 대응을 위한 최소 범위로 제한한다.
- localStorage보다 sessionStorage를 우선 검토한다.
```

### 8. 응답 제출과 재시도

전체 문항 완료 후 아래 API를 호출한다.

```http
POST /api/sessions/{sessionId}/answers/bulk
```

구현 기준:

```txt
- 제출 중 버튼 중복 클릭을 방지한다.
- 네트워크 실패 시 입력값을 유지한다.
- 재시도 버튼을 제공한다.
- 실패 메시지는 짧고 명확하게 제공한다.
- 성공 후 임시 응답값을 정리하고 다음 단계로 이동한다.
```

재시도 UI 문구 예시:

```txt
일시적으로 연결이 원활하지 않습니다. 입력한 내용은 유지되어 있습니다. 다시 제출해 주세요.
```

### 9. API Client

`web/src/lib/apiClient.ts`를 만든다.

구현 기준:

```txt
- base URL은 환경변수에서 읽는다.
- 공통 error object를 파싱한다.
- timeout 또는 AbortController를 적용한다.
- 참가자 API 함수는 명시적으로 작성한다.
- 사용자 입력으로 URL path를 무제한 조합하지 않는다.
```

### 10. 테스트

가능한 범위에서 다음을 확인한다.

```txt
- TypeScript build 통과
- 참가자 진입 화면 렌더링
- 동의 체크 전 다음 버튼 비활성화
- 문항 API mock으로 1~77번 렌더링
- 제출 실패 시 입력값 유지
- resumeToken 저장 및 복구
```

테스트 프레임워크가 아직 없다면 최소한 `npm run build`를 통과시킨다.

## 금지 사항

```txt
- 마음신호 요약 화면을 완성 구현하지 않는다.
- 마음카드, 타인 카드, 응원 문장, 완료 코드 화면을 구현하지 않는다.
- TV 화면이나 관리자 화면을 구현하지 않는다.
- 프론트엔드에서 척도 점수화나 위험 플래그를 최종 계산하지 않는다.
- 문항을 프론트엔드에 하드코딩하지 않는다.
- 원문 응답을 장기 보관하는 구조를 만들지 않는다.
```

## 완료 기준

```txt
- 참가자 진입 라우트가 동작한다.
- 이벤트 설정 조회와 세션 생성/복구가 동작한다.
- 필수 동의 저장이 동작한다.
- 1~77번 문항을 API에서 선로딩한다.
- 문항 진행 상태가 로컬에서 유지된다.
- 전체 제출 시 answers/bulk API를 호출한다.
- 제출 실패 시 재시도 가능하다.
- npm run build가 통과한다.
```

## 테스트 방법

```bash
cd web
npm install
npm run build
```

API와 함께 확인:

```bash
docker compose up --build
# 브라우저에서 http://localhost:5173/fire-expo-2026 접속
```

네트워크 실패 확인:

```txt
1. 문항 응답을 일부 입력한다.
2. API 서버를 잠시 중지하거나 네트워크 실패를 시뮬레이션한다.
3. 제출을 시도한다.
4. 입력값이 유지되고 재시도 버튼이 보이는지 확인한다.
5. API 서버 복구 후 다시 제출한다.
```

## 작업 후 보고 형식

```md
## 작업 요약
- 참가자 모바일 진입, 동의, 문항 선로딩, 로컬 진행 상태, 제출 재시도 플로우를 구현했다.

## 변경 파일
- web/src/routes/ParticipantRoutes.tsx: 참가자 라우트 추가
- web/src/hooks/useQuestionProgress.ts: 문항 진행 상태 관리
- ...

## 실행 방법
- cd web && npm run build
- docker compose up --build

## 테스트 결과
- ...

## 남은 작업 / TODO
- 마음신호 요약 화면은 Phase 06에서 구현 필요
- 마음카드/응원/완료 화면은 Phase 07에서 구현 필요

## 주의 사항
- 척도 점수화는 프론트에서 하지 않고 서버 결과만 사용함
```
