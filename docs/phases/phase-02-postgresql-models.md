# PHASE 02. PostgreSQL 핵심 모델과 마이그레이션

이 문서는 VS Code Codex에 그대로 붙여넣어 실행할 수 있는 구현 지시서다.

## 목표

마음나무 MVP의 PostgreSQL 데이터 모델을 구현한다.

이 Phase에서는 API 기능 구현보다 DB 연결, 모델, enum, 마이그레이션, 기본 repository 기반을 만드는 데 집중한다.

완료 후에는 다음이 가능해야 한다.

```txt
- FastAPI에서 PostgreSQL 연결 설정 확인
- Alembic 마이그레이션 생성 및 적용
- 핵심 테이블 생성
- DB 세션 dependency 준비
- 모델 import 및 기본 테스트 가능
```

## 작업 전 확인 사항

Codex는 먼저 아래를 수행한다.

```txt
1. 현재 api/ 구조와 Phase 01 구현 결과를 확인한다.
2. docs/codex-common-rules.md를 읽는다.
3. docs/04-data-model.md 전체를 읽는다.
4. docs/07-backend-structure.md를 읽는다.
5. docs/13-security-privacy-policy.md의 데이터 저장 원칙을 확인한다.
6. 기존 DB 라이브러리, 패키지 매니저, 마이그레이션 구조가 있는지 확인한다.
```

## 참조 문서

```txt
docs/codex-common-rules.md
docs/04-data-model.md
docs/07-backend-structure.md
docs/08-session-state.md
docs/09-scoring-risk-policy.md
docs/10-llm-keyword-policy.md
docs/13-security-privacy-policy.md
```

## 수정 또는 생성할 파일

상황에 따라 아래 파일을 생성 또는 보완한다.

```txt
api/alembic.ini
api/alembic/env.py
api/alembic/versions/*.py
api/app/db/__init__.py
api/app/db/base.py
api/app/db/session.py
api/app/models/__init__.py
api/app/models/enums.py
api/app/models/event.py
api/app/models/session.py
api/app/models/consent.py
api/app/models/question.py
api/app/models/answer.py
api/app/models/score.py
api/app/models/summary.py
api/app/models/card.py
api/app/models/reply.py
api/app/models/keyword.py
api/app/models/completion.py
api/app/models/admin.py
api/app/repositories/__init__.py
api/app/repositories/base.py
api/tests/test_models_import.py
```

기존 ORM 구조가 있다면 삭제하지 말고 같은 구조 안에서 보완한다.

## 구현 내용

### 1. DB 라이브러리 선택

기본 권장 구조는 다음이다.

```txt
- SQLAlchemy 2.x
- Alembic
- psycopg 또는 asyncpg 중 현재 코드베이스와 맞는 드라이버
- Pydantic은 API schema 용도로 사용
```

기존 코드가 sync SQLAlchemy를 쓰고 있으면 sync로 유지한다. 기존 코드가 async SQLAlchemy를 쓰고 있으면 async로 유지한다. 이 Phase에서 임의로 대규모 변경하지 않는다.

### 2. Enum 정의

`docs/04-data-model.md`의 enum 값을 모델에 반영한다.

필수 enum:

```txt
event_status: draft, open, closed, archived
session_status: created, consented, questions_completed, summary_viewed, card_created, reply_created, completed, abandoned
question_type: single_select, multi_select, likert, text, number
scale_code: profile, phq9, pcl5, kmies, kscs
safety_status: safe, review, exclude
public_status: pending, public, hidden, excluded
reply_type: comfort, empathy, small_coping
keyword_job_status: pending, processing, succeeded, failed, retry_wait
keyword_source_type: mind_card, reply, summary
keyword_category: mind_signal, support, recovery, coping, neutral
keyword_status: active, hidden, excluded
keyword_extraction_method: llm, fallback, admin
completion_code_status: issued, redeemed, void
```

문자열 enum으로 구현해도 된다. 단, 값은 문서와 일치해야 한다.

### 3. 핵심 테이블 모델 구현

아래 테이블을 우선 구현한다.

```txt
events
sessions
consent_logs
questions
answers
scale_scores
risk_flags
summaries
mind_cards
card_selections
replies
keywords
keyword_jobs
completion_codes
admin_users
admin_audit_logs
```

구현 시 주의 사항:

