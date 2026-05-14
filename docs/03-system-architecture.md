# 03. System Architecture

## 1. 전체 구조

마음나무 MVP는 React/Vite/TypeScript 프론트엔드, FastAPI 백엔드, PostgreSQL 데이터베이스, Docker Compose 실행 구조로 구성한다.

```txt
[Participant Mobile Web]
  React + Vite + TypeScript
  - QR 접속
  - 문항 선로딩
  - 로컬 진행 상태
  - 제출 재시도
  - 마음카드/응원 작성
  - 완료 코드 확인

        |
        | REST API
        v

[FastAPI Backend]
  - 이벤트 설정
  - 익명 세션
  - 동의 기록
  - 문항 제공
  - 응답 저장
  - 점수화
  - 위험 플래그
  - 마음신호 요약
  - 안전 필터
  - keyword job 생성
  - LLM/fallback 키워드 처리
  - 완료 코드 발급
  - 관리자 API
  - SSE stream

        |
        v

[PostgreSQL]
  - events
  - sessions
  - consent_logs
  - questions
  - answers
  - scale_scores
  - risk_flags
  - summaries
  - mind_cards
  - replies
  - keyword_jobs
  - keywords
  - completion_codes
  - admin_users
  - admin_audit_logs

        ^
        |
        | SSE
        |

[TV Display]
  React route: /display/:eventSlug
  - EventSource 연결
  - 자동 재연결
  - 마지막 데이터 유지
  - 워드클라우드 표시

[Admin Web]
  React routes: /admin/*
  - 검수
  - 키워드 상태
  - 완료 코드
  - 상품 지급
  - 감사 로그
```

## 2. 컴포넌트별 책임

## 2.1 Frontend Web

프론트엔드는 하나의 React 앱 안에서 참가자, TV, 관리자 라우트를 분리한다.

```txt
web/
  src/
    app/
    routes/
      participant/
      display/
      admin/
    components/
    hooks/
    api/
    types/
    utils/
```

### 참가자 라우트

```txt
/e/:eventSlug
/e/:eventSlug/consent
/e/:eventSlug/questions
/e/:eventSlug/summary
/e/:eventSlug/cards/new
/e/:eventSlug/cards/select
/e/:eventSlug/replies/new
/e/:eventSlug/complete
/e/:eventSlug/help
```

참가자 라우트의 핵심 책임은 다음이다.

```txt
- 이벤트 설정 조회
- 익명 세션 생성 또는 복구
- 문항 1~77번 선로딩
- 진행 상태 로컬 유지
- 제출 실패 시 재시도
- 완료 후 로컬 임시 데이터 정리
```

### TV 라우트

```txt
/display/:eventSlug
```

TV 라우트의 핵심 책임은 다음이다.

```txt
- 초기 snapshot 조회
- SSE EventSource 연결
- 최신 키워드 집계 반영
- 연결 끊김 시 자동 재연결
- 마지막 정상 데이터 유지
- 장시간 연결 실패 시 작은 상태 표시
```

### 관리자 라우트

```txt
/admin/login
/admin/events/:eventSlug/dashboard
/admin/events/:eventSlug/cards
/admin/events/:eventSlug/replies
/admin/events/:eventSlug/keywords
/admin/events/:eventSlug/jobs
/admin/events/:eventSlug/rewards
/admin/events/:eventSlug/audit-logs
```

관리자 라우트의 핵심 책임은 다음이다.

```txt
- 관리자 인증 토큰 관리
- 검수 목록 조회
- 공개/숨김/수정/삭제 처리
- 키워드 상태 관리
- keyword job 상태 확인
- 완료 코드 조회 및 지급 처리
```

## 2.2 FastAPI Backend

백엔드는 모든 중요한 판단과 상태 전이를 담당한다.

```txt
api/
  app/
    main.py
    core/
      config.py
      security.py
      database.py
      enums.py
    models/
    schemas/
    routers/
      public_events.py
      sessions.py
      questions.py
      answers.py
      summaries.py
      cards.py
      replies.py
      display.py
      admin_auth.py
      admin_events.py
      admin_review.py
      admin_keywords.py
      admin_rewards.py
    services/
      session_service.py
      consent_service.py
      scoring_service.py
      risk_service.py
      summary_service.py
      safety_filter_service.py
      keyword_service.py
      keyword_job_service.py
      display_service.py
      completion_service.py
      reward_service.py
      audit_service.py
    repositories/
    workers/
      keyword_worker.py
    tests/
```

백엔드의 핵심 원칙은 다음이다.

```txt
- LLM이 세션 상태를 결정하지 않는다.
- LLM이 위험도를 판단하지 않는다.
- LLM이 공개 여부를 결정하지 않는다.
- LLM 지연이 사용자 흐름을 막지 않는다.
- 사용자 요청에서 직접 SQL을 생성하지 않는다.
- 모든 DB 조회는 repository 또는 query function으로 제한한다.
```

## 2.3 PostgreSQL

PostgreSQL은 MVP의 단일 데이터 저장소다.

저장 대상은 다음이다.

```txt
- 이벤트 설정
- 익명 세션
- 동의 기록
- 문항 설정
- 응답값
- 척도 점수
- 위험 플래그
- 마음신호 요약
- 마음카드 원문 및 검수 상태
- 응원 문장 원문 및 검수 상태
- keyword job 상태
- 정제 키워드
- 완료 코드
- 상품 지급 상태
- 관리자 감사 로그
```

