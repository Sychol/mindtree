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
