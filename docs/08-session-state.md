# 08. Session State

## 1. 목적

이 문서는 마음나무 MVP의 익명 세션 상태, 상태 전이, 재접속 복구, 프론트엔드 임시 상태 관리 기준을 정의한다.

세션 설계의 핵심은 다음이다.

```txt
- 참가자는 회원가입하지 않는다.
- 원문 session key 또는 resume token은 DB에 저장하지 않는다.
- 세션 상태는 백엔드가 최종 관리한다.
- 프론트엔드 상태는 사용자 경험을 위한 보조 상태다.
- 네트워크 실패와 새로고침을 정상 운영 조건으로 본다.
- 완료 코드는 세션당 1개만 발급한다.
```

## 2. Session Status

MVP의 세션 상태는 다음을 사용한다.

```txt
created
consented
questions_completed
summary_viewed
card_created
reply_created
completed
abandoned
```

기본 진행 방향:

```txt
created
→ consented
→ questions_completed
→ summary_viewed
→ card_created
→ reply_created
→ completed
```

`abandoned`는 운영 종료 후 장시간 미완료 세션을 정리하거나 통계에서 분리하기 위한 상태다. 참가자 플로우에서 직접 전이시키지 않아도 된다.

## 3. 상태 전이 조건

| From | To | 조건 | 처리 주체 |
|---|---|---|---|
| 없음 | created | event open 상태에서 세션 생성 또는 복구 | SessionService |
| created | consented | 필수 동의 저장 완료 | ConsentService |
| consented | questions_completed | 필수 문항 응답 저장, 점수화, 위험 플래그 계산 완료 | AnswerService |
| questions_completed | summary_viewed | 마음신호 요약 확인 처리 완료 | SummaryService |
| summary_viewed | card_created | 마음카드 1개 이상 저장 완료 | CardService |
| card_created | reply_created | 타인 카드 선택 및 응원 문장 저장 완료 | ReplyService |
| reply_created | completed | 완료 조건 검증 후 완료 코드 발급 | CompletionService |

주의:

```txt
- card_created와 reply_created는 참가자 흐름을 구분하기 위한 상태다.
- 완료 코드는 reply 저장 transaction 안에서 함께 발급할 수 있다.
- 중복 호출 시 이미 발급된 완료 코드를 반환해야 한다.
```

## 4. last_step 기준

`session.status`는 서버 기준의 완료 상태이고, `last_step`은 UI 복구를 위한 보조값이다.

예시:

```txt
status = consented
last_step = questions/phq9

status = questions_completed
last_step = summary

status = card_created
last_step = cards/select
```

프론트엔드는 `last_step`을 참고해 이동하되, 접근 허용 여부는 `status` 기준으로 판단한다.

## 5. 세션 생성과 복구

### 5.1 최초 진입

```txt
QR 접속
→ GET /api/events/{eventSlug}/public
→ localStorage resumeToken 없음
→ POST /api/events/{eventSlug}/sessions
→ 새 session 생성
→ resumeToken 반환
→ 프론트엔드가 resumeToken 저장
```

DB 저장 기준:

```txt
anonymous_key_hash: 서버가 생성한 익명 key hash
resume_token_hash: 클라이언트 복구 token의 hash
```

원문 token은 DB에 저장하지 않는다.

### 5.2 재접속

```txt
QR 재접속 또는 새로고침
→ localStorage resumeToken 조회
→ POST /api/events/{eventSlug}/sessions with resumeToken
→ 서버가 hash로 기존 session 조회
→ session.status와 last_step 반환
→ 프론트엔드가 적절한 화면으로 이동
```

## 6. 프론트엔드 임시 상태

### 6.1 저장 가능한 값

```txt
localStorage:
- resumeToken
- sessionId

sessionStorage:
- questionsCache
- questionDraft
- currentQuestionNo
- lastSubmittedAt
```

### 6.2 저장 금지 또는 제한 값

```txt
localStorage 저장 금지:
- 마음카드 원문
- 응원 문장 원문
- 척도 점수
- 위험 플래그
- 관리자 토큰 외 민감 운영 데이터

sessionStorage 임시 저장 후 완료 시 삭제:
- 문항 응답 draft
```

자유입력 원문은 장기 로컬 저장하지 않는다.

## 7. Progress 계산

세션 상태 조회 API는 프론트엔드 복구를 위해 progress object를 반환한다.

예시:

```json
{
  "progress": {
    "consentAccepted": true,
    "questionsCompleted": true,
    "summaryViewed": true,
    "mindCardCount": 1,
    "selectedCard": true,
    "replyCreated": false,
    "completionCodeIssued": false
  }
}
```

progress는 DB의 실제 데이터를 기준으로 계산한다.

