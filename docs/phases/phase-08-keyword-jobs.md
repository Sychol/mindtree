# PHASE 08. 비동기 키워드 추출·LLM job·fallback 키워드

이 문서는 VS Code Codex에 그대로 붙여넣어 사용할 수 있는 Phase 작업 지시서다.  
모든 작업은 `docs/codex-common-rules.md`를 우선 기준으로 삼는다.


## 목표

마음카드와 응원 문장에서 키워드를 추출하는 PostgreSQL 기반 비동기 job 처리를 구현한다.  
LLM은 키워드 후보 추출 보조 도구이며, 실패하거나 지연되면 규칙 기반 fallback 키워드 추출을 사용한다. 참가자 흐름은 키워드 추출 완료를 기다리지 않는다.

## 작업 전 확인 사항

```txt
- Phase 07에서 mind_card/reply 저장 시 keyword_jobs가 생성되는지 확인한다.
- docs/10-llm-keyword-policy.md를 반드시 읽는다.
- Redis/Celery는 MVP 범위에서 제외한다는 원칙을 확인한다.
- PostgreSQL 기반 keyword_jobs 상태 관리가 MVP에 포함된다는 기준을 확인한다.
```

## 참조 문서

```txt
- docs/codex-common-rules.md
- docs/04-data-model.md
- docs/05-api-spec.md
- docs/07-backend-structure.md
- docs/10-llm-keyword-policy.md
- docs/11-tv-display-policy.md
- docs/12-admin-policy.md
- docs/13-security-privacy-policy.md
- docs/15-testing-operation-checklist.md
```

## 수정 또는 생성할 파일

```txt
api/app/
├── services/keywords/
│   ├── __init__.py
│   ├── extractor.py
│   ├── fallback_extractor.py
│   ├── normalizer.py
│   ├── synonym_map.py
│   ├── job_runner.py
│   └── llm_keyword_extractor.py
├── services/llm/
│   ├── base.py
│   ├── mock_client.py
│   └── provider.py
├── repositories/keyword_jobs.py
├── repositories/keywords.py
├── api/routes/keyword_jobs_internal.py 선택사항
└── workers/keyword_worker.py 선택사항

api/tests/
├── test_fallback_keyword_extractor.py
├── test_keyword_normalizer.py
├── test_keyword_job_runner.py
└── test_llm_keyword_fallback.py
```

## 구현 내용

### 1. keyword job 상태 모델 사용

`keyword_jobs` 상태를 다음 기준으로 사용한다.

```txt
pending:
  처리 대기

processing:
  worker가 처리 중

succeeded:
  키워드 저장 완료

failed:
  최대 재시도 후 실패

retry_wait:
  일시 실패 후 다음 재시도 대기
```

필수 기록:

```txt
- source_type: mind_card 또는 reply
- source_id
- status
- attempts
- max_attempts
- available_at
- started_at
- finished_at
- extraction_method: llm 또는 fallback
- fallback_used
- error_message
```

### 2. PostgreSQL 기반 job claim

구현 기준:

```txt
- pending 또는 retry_wait 중 available_at이 지난 job을 가져온다.
- 동시에 여러 worker가 실행되어도 같은 job을 중복 처리하지 않게 한다.
- 가능하면 SELECT FOR UPDATE SKIP LOCKED를 사용한다.
- processing으로 바꾼 뒤 처리한다.
- 성공 시 succeeded, 실패 시 retry_wait 또는 failed로 전이한다.
```

주의:

```txt
- Redis/Celery를 추가하지 않는다.
- public API로 무작정 job 실행 endpoint를 열지 않는다.
- 내부 개발용 endpoint가 필요하면 인증 또는 local-only 조건을 둔다.
```

### 3. fallback 키워드 추출

LLM 없이도 작동하는 fallback extractor를 구현한다.

기본 처리:

```txt
- 입력 문장 normalize
- 금칙어와 개인정보 패턴 제거
- 조사/불용어 제거
- 너무 짧은 단어 제거
- 회복/응원/감정 관련 사전 매핑
- 유사어 병합
- 최대 키워드 수 제한
```

예시 매핑:

```txt
잠이 안 와요 -> 잠, 피로
가슴이 답답해요 -> 답답함, 긴장
괜찮아요 쉬어가도 돼요 -> 위로, 쉼
버텨줘서 고마워요 -> 응원, 감사
```

