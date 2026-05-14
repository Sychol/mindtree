# PHASE 11. 현장 운영 하드닝·장애 대응 테스트

이 문서는 VS Code Codex에 그대로 붙여넣어 사용할 수 있는 Phase 작업 지시서다.  
모든 작업은 `docs/codex-common-rules.md`를 우선 기준으로 삼는다.


## 목표

박람회 현장에서 마음나무 MVP가 끊기지 않고 운영될 수 있도록 장애 대응, 네트워크 실패, LLM disabled/mock, fallback 키워드, SSE 재연결, 상품 지급 중복 방지, 개인정보/공개 제한을 최종 점검한다.  
이 Phase는 신규 대형 기능 추가가 아니라 안정성 검증과 운영 준비 단계다.

## 작업 전 확인 사항

```txt
- Phase 00~10이 완료되었는지 확인한다.
- docs/15-testing-operation-checklist.md를 읽는다.
- docs/13-security-privacy-policy.md를 읽는다.
- docs/99-out-of-scope.md를 읽고 MVP 제외 기능을 추가하지 않는다.
- 실제 운영 secret이 코드에 들어 있지 않은지 확인한다.
```

## 참조 문서

```txt
- docs/codex-common-rules.md
- docs/01-mvp-scope.md
- docs/05-api-spec.md
- docs/08-session-state.md
- docs/09-scoring-risk-policy.md
- docs/10-llm-keyword-policy.md
- docs/11-tv-display-policy.md
- docs/12-admin-policy.md
- docs/13-security-privacy-policy.md
- docs/14-docker-runtime.md
- docs/15-testing-operation-checklist.md
- docs/99-out-of-scope.md
```

## 수정 또는 생성할 파일

```txt
scripts/
├── field-smoke-test.sh
├── reset-local-db.sh 선택사항
└── seed-demo-event.sh 선택사항

api/tests/
├── test_field_participant_flow.py
├── test_field_network_idempotency.py
├── test_field_llm_disabled.py
├── test_field_display_privacy.py
└── test_field_rewards.py

web/src/
└── tests/field-flow.spec.ts 또는 기존 테스트 구조에 맞는 파일

docs/
└── field-runbook.md 선택사항
```

기존 테스트 도구가 없다면 무리하게 새 도구를 추가하지 말고, 현재 프로젝트의 테스트 방식에 맞춘다.

## 구현 내용

### 1. 현장 smoke test 스크립트

`scripts/field-smoke-test.sh` 또는 같은 역할의 스크립트를 만든다.

검증 항목:

```txt
- API health check
- web 접속 가능 여부
- postgres 연결 가능 여부
- event public 조회
- session 생성
- questions 77개 조회
- display snapshot 조회
```

주의:

```txt
- 운영 secret을 출력하지 않는다.
- 실제 운영 DB를 초기화하는 명령을 포함하지 않는다.
```

### 2. 참가자 end-to-end API 테스트

API 레벨에서 다음 흐름을 테스트한다.

```txt
1. 이벤트 조회
2. 세션 생성
3. 동의 저장
4. 문항 조회
5. 응답 bulk 저장
6. scoring complete
7. summary 조회 및 viewed 처리
8. 마음카드 작성
9. 타인 카드 선택
10. 응원 문장 작성
11. 완료 코드 발급
```

검증 기준:

```txt
- 키워드 job이 늦어도 완료 코드 발급이 가능해야 한다.
- 위험 플래그가 있어도 참가자 완료는 막지 않아야 한다.
- 공개 제한 대상 원문은 TV 집계에서 제외되어야 한다.
```

### 3. 네트워크 실패와 idempotency 테스트

테스트 항목:

```txt
- 같은 answers/bulk 요청을 여러 번 보내도 중복 답변 row가 생기지 않음
- 같은 scoring complete 요청을 여러 번 보내도 scale_scores가 중복되지 않음
- 같은 completion-code 요청을 여러 번 보내도 같은 코드 반환
- 지급 redeem 중복 요청은 두 번째 요청이 실패 또는 already_redeemed 응답
```

프론트 수동 테스트:

```txt
- 제출 직전 API 서버 중단
- 재시도 UI 표시 확인
- API 서버 복구 후 같은 입력으로 제출 성공 확인
- 입력값이 초기화되지 않는지 확인
```

### 4. LLM disabled/mock/fallback 테스트

환경별 테스트:

```txt
LLM_ENABLED=false:
- template summary 제공
- fallback keyword 사용 가능

LLM_PROVIDER=mock 성공:
- mock keyword 저장

LLM_PROVIDER=mock 실패:
- fallback keyword 저장
- keyword_jobs.fallback_used=true
```

