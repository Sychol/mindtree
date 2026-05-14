# 07. Backend Structure

## 1. 목적

이 문서는 마음나무 MVP의 FastAPI 백엔드 구현 구조를 정의한다. 백엔드는 이벤트 설정, 익명 세션, 점수화, 위험 플래그, 공개 제한, 키워드 job, TV SSE, 관리자 검수, 상품 지급을 담당한다.

핵심 원칙은 다음이다.

```txt
- 모든 중요한 상태 전이는 백엔드 service layer에서 수행한다.
- 사용자 입력에서 직접 SQL을 생성하지 않는다.
- LLM은 진단, 위험 판단, 공개 여부 판단, 세션 상태 결정을 하지 않는다.
- LLM 또는 네트워크 실패가 참가자 완료 흐름을 막지 않는다.
- TV API는 원문을 반환하지 않는다.
- 관리자 API는 인증과 감사 로그를 전제로 한다.
```

## 2. 권장 폴더 구조

```txt
api/
  pyproject.toml 또는 requirements.txt
  alembic.ini
  app/
    main.py

    core/
      config.py
      database.py
      security.py
      enums.py
      errors.py
      logging.py
      time.py

    models/
      event.py
      session.py
      question.py
      answer.py
      scoring.py
      risk.py
      summary.py
      mind_card.py
      reply.py
      keyword.py
      completion_code.py
      admin.py
      audit.py

    schemas/
      common.py
      event.py
      session.py
      question.py
      answer.py
      scoring.py
      summary.py
      card.py
      reply.py
      display.py
      admin.py
      keyword.py
      completion.py

    routers/
      public_events.py
      sessions.py
      questions.py
      answers.py
      summaries.py
      cards.py
      replies.py
      completion.py
      display.py
      admin_auth.py
      admin_events.py
      admin_review.py
      admin_keywords.py
      admin_rewards.py
      admin_audit_logs.py

    repositories/
      event_repository.py
      session_repository.py
      question_repository.py
      answer_repository.py
      scoring_repository.py
      risk_repository.py
      summary_repository.py
      card_repository.py
      reply_repository.py
      keyword_repository.py
      keyword_job_repository.py
      completion_repository.py
      admin_repository.py
      audit_repository.py

    services/
      event_service.py
      session_service.py
      consent_service.py
      question_service.py
      answer_service.py
      scoring_service.py
      risk_service.py
      summary_service.py
      safety_filter_service.py
      card_service.py
      reply_service.py
      keyword_service.py
      keyword_job_service.py
      display_service.py
      completion_service.py
      admin_auth_service.py
      review_service.py
      reward_service.py
      audit_service.py

    llm/
      base.py
      mock_provider.py
      openai_provider.py
      prompts.py
      output_parser.py

    workers/
      keyword_worker.py
      scheduler.py

    seeds/
      events.py
      questions.py
      admin.py

    tests/
      test_health.py
      test_sessions.py
      test_scoring.py
      test_risk.py
      test_keyword_fallback.py
      test_completion_code.py
      test_display.py
      test_admin_rewards.py

  alembic/
    env.py
    versions/
```

## 3. Layer 책임

### 3.1 Router

Router는 HTTP 요청/응답만 담당한다.

```txt
- path parameter와 request body 검증
- 인증 dependency 적용
- service 호출
- response schema 반환
- 공통 error object 반환
```

Router에서 하지 말아야 할 일:

```txt
- 직접 SQL 작성
- 점수화 계산
- 위험 플래그 계산
- LLM prompt 구성
- 세션 상태 직접 변경
- 감사 로그 누락 가능성이 있는 관리자 변경 처리
```

### 3.2 Service

Service는 업무 규칙을 담당한다.

```txt
- 세션 상태 전이
- idempotent 처리
- 점수화와 위험 플래그 계산
- 공개 제한 계산
- 마음카드/응원 문장 저장 후 keyword job 생성
- 완료 조건 검증과 완료 코드 발급
- 관리자 검수 처리와 감사 로그 기록
```

Service는 repository를 통해서만 DB에 접근한다.

### 3.3 Repository

Repository는 DB query function의 집합이다.

```txt
- get_event_by_slug
- get_or_create_session
- upsert_answers
- save_scale_scores
- save_risk_flags
- list_public_cards
- create_keyword_job
- claim_next_keyword_jobs
- aggregate_display_keywords
- redeem_completion_code
```

사용자 입력으로 SQL 문자열을 조립하지 않는다. raw SQL이 필요한 경우 반드시 파라미터 바인딩을 사용한다.

### 3.4 Worker

Worker는 keyword job 처리를 담당한다.

MVP에서는 Redis/Celery를 도입하지 않고 PostgreSQL 기반 job table을 사용한다.