```txt
consentAccepted:
- consent_logs 존재

questionsCompleted:
- 필수 questions에 대한 answers 존재
- scale_scores 존재
- risk_flags 존재

summaryViewed:
- summaries.viewed_at 존재

mindCardCount:
- mind_cards count

selectedCard:
- card_selections 존재

replyCreated:
- replies 존재

completionCodeIssued:
- completion_codes 존재
```

## 8. Route Guard 기준

프론트엔드 route guard는 다음처럼 동작한다.

```txt
/e/:eventSlug/consent:
- created 이상 접근 가능

/e/:eventSlug/questions:
- consented 이상 접근 가능

/e/:eventSlug/summary:
- questions_completed 이상 접근 가능

/e/:eventSlug/cards/new:
- summary_viewed 이상 접근 가능

/e/:eventSlug/cards/select:
- card_created 이상 접근 가능

/e/:eventSlug/replies/new:
- card_created 이상 + selectedCard 필요

/e/:eventSlug/complete:
- completed 또는 completionCodeIssued 필요
```

프론트엔드 guard가 우회되어도 백엔드 API가 상태를 다시 검증한다.

## 9. Idempotent 처리

### 9.1 동의 저장

같은 세션의 같은 `consent_version` 동의 저장은 중복 생성보다 기존 동의 확인 후 status 유지가 적절하다.

```txt
이미 consented 상태:
- 기존 consent 반환
- status를 되돌리지 않음
```

### 9.2 응답 저장

`answers`는 `UNIQUE(session_id, question_id)` 기준으로 upsert한다.

```txt
같은 문항 재제출:
- answer_value와 score_value 업데이트
- 필수 문항 전체가 있으면 재점수화 가능
```

### 9.3 요약 조회

요약이 이미 있으면 같은 요약을 반환한다. LLM 보정이 나중에 도착해도 참가자에게 이미 보여준 `final_text`를 불안정하게 바꾸지 않는다.

### 9.4 완료 코드 발급

`completion_codes`는 `UNIQUE(event_id, session_id)`를 가진다.

```txt
이미 완료 코드 있음:
- 기존 code 반환
- 새 code 발급 금지
```

## 10. 네트워크 실패 처리

### 10.1 문항 제출 실패

```txt
사용자 입력 유지
→ 오류 안내
→ 재시도 버튼 표시
→ 같은 payload 재전송
→ 서버는 upsert 처리
```

### 10.2 마음카드 제출 실패

```txt
입력값 화면 유지
→ 재시도 가능
→ 성공 후 keyword job 생성
→ 다음 단계 이동
```

동일 카드 중복 생성을 줄이기 위해 client-generated idempotency key를 사용할 수 있다.

### 10.3 응원 문장 제출 실패

```txt
입력값 화면 유지
→ 재시도 가능
→ 성공 시 completion code 발급 가능
```

## 11. Abandoned 처리

MVP에서는 abandoned 처리를 운영 필수 기능으로 만들지 않는다. 단, 이벤트 종료 후 통계 정리를 위해 다음 기준을 둘 수 있다.

```txt
- event closed 이후 미완료 session
- created 또는 consented 상태로 장시간 진행 없음
- 운영자가 수동 정리 또는 배치 정리
```

abandoned 처리 시 원문 데이터 삭제 여부는 별도 보존 정책을 따른다.

## 12. 완료 후 정리

완료 화면 진입 시 프론트엔드는 다음을 수행한다.

```txt
- questionDraft 삭제
- currentQuestionNo 삭제
- 임시 입력값 삭제
- resumeToken은 유지 가능
```

resumeToken은 완료 코드 재조회와 재방문 복구를 위해 이벤트 종료 전까지 유지할 수 있다. 운영 정책상 종료 후 삭제 안내를 제공할 수 있다.

## 13. 세션 상태 금지 사항

```txt
- 프론트엔드 상태만으로 completed 처리하지 않는다.
- LLM job 완료 여부를 session.status 전이 조건으로 사용하지 않는다.
- keyword job 실패 때문에 completed 전이를 막지 않는다.
- 안전 필터 review/exclude 때문에 참가자 완료를 막지 않는다.
- 원문 resumeToken을 DB 또는 로그에 저장하지 않는다.
- 관리자 지급 처리와 참가자 완료 처리를 같은 상태로 취급하지 않는다.
```

## 14. 테스트 기준

```txt
- 최초 진입 시 created 세션 생성
- resumeToken으로 기존 세션 복구
- 동의 후 consented 전이
- 응답 제출 후 questions_completed 전이
- 요약 확인 후 summary_viewed 전이
- 마음카드 작성 후 card_created 전이
- 응원 작성 후 completed 전이와 완료 코드 발급
- 완료 코드 중복 발급 방지
- 새로고침 후 last_step 복구
- 제출 실패 후 재시도 성공
```
