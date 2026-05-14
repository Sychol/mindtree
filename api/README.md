# API

이 폴더는 마음나무 FastAPI 백엔드 위치다.

Phase 01에서는 FastAPI 앱, settings, health check, 공통 error response 구조를 구현했다. Phase 02에서는 PostgreSQL 연결, SQLAlchemy 모델, Alembic 초기 migration, DB session dependency를 구현한다. 비즈니스 API는 아직 구현하지 않는다.

후속 작업:

- Phase 03: 이벤트, 익명 세션, 필수 동의 API 구현
- Phase 04 이후: 문항, 응답, 점수화, 요약, 카드, 키워드, TV, 관리자 API 구현

## 로컬 실행

```bash
cd api
pytest
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
curl http://localhost:8000/api/health
```

## Migration

```bash
cd api
alembic upgrade head
```

Docker 기반 확인:

```bash
docker compose up -d postgres
docker compose run --rm api alembic upgrade head
docker compose run --rm --no-deps api pytest
```

## Docker 실행

```bash
cp .env.example .env
docker compose up --build api
curl http://localhost:8000/api/health
```

`GET /api/health`는 DB 연결 없이 동작한다. DB health check와 실제 업무 API는 후속 Phase에서 추가한다.

TODO:

- Phase 03 이후 실제 업무 router를 `app/api/router.py`에 연결한다.
