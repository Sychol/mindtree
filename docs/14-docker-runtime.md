# 14. Docker Runtime

## 1. 목적

이 문서는 마음나무 MVP의 Docker Compose 실행 구조, 환경변수, 개발 실행, migration, seed, health check 기준을 정의한다.

MVP 기본 런타임은 다음 3개 컨테이너다.

```txt
postgres
api
web
```

Redis, Celery, pgvector, Chroma는 MVP 기본 런타임에 포함하지 않는다. 키워드 비동기 처리는 PostgreSQL 기반 `keyword_jobs`로 시작한다.

## 2. 권장 레포 구조

```txt
maeumnamu/
  docker-compose.yml
  .env.example
  README.md

  api/
    Dockerfile
    requirements.txt 또는 pyproject.toml
    alembic.ini
    app/
    alembic/

  web/
    Dockerfile
    package.json
    vite.config.ts
    src/

  docs/
```

## 3. docker-compose 서비스

### 3.1 postgres

역할:

```txt
- PostgreSQL 데이터 저장소
- events, sessions, questions, answers, keywords 등 모든 MVP 데이터 저장
```

권장 설정:

```txt
image: postgres:16
port: 5432
volume: postgres_data
healthcheck: pg_isready
```

### 3.2 api

역할:

```txt
- FastAPI 서버
- REST API
- SSE stream
- PostgreSQL migration 실행 대상
- 개발 환경 keyword worker 실행 가능
```

권장 설정:

```txt
port: 8000
depends_on: postgres healthcheck
DATABASE_URL 주입
LLM 관련 환경변수 주입
```

### 3.3 web

역할:

```txt
- Vite React 개발 서버 또는 build 결과 serving
- 참가자, TV, 관리자 화면 제공
```

권장 설정:

```txt
port: 5173
VITE_API_BASE_URL 주입
```

## 4. docker-compose 예시 구조

실제 구현 시 Codex가 아래 구조를 기준으로 작성한다.

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: maeumnamu
      POSTGRES_USER: maeumnamu
      POSTGRES_PASSWORD: maeumnamu_dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U maeumnamu -d maeumnamu"]
      interval: 5s
      timeout: 5s
      retries: 10

  api:
    build: ./api
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  web:
    build: ./web
    env_file:
      - .env
    ports:
      - "5173:5173"
    depends_on:
      - api

volumes:
  postgres_data:
```

위 예시는 기준 구조다. 실제 값은 `.env`와 `.env.example`로 관리한다.

## 5. 환경변수

### 5.1 공통

```txt
APP_ENV=development
TZ=Asia/Seoul
```

### 5.2 Database

```txt
POSTGRES_DB=maeumnamu
POSTGRES_USER=maeumnamu
POSTGRES_PASSWORD=replace-me
DATABASE_URL=postgresql+asyncpg://maeumnamu:replace-me@postgres:5432/maeumnamu
```

SQLAlchemy sync driver를 쓰면 `postgresql://` 형식으로 맞춘다. async/sync 선택은 Phase 01~02에서 확정한다.

### 5.3 API

```txt
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=replace-me
CORS_ORIGINS=http://localhost:5173
ADMIN_JWT_EXPIRES_MINUTES=480
```

### 5.4 Frontend

```txt
VITE_API_BASE_URL=http://localhost:8000/api
```

### 5.5 LLM / Keyword Worker

```txt
LLM_ENABLED=false
LLM_PROVIDER=mock
LLM_API_KEY=replace-me
LLM_TIMEOUT_SECONDS=5
KEYWORD_WORKER_ENABLED=true
KEYWORD_WORKER_INTERVAL_SECONDS=3
KEYWORD_FALLBACK_ENABLED=true
```

실제 API key는 `.env.example`에 넣지 않는다.

## 6. .env.example 기준

`.env.example`에는 개발자가 복사해 사용할 placeholder만 둔다.

