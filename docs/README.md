# 마음나무 문서 인덱스

이 폴더는 마음나무 이벤트 MVP를 실제 구현 가능한 웹서비스로 만들기 위한 기준 문서 모음이다. `docs/`는 설계 기준 문서이고, `docs/phases/`는 Codex가 단계별로 실행할 구현 지시서를 담는 위치로 사용한다.

## 문서 목적

마음나무는 소방안전박람회 부스 방문자가 QR로 접속해 짧게 마음상태를 점검하고, 마음카드와 응원 문장을 남기면, 정제된 익명 키워드가 TV 화면의 나무 잎 워드클라우드로 표시되는 이벤트형 리본톡 체험 서비스다.

이 문서 세트의 목표는 다음이다.

- MVP 범위와 제외 범위를 명확히 고정한다.
- DB, API, 세션, 화면, LLM 처리 흐름을 Codex가 임의로 결정하지 않게 한다.
- 박람회 현장의 네트워크 지연, LLM 지연, TV 연결 끊김을 기본 운영 조건으로 반영한다.
- 개인 결과와 원문 문장은 공개하지 않고, TV에는 익명 키워드만 표시하는 원칙을 유지한다.

## 문서 목록

```txt
docs/
  README.md
  00-project-overview.md
  01-mvp-scope.md
  03-system-architecture.md
  04-data-model.md
  05-api-spec.md
  06-frontend-structure.md
  07-backend-structure.md
  08-session-state.md
  09-scoring-risk-policy.md
  10-llm-keyword-policy.md
  11-tv-display-policy.md
  12-admin-policy.md
  13-security-privacy-policy.md
  14-docker-runtime.md
  15-testing-operation-checklist.md
  99-out-of-scope.md
  codex-common-rules.md
  data/
    README.md
    questions_fire_expo_2026.json
    scoring_rules_v1.json
    260508_소방박람회_조사항목_full_version.csv
  phases/
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



## Phase 문서 목록

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

## 권장 읽기 순서

1. `00-project-overview.md`  
   서비스 정의, 사용자 흐름, 운영 원칙을 확인한다.

2. `01-mvp-scope.md`  
   MVP에 반드시 포함할 기능과 제외할 기능을 확인한다.

3. `03-system-architecture.md`  
   React, FastAPI, PostgreSQL, Docker Compose, SSE 구조를 확인한다.

4. `04-data-model.md`  
   PostgreSQL 테이블, 상태값, 인덱스, 데이터 공개 정책을 확인한다.

5. `05-api-spec.md`  
   참가자, TV, 관리자 API의 요청/응답 구조와 상태 전이 규칙을 확인한다.

6. `06-frontend-structure.md`와 `07-backend-structure.md`  
   실제 코드 폴더 구조와 책임 분리를 확인한다.

7. `08-session-state.md`~`15-testing-operation-checklist.md`  
   세션, 점수화, LLM, TV, 관리자, 보안, Docker, 테스트 정책을 확인한다.

8. `99-out-of-scope.md`  
   MVP에서 제외하는 기능을 확인한다.

9. `codex-common-rules.md`  
   Codex가 모든 Phase에서 반드시 지켜야 할 공통 구현 규칙을 확인한다.


## 데이터 seed 파일

문항 CSV는 구현에서 바로 읽기 쉽도록 JSON으로 변환했다.

```txt
docs/data/questions_fire_expo_2026.json
docs/data/scoring_rules_v1.json
```

`questions_fire_expo_2026.json`은 다음을 포함한다.

```txt
- 1~77번 문항
- questionKey
- options
- scoreMap
- 척도별 목적
- 척도별 절단점
- K-SCS 역채점 문항
- ruleVersion
```

Codex는 Phase 04에서 이 JSON 파일들을 기준으로 `questions` 테이블 seed와 scoring rule을 구현한다.

## 고정 기술 스택

```txt
Frontend: React, Vite, TypeScript
Backend: Python, FastAPI
Database: PostgreSQL
Runtime: Docker, Docker Compose
Development: VS Code + Codex
Realtime Display: SSE
```

## 핵심 구현 원칙

```txt
1. 참가자 흐름은 네트워크 지연에도 최대한 끊기지 않아야 한다.
2. LLM 처리 때문에 참가자가 기다리면 안 된다.
3. TV 반영은 준실시간이면 충분하며, 수 초~수십 초 지연을 허용한다.
4. TV에는 개인 결과, 점수, 원문, 위험 플래그를 표시하지 않는다.
5. 위험 판단과 공개 여부는 LLM이 아니라 서버 규칙과 관리자 검수로 결정한다.
6. PostgreSQL은 정형 데이터와 원문 데이터의 기본 저장소로 사용한다.
7. 사용자 입력에서 직접 SQL을 생성하지 않는다.
8. 백엔드는 명시적 service/repository/query function을 통해서만 데이터를 조회한다.
```


## Codex Phase 문서

`docs/phases/`는 Codex에 직접 붙여넣을 수 있는 단계별 구현 지시서다. `phase-00`부터 `phase-11`까지 순서대로 진행하며, 각 Phase는 목표, 작업 전 확인 사항, 수정 또는 생성할 파일, 구현 내용, 금지 사항, 완료 기준, 테스트 방법, 작업 후 보고 형식을 포함한다.

## Codex 사용 방식

Codex에게 구현을 맡길 때는 다음 순서를 따른다.

```txt
1. codex-common-rules.md를 먼저 읽게 한다.
2. 현재 Phase와 직접 관련된 기준 문서를 읽게 한다.
3. 현재 코드베이스를 먼저 확인하게 한다.
4. 해당 Phase 범위 안에서만 파일을 생성·수정하게 한다.
5. 작업 후 변경 파일, 변경 이유, 실행 방법, 남은 작업을 보고하게 한다.
```

## MVP 이후 확장 후보

다음 기능은 MVP에서 제외하고, 별도 확장 Phase에서 다룬다.

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
