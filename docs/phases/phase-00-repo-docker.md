# PHASE 00. 레포와 Docker 기반 구성

이 문서는 VS Code Codex에 그대로 붙여넣어 실행할 수 있는 구현 지시서다.

## 목표

마음나무 MVP의 기본 레포 구조와 Docker Compose 실행 기반을 만든다.

이 Phase의 목표는 기능 구현이 아니라, 이후 Phase들이 같은 구조 위에서 작업할 수 있는 최소 개발 환경을 만드는 것이다.

완료 후에는 다음이 가능해야 한다.

```txt
- api, web, docs 폴더 구조 확인
- postgres, api, web 컨테이너 구동 기반 확인
- .env.example 기준으로 개발 환경변수 확인
- 추후 FastAPI와 React/Vite 구현을 얹을 수 있는 기본 구조 확보
```

## 작업 전 확인 사항

Codex는 먼저 아래를 수행한다.

```txt
1. 현재 코드베이스의 최상위 파일과 폴더 구조를 확인한다.
2. docs/codex-common-rules.md를 읽는다.
3. docs/01-mvp-scope.md를 읽는다.
4. docs/03-system-architecture.md를 읽는다.
5. docs/14-docker-runtime.md를 읽는다.
6. 이미 api, web, docker-compose.yml, .env.example이 있는지 확인한다.
```

기존 파일이 있으면 임의로 삭제하지 말고 필요한 부분만 보완한다.

## 참조 문서

```txt
docs/codex-common-rules.md
docs/01-mvp-scope.md
docs/03-system-architecture.md
docs/14-docker-runtime.md
```

## 수정 또는 생성할 파일

상황에 따라 아래 파일을 생성 또는 보완한다.

```txt
README.md
.gitignore
.env.example
docker-compose.yml
api/
api/Dockerfile
api/README.md
web/
web/Dockerfile
web/README.md
docs/phases/README.md
```

이미 존재하는 파일은 기존 내용을 보존하고 누락된 설정만 추가한다.

## 구현 내용

### 1. 최상위 레포 구조 정리

기본 구조는 아래를 기준으로 한다.

```txt
maeumnamu/
  api/
  web/
  docs/
  docker-compose.yml
  .env.example
  .gitignore
  README.md
```

`api/`는 FastAPI 백엔드, `web/`은 React/Vite/TypeScript 프론트엔드, `docs/`는 설계 및 Codex 작업 문서 위치다.

### 2. `.env.example` 작성

운영 secret을 넣지 말고 placeholder만 둔다.

필수 항목 예시는 다음이다.

```env
APP_ENV=local
API_HOST=0.0.0.0
API_PORT=8000
WEB_PORT=5173

POSTGRES_DB=maeumnamu
POSTGRES_USER=maeumnamu
POSTGRES_PASSWORD=maeumnamu_dev_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://maeumnamu:maeumnamu_dev_password@postgres:5432/maeumnamu

JWT_SECRET_KEY=change-me-in-local-only
JWT_ALGORITHM=HS256

LLM_ENABLED=false
LLM_PROVIDER=disabled
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=8

KEYWORD_WORKER_ENABLED=true
DISPLAY_SSE_HEARTBEAT_SECONDS=15
```

주의:

```txt
- 실제 API key를 넣지 않는다.
- 운영용 DB password를 넣지 않는다.
- .env 파일은 gitignore 대상이어야 한다.
```

### 3. Docker Compose 기본 구성

`docker-compose.yml`은 MVP 개발 기준으로 다음 서비스를 포함한다.

```txt
postgres
api
web
```

구현 기준:

```txt
- postgres는 PostgreSQL 16 계열 이미지를 사용한다.
- api는 ./api를 build context로 사용한다.
- web은 ./web을 build context로 사용한다.
- api는 postgres에 의존한다.
- web은 api URL 환경변수를 받을 수 있어야 한다.
- postgres data volume을 둔다.
- 개발 포트는 기본적으로 8000, 5173, 5432를 사용한다.
```

Phase 00에서는 API와 Web의 실제 기능을 깊게 구현하지 않는다. 컨테이너 기반 실행 구조를 만드는 데 집중한다.

### 4. Dockerfile 기본값

`api/Dockerfile`과 `web/Dockerfile`이 없으면 개발용 기본 파일을 만든다.

단, FastAPI 앱 본체와 React 앱 본체는 이후 Phase에서 구현한다. 이 Phase에서는 다음 정도의 구조만 허용한다.

```txt
api:
- Python 런타임 기반
- requirements 또는 pyproject를 설치할 수 있는 구조
- 이후 uvicorn 실행이 가능하도록 준비

web:
- Node 런타임 기반
- package.json 기반 npm install 가능 구조
- 이후 Vite dev server 실행이 가능하도록 준비
```

현재 코드베이스가 이미 다른 패키지 매니저를 쓰고 있으면 임의로 바꾸지 않는다.

### 5. 최상위 README 보완

최상위 `README.md`에는 최소한 아래를 적는다.

```txt
- 프로젝트 한 줄 설명
- 기술 스택
- 폴더 구조
- 로컬 실행 준비
- docker compose 실행 명령
- Phase 기반 구현 방식
```

예시 실행 명령:

```bash
cp .env.example .env
docker compose up --build
```

### 6. `.gitignore` 보완

아래 항목을 포함한다.

```txt
.env
.env.*
!.env.example
__pycache__/
.pytest_cache/
.mypy_cache/
.venv/
node_modules/
dist/
build/
.coverage
.DS_Store
```

## 금지 사항

```txt
- FastAPI의 실제 업무 API를 구현하지 않는다.
- PostgreSQL 모델과 마이그레이션을 구현하지 않는다.
- React 참가자/TV/관리자 화면을 구현하지 않는다.
- Redis, Celery, pgvector, Chroma를 추가하지 않는다.
- 실제 API Key, 운영 Secret을 코드에 넣지 않는다.
- 기존 파일을 임의로 삭제하지 않는다.
```

## 완료 기준

```txt
- api/, web/, docs/ 구조가 존재한다.
- docker-compose.yml에 postgres, api, web 서비스가 정의되어 있다.
- .env.example이 존재하고 운영 secret이 포함되어 있지 않다.
- README.md에 기본 실행 방법이 적혀 있다.
- .gitignore에 민감 파일과 빌드 산출물이 제외되어 있다.
```

## 테스트 방법

가능한 범위에서 아래를 확인한다.

```bash
cp .env.example .env
docker compose config
docker compose up --build
```

아직 API/Web 본체가 없는 경우 컨테이너가 완전히 실행되지 않을 수 있다. 그 경우 Phase 01 이후 실행 가능해질 항목을 TODO로 명확히 남긴다.

## 작업 후 보고 형식

```md
## 작업 요약
- 레포 기본 구조와 Docker Compose 기반을 구성했다.

## 변경 파일
- docker-compose.yml: postgres/api/web 서비스 정의
- .env.example: 개발 환경변수 placeholder 추가
- ...

## 실행 방법
- cp .env.example .env
- docker compose config
- docker compose up --build

## 테스트 결과
- ...

## 남은 작업 / TODO
- FastAPI 앱 본체는 Phase 01에서 구현 필요
- PostgreSQL 모델과 마이그레이션은 Phase 02에서 구현 필요

## 주의 사항
- 실제 secret은 포함하지 않았음
```