```txt
- UUID primary key를 사용한다.
- created_at, updated_at을 둔다.
- sessions에는 원문 resume token을 저장하지 않는다.
- sessions에는 resume_token_hash 또는 anonymous_key_hash만 저장한다.
- 사용자 입력 원문은 mind_cards/replies에 저장하되 TV API로 직접 반환하지 않는다.
- 위험 플래그와 공개 상태는 서버 로직에서 갱신할 수 있도록 필드를 둔다.
- keyword_jobs는 PostgreSQL 기반 비동기 작업 상태 관리를 위해 포함한다.
- completion_codes는 세션당 1개 발급을 보장해야 한다.
- admin_audit_logs는 검수, 수정, 지급 처리 등 관리자 행위를 남긴다.
```

### 4. 인덱스와 제약 조건

필수 제약 조건 예시:

```txt
- events.slug unique
- sessions(event_id, anonymous_key_hash) unique
- questions(event_id, question_no) unique
- questions(event_id, question_key) unique
- answers(session_id, question_id) unique
- scale_scores(session_id, scale_code) unique
- completion_codes(session_id) unique
- completion_codes(code) unique
```

필수 인덱스 예시:

```txt
- sessions(event_id, status)
- mind_cards(event_id, public_status, safety_status)
- replies(event_id, public_status, safety_status)
- keywords(event_id, status, category)
- keyword_jobs(status, next_run_at)
- completion_codes(event_id, code)
- admin_audit_logs(event_id, created_at)
```

### 5. DB 세션 dependency

`api/app/db/session.py`에 DB session 생성 및 dependency를 둔다.

예상 형태:

```txt
- engine 생성
- SessionLocal 생성
- get_db dependency
```

FastAPI 라우터에서 사용할 수 있도록 준비하되, 업무 API는 Phase 03 이후 구현한다.

### 6. Alembic 마이그레이션

초기 마이그레이션을 만든다.

구현 기준:

```txt
- 모델 metadata가 Alembic env.py에 연결되어야 한다.
- alembic upgrade head로 테이블이 생성되어야 한다.
- 마이그레이션 파일명은 의미 있게 작성한다.
```

### 7. 기본 테스트

가능한 범위에서 다음 테스트를 작성한다.

```txt
- 모델 import 테스트
- enum 값 테스트
- metadata에 핵심 테이블이 포함되는지 테스트
```

DB integration test는 현재 환경이 준비되어 있으면 작성한다. 준비가 어렵다면 TODO와 이유를 남긴다.

## 금지 사항

```txt
- API endpoint를 대량 구현하지 않는다.
- 프론트엔드 화면을 구현하지 않는다.
- DB 테이블을 docs/04-data-model.md와 다르게 임의 설계하지 않는다.
- 원문 resume token 또는 raw session key를 DB에 저장하지 않는다.
- 사용자 입력에서 직접 SQL을 생성하는 구조를 만들지 않는다.
- Redis/Celery/pgvector를 추가하지 않는다.
- RAG 관련 테이블을 MVP에 추가하지 않는다.
```

## 완료 기준

```txt
- Alembic이 설정되어 있다.
- 핵심 모델과 enum이 구현되어 있다.
- alembic upgrade head로 핵심 테이블이 생성된다.
- DB session dependency가 준비되어 있다.
- 모델 import 테스트가 통과한다.
```

## 테스트 방법

```bash
cd api
alembic upgrade head
pytest
```

Docker 기반 확인:

```bash
docker compose up -d postgres
cd api
alembic upgrade head
pytest
```

필요 시 DB 확인:

```bash
docker compose exec postgres psql -U maeumnamu -d maeumnamu -c '\dt'
```

## 작업 후 보고 형식

```md
## 작업 요약
- PostgreSQL 연결, SQLAlchemy 모델, Alembic 초기 마이그레이션을 구현했다.

## 변경 파일
- api/app/models/event.py: events 모델 추가
- api/app/models/session.py: sessions 모델 추가
- ...

## 실행 방법
- docker compose up -d postgres
- cd api && alembic upgrade head
- cd api && pytest

## 테스트 결과
- ...

## 남은 작업 / TODO
- seed data는 Phase 04에서 구현 필요
- 이벤트/세션 API는 Phase 03에서 구현 필요

## 주의 사항
- 원문 resume token은 저장하지 않고 hash 필드만 사용하도록 모델링함
```