MVP에서는 Redis, Celery, Chroma, pgvector를 도입하지 않는다. 비동기 LLM 처리는 PostgreSQL의 `keyword_jobs` 테이블과 백엔드 worker loop 또는 API 프로세스 내부 background task로 시작한다.

## 2.4 LLM 처리 모듈

LLM은 선택적 보조 모듈이다.

```txt
입력:
- 마음카드 문장
- 응원 문장
- 점수화 결과를 바탕으로 한 요약 후보 문장

출력:
- 키워드 후보
- 요약 문장 보정안

금지:
- 진단
- 위험도 판단
- 공개 여부 판단
- 세션 상태 변경
- 관리자 승인 대체
```

LLM provider는 환경변수로 제어한다.

```txt
LLM_PROVIDER=none|mock|openai|local
LLM_ENABLED=true|false
LLM_TIMEOUT_SECONDS=8
LLM_MAX_RETRIES=2
```

`LLM_ENABLED=false` 또는 provider 실패 시 fallback 키워드 추출을 사용한다.

## 3. 주요 데이터 흐름

## 3.1 이벤트 진입 및 세션 생성

```txt
Frontend
→ GET /api/events/{eventSlug}/public
→ POST /api/events/{eventSlug}/sessions
→ localStorage/sessionStorage에 sessionId와 resumeToken 저장
```

DB 저장:

```txt
sessions.status = created
sessions.anonymous_key_hash = hash(resumeToken)
```

## 3.2 동의

```txt
Frontend
→ POST /api/sessions/{sessionId}/consent
→ Backend stores consent_logs
→ sessions.status = consented
```

## 3.3 문항 선로딩

```txt
Frontend
→ GET /api/events/{eventSlug}/questions
→ questions 전체 수신
→ 프론트 로컬 상태에 캐시
```

## 3.4 응답 제출 및 점수화

```txt
Frontend
→ PUT /api/sessions/{sessionId}/answers/bulk
→ Backend upsert answers
→ scoring_service.calculate_scores()
→ risk_service.calculate_flags()
→ sessions.status = questions_completed
```

## 3.5 마음신호 요약

```txt
Backend
→ summary_service.create_template_summary()
→ optional LLM polish job
→ summaries 저장

Frontend
→ GET /api/sessions/{sessionId}/summary
→ 템플릿 또는 final summary 표시
→ POST /api/sessions/{sessionId}/summary/viewed
```

## 3.6 마음카드와 keyword job

```txt
Frontend
→ POST /api/sessions/{sessionId}/cards

Backend
→ mind_cards 저장
→ safety_filter_service.evaluate()
→ public_status 결정
→ keyword_jobs 생성
→ sessions.status = card_created
```

사용자는 키워드 추출을 기다리지 않고 다음 단계로 이동한다.

## 3.7 응원 문장과 keyword job

```txt
Frontend
→ GET /api/events/{eventSlug}/cards/public
→ POST /api/sessions/{sessionId}/selected-card
→ POST /api/sessions/{sessionId}/replies

Backend
→ replies 저장
→ safety_filter_service.evaluate()
→ keyword_jobs 생성
→ completion code 발급 가능 여부 확인
```

## 3.8 키워드 추출

```txt
keyword_worker
→ pending job 조회
→ processing 변경
→ LLM keyword extraction 시도
→ 실패 시 fallback keyword extraction
→ keywords 저장
→ job status = succeeded 또는 failed
```

## 3.9 TV 표시

```txt
TV Frontend
→ GET /api/events/{eventSlug}/display/snapshot
→ GET /api/events/{eventSlug}/stream

Backend SSE
→ keyword aggregate payload 전송
```

SSE payload 예시:

```json
{
  "type": "keyword_snapshot",
  "eventSlug": "fire-expo-2026",
  "participantCount": 124,
  "topMindKeywords": [
    { "text": "긴장", "weight": 16 },
    { "text": "피로", "weight": 12 }
  ],
  "topSupportKeywords": [
    { "text": "쉼", "weight": 18 },
    { "text": "괜찮아", "weight": 11 }
  ],
  "cloudKeywords": [
    { "text": "쉼", "weight": 18, "category": "support" }
  ],
  "generatedAt": "2026-05-13T09:00:00Z"
}
```

## 4. Docker Compose 구조

MVP의 기본 컨테이너는 다음 세 개다.

```txt
postgres
api
web
```

예상 구조:

```txt
.
  docker-compose.yml
  .env.example
  api/
  web/
  docs/
```

기본 포트:

```txt
web: http://localhost:5173
api: http://localhost:8000
postgres: localhost:5432
```

환경변수 예시:

```txt
POSTGRES_DB=maeumnamu
POSTGRES_USER=maeumnamu
POSTGRES_PASSWORD=maeumnamu_dev
DATABASE_URL=postgresql+psycopg://maeumnamu:maeumnamu_dev@postgres:5432/maeumnamu
API_CORS_ORIGINS=http://localhost:5173
JWT_SECRET=replace_me_in_real_env
SESSION_HASH_SECRET=replace_me_in_real_env
LLM_ENABLED=false
LLM_PROVIDER=none
```

실제 API key와 운영 secret은 코드나 문서에 넣지 않는다.

## 5. 장애 대응 기준

```txt
API 일시 실패:
- 참가자 입력 유지
- 재시도 버튼 제공

LLM 실패:
- fallback 키워드 사용
- job 상태에 fallback_used 저장

SSE 연결 실패:
- TV 마지막 데이터 유지
- 자동 재연결
- 필요 시 snapshot polling fallback

DB 연결 실패:
- health check 실패
- 관리자 화면에 오류 표시
- 참가자에게 일시적 장애 안내
```