검증 기준:

```txt
- LLM 실패가 참가자 완료 실패로 이어지지 않는다.
- failed/retry_wait job 상태가 관리자 화면에서 보인다.
```

### 5. SSE 재연결과 TV privacy 테스트

테스트 항목:

```txt
- display snapshot에 원문 body가 없는지
- display snapshot에 session id, score, risk flag가 없는지
- SSE 연결 중 API 서버 재시작 후 화면이 마지막 데이터를 유지하는지
- 재연결 후 최신 데이터로 갱신되는지
```

가능하면 browser-level 테스트를 추가한다. 어렵다면 수동 테스트 절차를 `docs/field-runbook.md`에 남긴다.

### 6. 관리자 운영 테스트

검증 항목:

```txt
- 검수 대기 카드 확인
- exclude 처리 후 TV에서 제외
- keyword 숨김 후 TV에서 제외
- failed job 재처리
- 완료 코드 조회
- 지급 처리
- 중복 지급 방지
- audit log 생성
```

### 7. 보안·개인정보 점검

점검 항목:

```txt
- .env.example에 placeholder만 있는지
- 실제 API key가 코드에 없는지
- resumeToken 원문이 DB에 없는지
- TV payload에 원문/점수/위험 플래그가 없는지
- 관리자 API가 인증 없이 열려 있지 않은지
- CORS가 개발/운영 환경별로 제어 가능한지
```

### 8. 현장 운영 runbook

선택적으로 `docs/field-runbook.md`를 작성한다.

포함 내용:

```txt
- 운영 전 준비
- docker compose 실행
- DB migration
- demo event seed
- QR URL 확인
- TV URL 확인
- 관리자 로그인
- LLM disabled/mock 모드 확인
- 장애 발생 시 조치
- 운영 종료 후 확인
```

## 금지 사항

```txt
- 새로운 대형 기능을 추가하지 않는다.
- RAG, pgvector, Redis/Celery, 기관형 통계, 상담 라우팅을 추가하지 않는다.
- 테스트 편의를 위해 개인정보 보호 정책을 약화하지 않는다.
- TV에 원문을 표시하는 임시 디버그 화면을 만들지 않는다.
- 실제 운영 secret을 테스트 코드나 문서에 넣지 않는다.
```

## 완료 기준

```txt
- field smoke test가 실행 가능하다.
- 참가자 전체 API 흐름 테스트가 통과한다.
- idempotency와 네트워크 재시도 관련 테스트가 통과한다.
- LLM disabled/mock/fallback 테스트가 통과한다.
- TV display privacy 테스트가 통과한다.
- 완료 코드 중복 지급 방지 테스트가 통과한다.
- 관리자 audit log 테스트가 통과한다.
- 운영 runbook 또는 체크리스트가 정리된다.
```

## 테스트 방법

```bash
docker compose up --build
bash scripts/field-smoke-test.sh
```

API 테스트:

```bash
cd api
pytest tests/test_field_participant_flow.py tests/test_field_network_idempotency.py tests/test_field_llm_disabled.py tests/test_field_display_privacy.py tests/test_field_rewards.py
```

프론트엔드:

```bash
cd web
npm run build
npm run test -- --run
```

수동 현장 시나리오:

```txt
1. QR URL 접속
2. 1~77번 문항 진행
3. API 서버 일시 중단 후 제출 실패 확인
4. API 서버 복구 후 재시도 성공 확인
5. 마음카드와 응원 문장 작성
6. 완료 코드 발급 확인
7. TV 화면에 키워드만 표시되는지 확인
8. SSE 재연결 확인
9. 관리자 화면에서 검수/지급/감사 로그 확인
```

## 작업 후 보고 형식

```txt
작업 후 다음 형식으로 보고한다.

1. 변경 파일 목록
   - 경로
   - 변경 이유

2. 구현 내용 요약
   - 이번 Phase에서 완료한 기능
   - docs 기준과 맞춘 부분

3. 실행 및 테스트 결과
   - 실행한 명령
   - 성공/실패 여부
   - 실패 시 원인과 남은 조치

4. TODO 및 남은 작업
   - 임시 구현이 있다면 이유와 위치
   - 다음 Phase에서 이어서 해야 할 사항

5. 범위 준수 확인
   - 현재 Phase 범위 밖 기능을 구현하지 않았는지
   - 기술 스택을 임의 변경하지 않았는지
   - 실제 API Key 또는 운영 Secret을 코드에 넣지 않았는지
```