```txt
pending/retry_wait job 조회
→ row lock 또는 상태 변경으로 claim
→ LLM 또는 fallback 처리
→ keywords 저장
→ job 상태 succeeded 또는 failed 기록
```

개발 환경에서는 API 프로세스의 startup task로 worker를 실행할 수 있다. 운영 분리가 필요해지면 같은 코드로 별도 프로세스를 실행한다.

## 4. 주요 Router 구성

### 4.1 Public Participant Routers

```txt
GET  /api/events/{eventSlug}/public
POST /api/events/{eventSlug}/sessions
GET  /api/sessions/{sessionId}
POST /api/sessions/{sessionId}/consent
GET  /api/events/{eventSlug}/questions
PUT  /api/sessions/{sessionId}/answers/bulk
GET  /api/sessions/{sessionId}/summary
POST /api/sessions/{sessionId}/summary/viewed
POST /api/sessions/{sessionId}/cards
GET  /api/events/{eventSlug}/cards/public
POST /api/sessions/{sessionId}/selected-card
POST /api/sessions/{sessionId}/replies
GET  /api/sessions/{sessionId}/completion-code
```

### 4.2 Display Routers

```txt
GET /api/events/{eventSlug}/display/snapshot
GET /api/events/{eventSlug}/stream
```

Display API는 원문을 반환하지 않는다.

### 4.3 Admin Routers

```txt
POST /api/admin/auth/login
GET  /api/admin/events/{eventSlug}/dashboard
GET  /api/admin/events/{eventSlug}/cards
PATCH /api/admin/cards/{cardId}/review
GET  /api/admin/events/{eventSlug}/replies
PATCH /api/admin/replies/{replyId}/review
GET  /api/admin/events/{eventSlug}/keywords
PATCH /api/admin/keywords/{keywordId}
GET  /api/admin/events/{eventSlug}/keyword-jobs
POST /api/admin/keyword-jobs/{jobId}/retry
GET  /api/admin/events/{eventSlug}/completion-codes/{code}
POST /api/admin/events/{eventSlug}/completion-codes/{code}/redeem
GET  /api/admin/events/{eventSlug}/audit-logs
```

관리자 변경성 API는 감사 로그를 기록한다.

## 5. 핵심 Service 책임

### 5.1 SessionService

```txt
- resumeToken hash 생성
- 익명 세션 생성 또는 복구
- session.status 조회
- last_step 업데이트
- 상태 전이 허용 여부 검증
```

DB에는 원문 resumeToken을 저장하지 않는다.

### 5.2 AnswerService

```txt
- bulk answers 검증
- question_id가 해당 event에 속하는지 확인
- required 문항 누락 확인
- answers upsert
- 전체 문항 완료 시 scoring service 호출
- session.status = questions_completed 전이
```

### 5.3 ScoringService

```txt
- question.score_map 기준으로 score_value 계산
- scale_code별 raw_score 계산
- sub_scores 계산
- scale_scores upsert
- rule_version 기록
```

점수화는 서버에서 최종 계산한다.

### 5.4 RiskService

```txt
- PHQ-9 item9 양성 여부 계산
- 자유입력 위기 표현 감지 결과 반영
- PCL-5/K-MIES 고신호 여부 계산
- public_restriction과 help_notice_required 계산
- risk_flags upsert
```

LLM은 RiskService의 판단을 대체하지 않는다.

### 5.5 SummaryService

```txt
- scale_scores와 risk_flags 기준 템플릿 요약 생성
- LLM provider 활성화 시 문장 보정 요청 가능
- LLM 실패 또는 timeout 시 template_text를 final_text로 사용
- summary viewed 처리
```

요약 문장은 진단명이 아니라 마음신호 언어로 작성한다.

### 5.6 SafetyFilterService

```txt
- 개인정보 의심 표현 감지
- 실명/연락처/소속/구체적 사건 식별정보 감지
- 자해·자살·죽음 관련 직접 표현 감지
- 욕설/혐오/특정인 비난 감지
- safety_status와 moderation_reason 반환
```

SafetyFilterService는 LLM 없이 동작해야 한다. 정규식, 금칙어 사전, 간단한 규칙 기반으로 시작한다.

### 5.7 CardService / ReplyService

```txt
- 입력 길이와 타입 검증
- 안전 필터 적용
- content_raw 저장
- 필요 시 content_redacted 저장
- public_status 결정
- keyword job 생성
- session.status 전이
```

키워드 추출이 끝날 때까지 참가자를 대기시키지 않는다.

### 5.8 KeywordJobService / KeywordService

```txt
- keyword_jobs 생성
- pending job claim
- LLM keyword extraction
- fallback keyword extraction
- 금칙어 제거
- 불용어 제거
- 정규화
- 유사어 병합
- keywords 저장
- job 상태 기록
```