주의:

```txt
- 위기 표현, 실명, 연락처, 구체 사건 정보는 키워드로 저장하지 않는다.
- 안전 상태가 exclude인 source는 키워드 추출에서 제외한다.
```

### 4. LLM 키워드 추출

LLM 사용 기준:

```txt
- LLM_ENABLED=true일 때만 사용한다.
- LLM_PROVIDER=mock이면 mock client를 사용한다.
- 실제 provider 구현은 API key 없이 placeholder 또는 TODO로 둘 수 있다.
- timeout과 retry를 둔다.
- JSON schema 형태로 키워드 후보를 받도록 한다.
```

LLM prompt 제한:

```txt
- 진단하지 말 것
- 위험도 판단하지 말 것
- 공개 여부 판단하지 말 것
- 원문을 재작성하지 말 것
- 명사형 또는 짧은 구 형태 키워드만 추출할 것
- 개인정보, 특정 사건, 위기 표현은 제외할 것
```

LLM 실패 시:

```txt
- fallback extractor를 실행한다.
- keyword_jobs.fallback_used=true로 기록한다.
- 실패 원인을 error_message에 축약 저장한다.
```

### 5. 키워드 저장 및 병합

`keywords` 저장 기준:

```txt
- event_id
- source_type
- source_id
- original_text 또는 raw_keyword
- normalized_text
- category
- weight
- extraction_method
- status=active 기본
```

정규화 기준:

```txt
- 공백 제거/정리
- 너무 긴 키워드 제외
- 유사어 map 적용
- 금칙어 제외
- 중복 keyword는 같은 source 내에서 하나로 합친다.
```

### 6. worker 실행 방식

MVP에서는 다음 중 하나로 구현한다.

```txt
권장 A:
- FastAPI startup에서 KEYWORD_WORKER_ENABLED=true일 때 background loop 실행
- local/dev에서만 명확히 사용

권장 B:
- 관리자가 재처리 버튼을 누르면 service가 job을 처리
- 테스트에서는 job_runner.process_next_jobs() 직접 호출
```

어떤 방식을 선택하든 다음은 지킨다.

```txt
- 참가자 요청 thread를 오래 점유하지 않는다.
- job 처리 실패가 API 전체 장애로 이어지지 않는다.
- worker 활성화 여부는 환경변수로 제어한다.
```

### 7. 테스트

필수 테스트:

```txt
- fallback extractor가 기본 키워드를 반환한다.
- 개인정보/위기 표현이 키워드에서 제외된다.
- LLM mock 성공 시 llm method로 keyword가 저장된다.
- LLM mock 실패 시 fallback keyword가 저장된다.
- exclude 상태 source는 keyword 생성 대상에서 제외된다.
- job 성공 시 status=succeeded가 된다.
- 반복 실패 시 failed 또는 retry_wait가 된다.
```

## 금지 사항

```txt
- Redis/Celery를 추가하지 않는다.
- 키워드 추출 완료를 참가자 완료 조건으로 만들지 않는다.
- LLM이 공개 여부나 위험도를 결정하게 하지 않는다.
- TV에 원문을 보내지 않는다.
- 실제 LLM API key를 코드에 넣지 않는다.
- RAG 후보 생성/export를 구현하지 않는다.
```

## 완료 기준

```txt
- keyword_jobs를 claim/process/update할 수 있다.
- fallback 키워드 추출이 동작한다.
- LLM mock 성공/실패 경로가 모두 동작한다.
- keywords 테이블에 정제된 키워드가 저장된다.
- job status, fallback_used, error_message가 기록된다.
- 관련 테스트가 통과한다.
```

## 테스트 방법

```bash
cd api
pytest tests/test_fallback_keyword_extractor.py tests/test_keyword_normalizer.py tests/test_keyword_job_runner.py tests/test_llm_keyword_fallback.py
```

수동 확인:

```txt
1. 마음카드 또는 응원 문장을 저장해 keyword_job 생성
2. KEYWORD_WORKER_ENABLED=false에서 job이 pending 유지되는지 확인
3. job_runner를 수동 실행
4. keywords 저장 확인
5. LLM mock failure 모드에서 fallback_used=true 확인
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
