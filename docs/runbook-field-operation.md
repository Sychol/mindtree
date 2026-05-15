# 마음나무 현장 운영 Runbook

이 문서는 local/dev 리허설과 박람회 현장 운영 절차를 정리한다. 실제 운영 secret, API key, DB password, 관리자 실제 비밀번호는 문서에 적지 않는다.

## 1. 운영 전 준비

- 장비: 운영 노트북, TV 또는 대형 모니터, 모바일 테스트 기기, 안정적인 전원.
- 네트워크: 참가자 모바일망과 운영 노트북망에서 `web`, `api` URL 접근 확인.
- QR URL: `http://localhost:5173/e/fire-expo-2026` 형식의 참가자 URL을 현장 도메인으로 교체해 검수.
- TV URL: `http://localhost:5173/display/fire-expo-2026`.
- 관리자 URL: `http://localhost:5173/admin/login`.
- 관리자 계정: 운영 전 별도 보안 채널에서 생성/회수 절차 확정.
- 상품 지급 담당자: 완료 코드만 보고 지급하며 이름, 전화번호, 소속을 요구하지 않도록 교육.
- 도움 안내 문구: 위험 플래그가 있을 때도 자동 차단이 아니라 현장 안내 기준으로만 사용.
- LLM mode: 운영 전 `LLM_ENABLED=false` 또는 `LLM_PROVIDER=mock` 리허설을 먼저 완료.

## 2. 실행 절차

`.env.example`을 복사해 local/dev 값만 채운다.

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Docker Compose:

```bash
docker compose config
docker compose build
docker compose up -d postgres api web
docker compose ps
```

`docker compose config` 출력에는 `.env` 값이 보일 수 있으므로 외부에 공유하지 않는다.

Migration:

```bash
docker compose exec api alembic upgrade head
```

개발 리허설 seed:

```bash
docker compose exec api python -m app.scripts.seed_dev
```

문항 seed만 다시 실행:

```bash
docker compose exec api python -m app.scripts.seed_questions --event-slug fire-expo-2026
```

관리자 bootstrap:

```bash
docker compose exec api python -m app.scripts.bootstrap_admin
```

`ADMIN_BOOTSTRAP_EMAIL`과 `ADMIN_BOOTSTRAP_PASSWORD`가 비어 있으면 아무 계정도 만들지 않는다.

Keyword worker 1회 실행:

```bash
docker compose exec api python -m app.scripts.run_keyword_worker --once
```

API smoke test:

```bash
docker compose exec api python -m app.scripts.run_smoke_tests
```

Health check:

```bash
curl http://localhost:8000/api/health
```

## 3. URL

- Participant: `http://localhost:5173/e/fire-expo-2026`
- TV Display: `http://localhost:5173/display/fire-expo-2026`
- Admin: `http://localhost:5173/admin/login`
- API Health: `http://localhost:8000/api/health`

현장 배포에서는 localhost 대신 현장 도메인 또는 내부 IP를 사용한다.

## 4. 리허설 절차

1. 참가자 모바일 플로우를 1회 완료한다.
2. 완료 코드가 참가자 화면에 표시되는지 확인한다.
3. keyword worker `--once`를 실행한다.
4. TV 화면에 키워드가 반영되는지 확인한다.
5. 관리자 Rewards 화면에서 완료 코드를 조회하고 지급 처리한다.
6. 같은 완료 코드로 다시 지급을 시도해 중복 지급 에러를 확인한다.
7. 관리자 Cards 또는 Replies 화면에서 공개 문장을 숨김 처리한다.
8. 관련 키워드가 TV snapshot에서 제외되는지 확인한다.
9. TV 화면을 열어 둔 상태에서 API 서버 재시작 또는 네트워크 차단을 수행한다.
10. TV가 마지막 snapshot을 유지하고 `reconnecting` 상태 후 복구되는지 확인한다.

## 5. 이벤트 당일 운영

시작 전:

- Docker 컨테이너 상태 확인.
- `/api/health` 확인.
- 참가자 QR 접속 확인.
- TV URL full screen 확인.
- 관리자 로그인 확인.
- `LLM_ENABLED`, `KEYWORD_FALLBACK_ENABLED` 확인.

운영 중:

- 참가자 제출 실패 문의는 새로고침 전에 재시도 버튼을 먼저 안내.
- TV가 비어 있으면 worker와 keyword status를 확인.
- 검수 대기 문장은 관리자 화면에서 공개/숨김/제외 처리.
- 완료 코드는 코드 기준으로만 지급.
- 중복 지급 에러가 나오면 재지급하지 않고 audit log를 확인.

종료 후:

- 이벤트 상태를 `closed`로 바꾸는 절차를 운영 책임자와 진행.
- 지급 완료 수와 audit log를 확인.
- 운영 데이터 백업/보관 정책을 따른다.
- 테스트 계정과 임시 비밀번호를 회수한다.

## 6. 금지 사항

- 운영 secret, API key, DB password, 관리자 실제 비밀번호 공유 금지.
- TV payload에 원문, 점수, 위험 플래그, 관리자 검수 상태 추가 금지.
- 리허설 없는 운영 금지.
- 테스트 데이터와 실제 데이터 혼합 금지.
- 위험 플래그가 있다는 이유만으로 완료 코드 지급 자동 차단 금지.
- `docker compose down -v`처럼 DB volume을 삭제하는 명령 금지.