job이 실패해도 참가자 흐름은 이미 완료될 수 있어야 한다.

### 5.9 DisplayService

```txt
- TV용 키워드 집계
- participantCount와 completedCount 계산
- topMindKeywords 계산
- topSupportKeywords 계산
- cloudKeywords 계산
- SSE snapshot 생성
```

DisplayService는 원문 카드나 응원 문장을 반환하지 않는다.

### 5.10 CompletionService / RewardService

```txt
- 완료 조건 검증
- 세션당 완료 코드 1개 발급
- 완료 코드 조회
- 지급 처리
- 중복 지급 방지
- 지급 감사 로그 기록
```

## 6. Transaction 기준

다음 작업은 하나의 transaction으로 처리한다.

```txt
- answers upsert + scoring + risk_flags + session.status 전이
- mind_card 저장 + keyword_job 생성 + session.status 전이
- reply 저장 + keyword_job 생성 + completion_code 발급 + session.status 전이
- 관리자 검수 상태 변경 + 감사 로그 생성
- 완료 코드 지급 처리 + 감사 로그 생성
```

keyword worker는 job claim과 결과 저장을 명확히 분리한다.

```txt
1. claim transaction:
   pending → processing
   locked_at 설정

2. processing:
   LLM 또는 fallback 실행

3. finish transaction:
   keywords 저장
   processing → succeeded/failed/retry_wait
```

## 7. Idempotency 기준

중복 호출에 안전해야 하는 작업:

```txt
- 세션 생성/복구
- 동의 저장
- answers bulk 저장
- summary 생성/조회
- summary viewed 처리
- 마음카드 작성 중 중복 제출
- 응원 문장 작성 중 중복 제출
- 완료 코드 발급
- 상품 지급 처리
```

실행 방식:

```txt
- UNIQUE 제약 활용
- upsert 사용
- 같은 session_id에 completion_code 1개만 허용
- 같은 code의 지급은 status 조건으로 처리
- 가능하면 Idempotency-Key 기록 테이블 추가를 후속으로 고려
```

## 8. Error 처리

공통 error schema:

```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "세션을 찾을 수 없습니다.",
    "details": {}
  }
}
```

Router는 domain exception을 HTTP status와 공통 error object로 변환한다.

대표 error code:

```txt
BAD_REQUEST
UNAUTHORIZED
FORBIDDEN
EVENT_NOT_FOUND
EVENT_NOT_OPEN
SESSION_NOT_FOUND
INVALID_SESSION_STATUS
CONSENT_REQUIRED
QUESTIONS_NOT_COMPLETED
CARD_NOT_FOUND
COMPLETION_CODE_ALREADY_REDEEMED
RATE_LIMITED
INTERNAL_ERROR
```

## 9. 설정 관리

`app/core/config.py`는 환경변수를 typed settings로 읽는다.

```txt
APP_ENV
DATABASE_URL
CORS_ORIGINS
SECRET_KEY
ADMIN_JWT_EXPIRES_MINUTES
LLM_ENABLED
LLM_PROVIDER
LLM_API_KEY
LLM_TIMEOUT_SECONDS
KEYWORD_WORKER_ENABLED
KEYWORD_WORKER_INTERVAL_SECONDS
DISPLAY_SNAPSHOT_INTERVAL_SECONDS
```

실제 API key와 secret은 코드에 넣지 않는다. `.env.example`에는 placeholder만 둔다.

## 10. Test 기준

백엔드 테스트는 최소한 다음을 포함한다.

```txt
- health check
- 세션 생성/복구
- 동의 저장 후 상태 전이
- 1~77번 응답 bulk 저장
- 점수화 upsert
- PHQ-9 item9 위험 플래그
- 자유입력 위기 표현 공개 제한
- 템플릿 요약 fallback
- 마음카드 저장 후 keyword job 생성
- fallback keyword extraction
- display snapshot 원문 미포함
- 완료 코드 중복 발급 방지
- 완료 코드 중복 지급 방지
- 관리자 검수 감사 로그
```

## 11. 금지 사항

```txt
- Router에서 직접 SQL을 작성하지 않는다.
- 사용자 요청으로 SQL 문자열을 생성하지 않는다.
- LLM 결과로 위험 플래그를 확정하지 않는다.
- LLM 결과로 공개 여부를 확정하지 않는다.
- TV API에서 content_raw 또는 content_redacted를 반환하지 않는다.
- 관리자 인증 없이 원문 조회 API를 만들지 않는다.
- Redis/Celery를 MVP 필수 구조로 추가하지 않는다.
- 실패한 keyword job 때문에 참가자 완료 처리를 막지 않는다.
```
