# 10. LLM and Keyword Policy

## 1. 목적

이 문서는 마음나무 MVP에서 LLM과 키워드 추출을 어떻게 사용할지 정의한다.

핵심 원칙은 다음이다.

```txt
- LLM은 보조 도구다.
- 참가자 흐름은 LLM 응답을 기다리지 않는다.
- 키워드 추출은 서버 내부 비동기 job으로 처리한다.
- LLM 실패 시 규칙 기반 fallback 키워드를 사용한다.
- TV에는 원문이 아니라 정제된 익명 키워드만 표시한다.
- LLM은 진단, 위험 판단, 공개 여부 판단, 관리자 승인 대체를 하지 않는다.
```

## 2. LLM의 허용 역할

```txt
허용:
- 마음신호 요약 문장 톤 보정
- 마음카드에서 키워드 후보 추출
- 응원 문장에서 키워드 후보 추출
- 키워드 category 후보 제안
- 과도하게 딱딱한 문장 완화
```

## 3. LLM의 금지 역할

```txt
금지:
- 진단
- 위험도 최종 판정
- 자살위험 최종 판단
- 공개 여부 결정
- 관리자 승인 대체
- 세션 상태 결정
- DB 구조 결정
- API 구조 결정
- SQL 생성
- 원문을 TV에 노출할지 판단
```

## 4. 처리 모드

환경변수로 LLM 모드를 제어한다.

```txt
LLM_ENABLED=false
LLM_PROVIDER=mock | openai | none
LLM_TIMEOUT_SECONDS=5
KEYWORD_FALLBACK_ENABLED=true
```

### 4.1 disabled mode

```txt
- LLM 호출 없음
- 템플릿 요약 사용
- fallback keyword extraction 사용
- 운영 리허설과 장애 대응 테스트에 사용
```

### 4.2 mock mode

```txt
- 고정 응답 또는 deterministic 응답 반환
- Codex 구현/테스트에 사용
- 실제 API key 불필요
```

### 4.3 live mode

```txt
- 실제 provider 호출
- timeout, retry, rate limit 처리 필요
- 실제 API key는 환경변수로만 주입
```

## 5. Keyword Job Lifecycle

`keyword_jobs.status`는 다음을 사용한다.

```txt
pending
processing
succeeded
failed
retry_wait
```

처리 흐름:

```txt
마음카드 또는 응원 문장 저장
→ 안전 필터 적용
→ 공개 가능 또는 검수 대상 상태 결정
→ keyword_jobs 생성
→ 참가자는 다음 단계 이동
→ worker가 pending job claim
→ LLM 추출 시도
→ 실패 시 fallback 추출
→ keywords 저장
→ job succeeded 또는 failed 기록
→ TV snapshot 집계에 반영
```

## 6. Job 생성 기준

### 6.1 생성 대상

```txt
source_type = mind_card
source_type = reply
source_type = summary
```

MVP에서 TV 반영의 핵심 대상은 `mind_card`와 `reply`다. `summary` 키워드는 후속 확장에서 사용할 수 있다.

### 6.2 생성 제한

아래 조건에서는 keyword job을 만들지 않거나 job은 만들되 TV 집계 대상에서 제외한다.

```txt
- safety_status = exclude
- public_status = excluded
- risk_flags.public_restriction = true
- crisis_expression_detected = true
- 개인정보 또는 식별 가능한 사건 정보가 제거되지 않음
```

관리자 재검수 후 safe/public으로 바뀌면 keyword job을 새로 생성하거나 재계산할 수 있다.

## 7. 입력 데이터 정책

LLM에는 필요한 최소 입력만 전달한다.

```txt
preferred input:
- content_redacted가 있으면 content_redacted
- 없으면 safety filter를 통과한 content_raw
- source_type
- reply_type 또는 prompt_type
- event language
```

LLM에 전달하지 않는 것:

```txt
- session_id
- resumeToken
- 완료 코드
- 관리자 정보
- 척도 점수 원문
- 위험 플래그 상세
- DB 내부 구조
```

## 8. LLM Output Schema

LLM 응답은 자유문장이 아니라 구조화 JSON으로 받는다.

예시:

```json
{
  "keywords": [
    {
      "text": "쉼",
      "normalized": "쉼",
      "category": "recovery",
      "weight": 1.0
    },
    {
      "text": "괜찮아",
      "normalized": "괜찮아",
      "category": "support",
      "weight": 1.0
    }
  ]
}
```

허용 category:

```txt
mind_signal
support
recovery
coping
neutral
```

스키마 파싱에 실패하면 fallback을 사용한다.

## 9. Prompt 원칙

Prompt는 다음을 명확히 지시한다.

```txt
- 진단하지 말 것
- 위험도 판단하지 말 것
- 공개 여부 판단하지 말 것
- 원문을 요약해서 길게 반환하지 말 것
- 1~5개의 짧은 한국어 키워드만 반환할 것
- 개인정보, 구체적 장소, 실명, 사건명은 키워드로 반환하지 말 것
- 부적절하거나 위험한 표현은 키워드로 반환하지 말 것
- 반드시 JSON schema를 따를 것
```

