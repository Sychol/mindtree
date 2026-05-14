# 마음나무 Codex 구현 Phase 문서

이 폴더는 마음나무 이벤트 MVP를 VS Code Codex로 단계별 구현하기 위한 Markdown 작업 지시서 모음이다.

`docs/`의 일반 문서는 설계 기준 문서이고, `docs/phases/`의 문서는 Codex가 실제로 수행할 작은 작업 단위다. Codex는 각 Phase 문서를 하나씩 읽고, 해당 Phase 범위 안에서만 구현한다.

## 실행 원칙

```txt
1. 반드시 phase-00부터 순서대로 진행한다.
2. 이전 Phase가 완료되지 않았으면 다음 Phase를 시작하지 않는다.
3. 모든 Phase는 docs/codex-common-rules.md를 먼저 따른다.
4. 현재 Phase와 직접 관련된 docs 기준 문서를 읽은 뒤 작업한다.
5. 기존 파일을 임의로 삭제하지 않는다.
6. Phase 범위 밖의 기능을 미리 구현하지 않는다.
7. 기술 스택을 임의로 변경하지 않는다.
8. 실제 API Key, 운영 DB 비밀번호, 운영 Secret을 코드에 넣지 않는다.
9. 임시 구현이 필요한 경우 TODO와 이유를 남긴다.
10. 작업 후 변경 파일, 변경 이유, 실행 방법, 테스트 결과, 남은 작업을 보고한다.
```

## Phase 목록

```txt
docs/phases/
  README.md
  _phase-template.md
  phase-00-repo-docker.md
  phase-01-fastapi-base.md
  phase-02-postgresql-models.md
  phase-03-event-session-consent.md
  phase-04-questions-scoring.md
  phase-05-participant-flow-retry.md
  phase-06-risk-summary-llm-fallback.md
  phase-07-cards-replies.md
  phase-08-keyword-jobs.md
  phase-09-tv-sse-display.md
  phase-10-admin-rewards.md
  phase-11-field-hardening.md
```

## 권장 실행 순서

| Phase | 목적 | 주요 산출물 |
|---|---|---|
| 00 | 레포와 Docker 기반 | 기본 폴더, `.env.example`, `docker-compose.yml`, API/Web 컨테이너 기반 |
| 01 | FastAPI 기반 | health check, settings, router, error format, 기본 테스트 |
| 02 | PostgreSQL 모델 | Alembic, SQLAlchemy 모델, 핵심 테이블, DB 세션 |
| 03 | 이벤트·세션·동의 | 공개 이벤트 조회, 익명 세션 생성/복구, 동의 저장 |
| 04 | 문항·점수화 | 1~77번 문항 조회, 응답 저장, 점수화, 위험 플래그 |
| 05 | 참가자 플로우 | 모바일 라우트, 문항 선로딩, 로컬 진행 상태, 제출 재시도 |
| 06 | 요약·LLM fallback | 템플릿 요약, 선택적 LLM 보정, 도움 안내, summary_viewed |
| 07 | 카드·응원·완료 | 마음카드, 타인 카드 선택, 응원 문장, 완료 코드 발급 |
| 08 | 키워드 job | PostgreSQL 기반 비동기 job, LLM 추출, fallback 키워드 |
| 09 | TV SSE | display snapshot, SSE stream, TV 워드클라우드, 자동 재연결 |
| 10 | 관리자·상품 | 관리자 인증, 검수, keyword/job 상태, 완료 코드 지급 처리 |
| 11 | 현장 하드닝 | 장애 테스트, LLM mock/disabled, SSE 재연결, 운영 체크리스트 |

## 공통 참조 문서

모든 Phase는 아래 문서를 기본 기준으로 삼는다.

```txt
docs/codex-common-rules.md
docs/01-mvp-scope.md
docs/03-system-architecture.md
docs/04-data-model.md
docs/05-api-spec.md
```

Phase별로 추가 참조 문서는 각 파일의 `참조 문서` 섹션에 적혀 있다.

## Phase 작업 후 보고 형식

Codex는 모든 Phase 완료 후 아래 형식으로 보고해야 한다.

```md
## 작업 요약
- ...

## 변경 파일
- path/to/file: 변경 이유

## 실행 방법
- ...

## 테스트 결과
- ...

## 남은 작업 / TODO
- ...

## 주의 사항
- ...
```

## 중요한 범위 제한

마음나무 MVP는 박람회 현장에서 안정적으로 운영되는 이벤트 서비스가 목표다. 따라서 다음 기능은 `docs/phases/` 구현 범위에 포함하지 않는다.

```txt
- RAG 후보 승인/반려
- RAG 데이터 export
- pgvector 기반 유사 사례 검색
- 기관형 멀티테넌트
- 상담 라우팅
- 장기 사용자 히스토리
- Redis/Celery 기반 작업 큐
- 복잡한 관리자 통계 대시보드
- 자동 리포트 생성
```

PostgreSQL 기반 `keyword_jobs`는 MVP에 포함한다. 이는 LLM 지연·실패·재처리 상태를 현장에서 확인하기 위한 최소 운영 장치다.