```txt
APP_ENV=development
TZ=Asia/Seoul

POSTGRES_DB=maeumnamu
POSTGRES_USER=maeumnamu
POSTGRES_PASSWORD=replace-me
DATABASE_URL=postgresql+asyncpg://maeumnamu:replace-me@postgres:5432/maeumnamu

SECRET_KEY=replace-me
CORS_ORIGINS=http://localhost:5173
ADMIN_JWT_EXPIRES_MINUTES=480

VITE_API_BASE_URL=http://localhost:8000/api

LLM_ENABLED=false
LLM_PROVIDER=mock
LLM_API_KEY=replace-me
LLM_TIMEOUT_SECONDS=5
KEYWORD_WORKER_ENABLED=true
KEYWORD_WORKER_INTERVAL_SECONDS=3
KEYWORD_FALLBACK_ENABLED=true
```

## 7. 개발 실행 명령

```bash
cp .env.example .env
docker compose up --build
```

API health check:

```bash
curl http://localhost:8000/health
```

Frontend:

```txt
http://localhost:5173
```

TV display 예시:

```txt
http://localhost:5173/display/fire-expo-2026
```

관리자 예시:

```txt
http://localhost:5173/admin/login
```

## 8. Migration 실행

Alembic을 사용하는 경우:

```bash
docker compose exec api alembic upgrade head
```

Migration 생성:

```bash
docker compose exec api alembic revision --autogenerate -m "create initial tables"
```

Codex는 migration 파일을 임의 삭제하지 않는다.

## 9. Seed 실행

초기 개발 seed는 다음을 포함한다.

```txt
- 기본 event
- 1~77번 questions
- 관리자 계정
- seed card
- 동의 문구 버전
```

명령 예시:

```bash
docker compose exec api python -m app.seeds.events
docker compose exec api python -m app.seeds.questions
docker compose exec api python -m app.seeds.admin
```

관리자 초기 비밀번호는 `.env`에서 읽거나 실행 시 출력 후 즉시 변경하는 방식으로 관리한다. 코드에 하드코딩하지 않는다.

## 10. Keyword Worker 실행

MVP에서는 두 가지 방식 중 하나를 사용한다.

### 10.1 API 내부 startup task

개발과 시연에 단순하다.

```txt
KEYWORD_WORKER_ENABLED=true
```

API 프로세스가 일정 주기로 `keyword_jobs`를 처리한다.

### 10.2 별도 worker 프로세스

운영 분리가 필요할 때 사용한다.

```bash
docker compose exec api python -m app.workers.keyword_worker
```

MVP Compose 기본 서비스에 별도 worker 컨테이너를 필수로 추가하지 않는다.

## 11. Health Check

API health endpoint:

```http
GET /health
```

응답 예시:

```json
{
  "status": "ok",
  "database": "ok",
  "version": "dev"
}
```

선택 endpoint:

```http
GET /health/db
GET /health/worker
```

## 12. 개발 Reset

주의: 개발 데이터 삭제 명령이다.

```bash
docker compose down -v
docker compose up --build
```

운영 데이터에는 사용하지 않는다.

## 13. 운영 시 추가 고려사항

MVP 이후 운영 배포에서는 다음을 추가한다.

```txt
- reverse proxy
- HTTPS
- 운영 DB backup
- log rotation
- secret manager
- 관리자 계정 정책
- 데이터 보존/파기 정책
- display token 또는 접근 제한
```

## 14. 구현 파일 기준

```txt
docker-compose.yml
.env.example
api/Dockerfile
web/Dockerfile
api/app/core/config.py
api/app/main.py
README.md
```

## 15. Docker 테스트 기준

```txt
- docker compose up --build 성공
- postgres healthcheck 통과
- api /health 성공
- web 접속 성공
- migration 실행 성공
- question seed 실행 성공
- 관리자 계정 seed 실행 성공
- LLM_ENABLED=false에서 참가자 완료 가능
- TV display route 접속 가능
- SSE 연결 가능
```

## 16. 금지 사항

```txt
- 실제 secret을 Dockerfile 또는 compose에 하드코딩하지 않는다.
- PostgreSQL 대신 SQLite/Firebase/MongoDB로 바꾸지 않는다.
- Redis/Celery를 MVP 필수로 추가하지 않는다.
- WebSocket 서버를 임의로 추가하지 않는다.
- migration 파일을 임의 삭제하지 않는다.
- 운영 데이터 reset 명령을 일반 실행 문서에 무심코 배치하지 않는다.
```
