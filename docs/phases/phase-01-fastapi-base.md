# PHASE 01. FastAPI 백엔드 기반 구성

이 문서는 VS Code Codex에 그대로 붙여넣어 실행할 수 있는 구현 지시서다.

## 목표

FastAPI 백엔드의 기본 앱 구조를 만든다.

이 Phase에서는 비즈니스 기능을 구현하지 않고, 이후 API 구현을 위한 공통 기반만 만든다.

완료 후에는 다음이 가능해야 한다.

```txt
- FastAPI 앱 실행
- /api/health 응답 확인
- 공통 settings 로딩
- 공통 error response 구조 확인
- router 구조 확인
- 기본 pytest 실행
```

## 작업 전 확인 사항

Codex는 먼저 아래를 수행한다.

```txt
1. 현재 코드베이스의 api/ 구조를 확인한다.
2. docs/codex-common-rules.md를 읽는다.
3. docs/03-system-architecture.md를 읽는다.
4. docs/05-api-spec.md의 공통 규칙을 읽는다.
5. docs/07-backend-structure.md를 읽는다.
6. Phase 00 산출물과 충돌하지 않는지 확인한다.
```

## 참조 문서

```txt
docs/codex-common-rules.md
docs/03-system-architecture.md
docs/05-api-spec.md
docs/07-backend-structure.md
docs/13-security-privacy-policy.md
```

## 수정 또는 생성할 파일

프로젝트 상태에 따라 아래 파일을 생성 또는 보완한다.

```txt
api/requirements.txt 또는 api/pyproject.toml
api/app/__init__.py
api/app/main.py
api/app/api/__init__.py
api/app/api/router.py
api/app/api/routes/__init__.py
api/app/api/routes/health.py
api/app/core/__init__.py
api/app/core/config.py
api/app/core/errors.py
api/app/core/logging.py
api/app/schemas/__init__.py
api/tests/__init__.py
api/tests/test_health.py
api/README.md
```

기존 패키지 매니저가 있으면 임의로 변경하지 않는다.

## 구현 내용

### 1. FastAPI 앱 엔트리포인트

`api/app/main.py`에 FastAPI 앱을 생성한다.

구현 기준:

```txt
- 앱 title은 Maeumnamu API 또는 마음나무 API로 설정한다.
- API prefix는 /api를 기준으로 한다.
- router는 app/api/router.py에서 include한다.
- CORS는 settings 기반으로 설정한다.
- 예외 핸들러는 공통 error object 형식을 사용한다.
```

### 2. Settings 구성

`api/app/core/config.py`에 환경변수 기반 설정을 만든다.

필수 설정 예시:

```txt
APP_ENV
API_HOST
API_PORT
DATABASE_URL
JWT_SECRET_KEY
JWT_ALGORITHM
LLM_ENABLED
LLM_PROVIDER
LLM_API_KEY
LLM_TIMEOUT_SECONDS
KEYWORD_WORKER_ENABLED
DISPLAY_SSE_HEARTBEAT_SECONDS
CORS_ORIGINS
```

주의:

```txt
- 실제 secret 기본값을 넣지 않는다.
- local 개발용 placeholder만 허용한다.
- 운영에서 필요한 값은 환경변수로 주입되도록 한다.
```

### 3. Health Check API

아래 API를 구현한다.

```http
GET /api/health
```

응답 예시:

```json
{
  "status": "ok",
  "service": "maeumnamu-api",
  "environment": "local"
}
```

이 API는 DB 연결 없이도 동작할 수 있어야 한다. DB health는 Phase 02 이후 별도 확장 가능하다.

### 4. 공통 에러 응답

`docs/05-api-spec.md`의 공통 에러 형식을 따른다.

```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "요청이 올바르지 않습니다.",
    "details": {}
  }
}
```

구현 기준:

```txt
- AppError 또는 유사한 커스텀 예외 클래스를 둔다.
- code, message, status_code, details를 명시한다.
- FastAPI exception handler에서 공통 JSON 형식으로 반환한다.
```

### 5. Router 구조

`api/app/api/router.py`에서 모든 라우트를 모은다.

Phase 01에서는 health router만 include한다.

이후 Phase에서 추가될 router는 아래 구조를 예상한다.

```txt
events.py
sessions.py
questions.py
summaries.py
cards.py
replies.py
display.py
admin_auth.py
admin_events.py
admin_rewards.py
```

단, 이 Phase에서 위 라우터들을 미리 구현하지 않는다.

### 6. 기본 테스트

`api/tests/test_health.py`를 작성한다.

테스트 기준:

```txt
- TestClient로 /api/health 호출
- status_code == 200
- response.status == ok
```

## 금지 사항

```txt
- DB 모델, Alembic, 마이그레이션을 구현하지 않는다.
- 이벤트, 세션, 문항, 카드, 관리자 API를 구현하지 않는다.
- LLM provider를 구현하지 않는다.
- Redis/Celery를 추가하지 않는다.
- FastAPI 외 프레임워크로 변경하지 않는다.
- 실제 API key 또는 secret을 코드에 넣지 않는다.
```

## 완료 기준

```txt
- FastAPI 앱이 실행된다.
- GET /api/health가 정상 응답한다.
- settings가 환경변수 기반으로 동작한다.
- 공통 error response 구조가 존재한다.
- pytest 기본 테스트가 통과한다.
```

## 테스트 방법

```bash
cd api
pytest

# 로컬 실행 예시
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 확인
curl http://localhost:8000/api/health
```

Docker 기반 확인:

```bash
docker compose up --build api
curl http://localhost:8000/api/health
```

## 작업 후 보고 형식

```md
## 작업 요약
- FastAPI 앱 기반, settings, health API, 공통 error response를 구현했다.

## 변경 파일
- api/app/main.py: FastAPI 앱 생성
- api/app/core/config.py: 환경변수 settings 구성
- ...

## 실행 방법
- cd api && pytest
- uvicorn app.main:app --reload

## 테스트 결과
- ...

## 남은 작업 / TODO
- DB 연결과 모델은 Phase 02에서 구현 필요
- 실제 업무 API는 Phase 03 이후 구현 필요

## 주의 사항
- 실제 secret은 코드에 포함하지 않았음
```