## 10. Fallback Keyword Extraction

LLM 실패 시 fallback은 반드시 동작해야 한다.

### 10.1 기본 절차

```txt
1. 입력 텍스트 정규화
2. 금칙어 제거
3. 개인정보 패턴 제거
4. 조사/불용어 제거
5. 너무 짧은 토큰 제거
6. 감정·회복 사전 매핑
7. 유사어 병합
8. 최대 1~5개 키워드 반환
```

### 10.2 예시 매핑

```txt
잠이 안 와요 → 잠, 피로
가슴이 답답해요 → 답답함, 긴장
괜찮아요, 쉬어가도 돼요 → 위로, 쉼
오늘도 버텼어요 → 버팀, 회복
숨을 천천히 쉬어봐요 → 호흡, 안정
```

### 10.3 불용어 예시

```txt
나
너
우리
오늘
그냥
정말
많이
조금
때문에
하지만
그래도
```

### 10.4 금칙어 예시 범위

구체 단어 목록은 별도 seed로 관리한다.

```txt
- 자해·자살·죽음 관련 직접 표현
- 욕설/혐오 표현
- 특정 개인 비난 표현
- 실명/전화번호/소속/구체 장소/날짜 패턴
```

## 11. 유사어 병합 정책

`normalized_keyword` 기준으로 TV 집계한다.

예시:

```txt
쉬고싶다, 쉬어가기, 휴식 → 쉼
괜찮다, 괜찮아, 괜찮습니다 → 괜찮아
불안, 초조, 긴장됨 → 긴장
피곤, 지침, 소진 → 피로
버텼다, 견뎠다 → 버팀
```

유사어 사전은 코드 상수 또는 seed JSON으로 시작한다. 관리자 화면에서 후속 수정할 수 있다.

## 12. Keyword 저장 기준

`keywords` 테이블 저장 필드:

```txt
source_type
source_id
keyword_text
normalized_keyword
category
weight
status
extraction_method
job_id
```

`extraction_method` 값:

```txt
llm
fallback
admin
```

TV 집계 조건:

```txt
keywords.status = active
source safety_status = safe
source public_status != excluded
risk_flags.public_restriction = false
normalized_keyword가 금칙어가 아님
```

## 13. Retry 정책

권장 기본값:

```txt
max_attempts = 2
LLM timeout = 5초
retry_wait = 10~30초
fallback enabled = true
```

처리 기준:

```txt
1차 LLM 실패:
- fallback 실행 가능하면 fallback 사용
- succeeded + fallback_used = true

fallback도 실패:
- failed
- 관리자 화면에 표시

관리자 재시도:
- attempts reset 또는 증가 정책 선택
- status = pending
- audit log 기록
```

## 14. 관리자 개입

관리자는 다음을 할 수 있다.

```txt
- 키워드 숨김
- 키워드 정규화 값 수정
- category 수정
- keyword job 재시도
- source 검수 후 키워드 재계산
```

관리자 수정 키워드는 `extraction_method = admin` 또는 audit log로 추적한다.

## 15. TV 반영 지연 정책

키워드는 비동기 처리 후 TV에 반영된다.

```txt
참가자 완료:
즉시 가능

키워드 추출:
수 초~수십 초 지연 허용

LLM 실패:
fallback 키워드 또는 미반영

TV 화면:
마지막 snapshot 유지
```

참가자에게 “키워드가 TV에 바로 보이지 않을 수 있음”을 UI에서 굳이 강조할 필요는 없다. 현장 운영 안정성을 우선한다.

## 16. 구현 파일 기준

```txt
api/app/llm/base.py
api/app/llm/mock_provider.py
api/app/llm/openai_provider.py
api/app/llm/prompts.py
api/app/llm/output_parser.py
api/app/services/keyword_service.py
api/app/services/keyword_job_service.py
api/app/services/safety_filter_service.py
api/app/workers/keyword_worker.py
api/app/repositories/keyword_repository.py
api/app/repositories/keyword_job_repository.py
api/app/tests/test_keyword_fallback.py
api/app/tests/test_keyword_jobs.py
```

## 17. 테스트 기준

```txt
- LLM disabled 상태에서 fallback 키워드 생성
- mock provider 상태에서 deterministic 키워드 생성
- LLM timeout 시 fallback_used = true
- output schema 파싱 실패 시 fallback 사용
- safety_status exclude source는 TV 집계 제외
- 개인정보 패턴이 키워드로 저장되지 않음
- 관리자 keyword hide 후 TV snapshot에서 제외
- failed job 재시도 후 pending 전이
```

## 18. 금지 사항

```txt
- 실제 API key를 코드에 넣지 않는다.
- LLM이 위험 플래그를 판단하게 하지 않는다.
- LLM이 공개 여부를 결정하게 하지 않는다.
- LLM 응답을 그대로 TV에 표시하지 않는다.
- LLM job 완료를 참가자 완료 조건으로 삼지 않는다.
- 원문 전체를 keyword output으로 저장하지 않는다.
- 개인정보, 구체 장소, 실명, 사건명을 키워드로 남기지 않는다.
```
