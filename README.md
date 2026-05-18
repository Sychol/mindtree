# 마음나무

마음나무는 소방안전박람회 부스 방문자가 QR로 접속해 마음상태를 짧게 점검하고, 마음카드와 응원 문장을 남기면, 정제된 익명 키워드가 TV 화면의 나무 잎 워드클라우드로 표시되는 이벤트형 리본톡 체험 서비스다.

## 기술 스택

- Frontend: React, Vite, TypeScript
- Backend: Python, FastAPI
- Database: PostgreSQL
- Runtime: Docker, Docker Compose
- Realtime Display: SSE

## 폴더 구조

```txt
maeumnamu/
  api/
    Dockerfile
    README.md
  web/
    Dockerfile
    README.md
  docs/
  docker-compose.yml
  .env.example
  .gitignore
  README.md
```

`docs/`는 MVP 설계 문서 위치이고, `docs/phases/`는 Phase별 구현 지시와 완료 기준을 관리한다. 각 Phase 작업 전에는 `docs/codex-common-rules.md`와 해당 Phase 문서를 먼저 확인한다.

## 로컬 실행 준비

개발 환경변수는 예시 파일을 복사해서 사용한다. 실제 API key, 운영 secret, 운영 DB password는 저장소에 넣지 않는다.

```bash
cp .env.example .env
docker compose config
docker compose up --build
```

PowerShell에서는 필요하면 다음처럼 복사할 수 있다.

```powershell
Copy-Item .env.example .env
```

PostgreSQL만 먼저 확인하려면 다음 명령을 사용한다.

```bash
docker compose up -d postgres
docker compose ps
docker compose down
```

## Phase 진행 방식

Phase 00에서는 Docker 기반과 폴더 구조를 준비한다. FastAPI 앱 본체는 Phase 01에서 구현하고, PostgreSQL 모델과 migration은 Phase 02에서 구현한다. React 참가자 화면은 Phase 05부터 구현한다.

이후 주요 순서는 다음과 같다.

- Phase 01: FastAPI 앱 본체, settings, health check
- Phase 02: PostgreSQL 모델과 Alembic migration
- Phase 03: 이벤트, 세션, 동의
- Phase 04: 문항, 응답, 점수화
- Phase 05: React/Vite 참가자 모바일 플로우
- Phase 09: TV display와 SSE
- Phase 10: 관리자 화면과 지급 처리

## Phase 00 이후 남은 작업

`api/Dockerfile`과 `web/Dockerfile`은 후속 구현을 얹기 위한 개발용 기반이다. 현재는 FastAPI 엔트리포인트와 React/Vite 앱 본체를 만들지 않았으므로 API/Web의 실제 HTTP 기능은 제공하지 않는다.

TODO:

- Phase 01에서 `api/app/main.py`, 설정, `/health`를 구현한다.
- Phase 02에서 PostgreSQL 모델과 Alembic migration을 구현한다.
- Phase 05에서 `web/package.json`, Vite 설정, 참가자 화면을 구현한다.
- Phase 09에서 TV display와 SSE 연결을 구현한다.
- Phase 10에서 관리자 화면을 구현한다.

## Phase 11 현장 리허설 실행 절차

이 절차는 local/dev 리허설 기준이다. 실제 운영 secret, API key, DB password, 관리자 실제 비밀번호는 코드나 문서에 넣지 말고 배포 환경에서 별도로 주입한다.

### 사전 요구사항

- Docker Desktop과 Docker Compose
- Python 3.12 이상
- Node.js와 npm
- `.env`는 `.env.example`을 복사한 뒤 local/dev 값만 채운다.

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

### Docker Compose 실행

```bash
docker compose config
docker compose build
docker compose up -d postgres api web
docker compose ps
```

`docker compose config` 출력에는 `.env` 값이 포함될 수 있으므로 외부에 공유하지 않는다. DB volume 삭제가 필요한 명령, 특히 `docker compose down -v`는 운영 데이터가 있을 때 실행하지 않는다.

### Migration과 seed

로컬 Docker Compose의 API 컨테이너는 시작할 때 기본적으로 migration과 개발 seed를 자동 실행한다.

```txt
AUTO_MIGRATE=true
AUTO_SEED_DEV=missing
```

`seed_dev`는 `fire-expo-2026` 이벤트, 최종 문항 seed, 관리자 계정, 공개 seed 카드를 준비한다. `AUTO_SEED_DEV=missing`이면 이벤트/문항 seed가 없거나 부족할 때만 자동 실행한다. 강제로 다시 upsert하려면 `AUTO_SEED_DEV=true`, 자동 실행을 끄려면 `false`로 둔다.

수동으로 다시 실행해야 할 때:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed_dev
```

문항 seed만 다시 확인해야 할 때:

```bash
docker compose exec api python -m app.scripts.seed_questions --event-slug fire-expo-2026
```

관리자 계정 bootstrap은 `.env`의 `ADMIN_BOOTSTRAP_EMAIL`과 `ADMIN_BOOTSTRAP_PASSWORD`가 비어 있지 않을 때만 생성된다.

```bash
docker compose exec api python -m app.scripts.bootstrap_admin
```

### Keyword worker와 smoke test

```bash
docker compose exec api python -m app.scripts.run_keyword_worker --once
docker compose exec api python -m app.scripts.run_smoke_tests
```

LLM 없이 운영 가능성을 먼저 확인하려면 `.env`를 다음처럼 둔다.

```txt
LLM_ENABLED=false
LLM_PROVIDER=disabled
KEYWORD_FALLBACK_ENABLED=true
```

mock 리허설은 실제 외부 API key 없이 다음처럼 확인한다.

```txt
LLM_ENABLED=true
LLM_PROVIDER=mock
KEYWORD_FALLBACK_ENABLED=true
```

### 접속 URL

- Participant: `http://localhost:5173/e/fire-expo-2026`
- TV Display: `http://localhost:5173/display/fire-expo-2026`
- Admin: `http://localhost:5173/admin/login`
- API Health: `http://localhost:8000/api/health`

### 테스트

Backend:

```bash
cd api
python -m pytest
```

Phase 11 focused:

```bash
cd api
python -m pytest tests/test_field_flow.py tests/test_privacy_display_contract.py tests/test_completion_redeem_idempotency.py tests/test_llm_modes.py tests/test_sse_reconnect_contract.py
```

Frontend:

```bash
cd web
npm install
npm run build
```

### 수동 리허설 체크리스트

1. 모바일에서 `Participant` URL로 참가자 플로우 1회를 완료한다.
2. 완료 코드가 표시되는지 확인한다.
3. `TV Display`에서 키워드가 표시되는지 확인한다.
4. API 서버 재시작 또는 일시 차단 후 TV가 마지막 snapshot을 유지하고 재연결되는지 확인한다.
5. 관리자 화면에서 완료 코드를 조회하고 지급 처리한다.
6. 같은 완료 코드를 다시 지급하려고 할 때 중복 지급 에러가 나는지 확인한다.
7. 관리자 화면에서 공개 문장을 숨긴 뒤 TV snapshot에서 제외되는지 확인한다.
8. `LLM_ENABLED=false`와 `KEYWORD_FALLBACK_ENABLED=true`에서도 참가자 완료와 키워드 처리가 가능한지 확인한다.
9. 모바일 네트워크 차단 후 문항 제출 재시도와 새로고침 복구를 확인한다.
10. 이벤트 종료 후 `closed` 처리와 QR/TV/관리자 접근 정책을 현장 책임자와 확인한다.
