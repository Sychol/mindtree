# PHASE 07. 마음카드·타인 카드·응원 문장

이 문서는 VS Code Codex에 그대로 붙여넣어 사용할 수 있는 Phase 작업 지시서다.  
모든 작업은 `docs/codex-common-rules.md`를 우선 기준으로 삼는다.


## 목표

참가자가 마음신호 요약을 본 뒤 마음카드를 작성하고, 공개 가능한 타인 마음카드 하나를 선택한 뒤, 응원·공감·작은 대처법 문장을 작성하는 흐름을 구현한다.  
사용자 입력은 안전 필터와 공개 상태를 거쳐 저장되며, 키워드 추출 job 생성까지 연결한다. 실제 키워드 추출 실행은 Phase 08에서 구현한다.

## 작업 전 확인 사항

```txt
- Phase 06에서 session.status가 summary_viewed로 전이되는지 확인한다.
- docs/10-llm-keyword-policy.md를 읽는다.
- docs/13-security-privacy-policy.md의 원문 공개 제한 기준을 확인한다.
- docs/05-api-spec.md의 카드/응원 관련 API가 있는지 확인한다.
```

## 참조 문서

```txt
- docs/codex-common-rules.md
- docs/04-data-model.md
- docs/05-api-spec.md
- docs/06-frontend-structure.md
- docs/07-backend-structure.md
- docs/08-session-state.md
- docs/09-scoring-risk-policy.md
- docs/10-llm-keyword-policy.md
- docs/12-admin-policy.md
- docs/13-security-privacy-policy.md
```

## 수정 또는 생성할 파일

```txt
api/app/
├── api/routes/cards.py
├── api/routes/replies.py
├── schemas/cards.py
├── schemas/replies.py
├── services/cards.py
├── services/replies.py
├── services/safety_filter.py
├── services/keyword_job_factory.py
├── repositories/cards.py
├── repositories/replies.py
└── repositories/keyword_jobs.py

api/tests/
├── test_cards_api.py
├── test_replies_api.py
├── test_safety_filter.py
└── test_keyword_job_creation.py

web/src/
├── api/cards.ts
├── api/replies.ts
├── pages/participant/MindCardPage.tsx
├── pages/participant/SelectPeerCardPage.tsx
├── pages/participant/ReplyPage.tsx
├── components/participant/MindCardForm.tsx
├── components/participant/PeerCardList.tsx
└── components/participant/ReplyForm.tsx
```

## 구현 내용

### 1. 마음카드 작성 API

구현 endpoint 예시:

```http
POST /api/sessions/{sessionId}/mind-cards
GET /api/sessions/{sessionId}/mind-cards
```

요청 예시:

```json
{
  "promptType": "to_current_me",
  "body": "오늘은 조금 쉬어가도 괜찮다."
}
```

구현 기준:

```txt
- session.status가 summary_viewed 이상인지 확인한다.
- 세션당 최소 1개, 최대 개수는 event settings를 따른다.
- body 길이 제한을 둔다.
- 실명, 연락처, 소속, 구체 장소/날짜/사건명 입력 금지 안내를 프론트에 표시한다.
- 저장 전 또는 저장 직후 safety_filter를 적용한다.
- safety_status가 safe이면 public_status를 public 또는 pending 정책에 따라 설정한다.
- review/exclude이면 public_status를 pending 또는 excluded로 둔다.
- 마음카드 생성 후 session.status를 card_created로 전이한다.
- keyword_jobs에 source_type=mind_card job을 생성한다. 실제 추출은 Phase 08에서 처리한다.
```

### 2. 안전 필터

규칙 기반 safety filter를 구현한다.

감지 범위:

```txt
- 자해/자살/죽음 관련 직접 표현
- 전화번호, 이메일, 상세 주소처럼 보이는 패턴
- 실명/소속/특정 사건명으로 보일 수 있는 민감 패턴은 보수적으로 review
- 욕설, 혐오, 특정 개인 비난
```

결과:

```txt
safe:
  공개 가능

review:
  관리자 확인 필요

exclude:
  공개 불가, TV 키워드 반영 제외
```

주의:

```txt
- safety filter는 공개 통제를 위한 운영 필터다.
- 참가자 완료와 상품 지급을 자동 차단하지 않는다.
- LLM을 안전 최종 판단자로 사용하지 않는다.
```

### 3. 타인 카드 선택 API

구현 endpoint 예시:

```http
GET /api/events/{eventSlug}/public-mind-cards?excludeSessionId={sessionId}&limit=10
POST /api/sessions/{sessionId}/selected-mind-card
```

구현 기준:

```txt
- public_status=public, safety_status=safe인 카드만 반환한다.
- 자기 세션의 카드는 제외한다.
- 위험 플래그 또는 public_restriction 대상 카드는 제외한다.
- 카드가 부족하면 운영자 seed 카드 또는 예시 카드를 반환할 수 있게 구조를 둔다.
- seed 카드가 없다면 “아직 공개 카드가 부족합니다” 안내가 가능해야 한다.
```

TV와 다른 점:

```txt
- 타인 카드 선택 화면에는 안전한 마음카드 원문이 익명으로 보일 수 있다.
- TV에는 마음카드 원문이 절대 표시되지 않는다.
```

### 4. 응원·공감·작은 대처법 작성 API

구현 endpoint 예시:

```http
POST /api/sessions/{sessionId}/replies
```

요청 예시:

```json
{
  "targetMindCardId": "uuid",
  "replyType": "comfort",
  "body": "그 마음을 버텨낸 것만으로도 충분히 애쓰셨습니다."
}
```

구현 기준:

```txt
- session.status가 card_created 이상인지 확인한다.
- targetMindCardId가 공개 가능한 타인 카드인지 확인한다.
- replyType은 comfort, empathy, small_coping 중 하나만 허용한다.
- body 길이 제한을 둔다.
- safety_filter를 적용한다.
- keyword_jobs에 source_type=reply job을 생성한다.
- 응원 문장 저장 후 session.status를 reply_created로 전이한다.
```

### 5. 프론트엔드 화면

구현 라우트 예시:

```txt
/e/:eventSlug/card/new
/e/:eventSlug/cards/select
/e/:eventSlug/reply/new
```

화면 기준:

```txt
MindCardPage:
- 작성 관점 선택
- 짧은 마음카드 입력
- 식별정보 입력 금지 안내
- 제출 실패 시 입력 유지 및 재시도

SelectPeerCardPage:
- 공개 가능한 타인 카드 목록
- 자기 카드 제외
- 카드 부족 시 seed/안내 표시

ReplyPage:
- replyType 선택
- 응원/공감/작은 대처법 입력
- 제출 성공 시 Phase 10 전까지 completion placeholder 또는 다음 화면으로 이동
```

### 6. 테스트

필수 테스트:

```txt
- summary_viewed 전 마음카드 작성 실패
- 마음카드 작성 후 card_created 상태 전이
- 위기 표현 포함 카드가 exclude 또는 review 처리됨
- 안전한 공개 카드만 타인 카드 목록에 반환됨
- 자기 카드가 타인 카드 목록에 포함되지 않음
- replyType이 허용값이 아니면 실패
- 응원 문장 작성 후 reply_created 상태 전이
- 카드/응원 저장 시 keyword_jobs가 생성됨
```

## 금지 사항

```txt
- 실제 키워드 추출 실행을 구현하지 않는다. Phase 08 범위다.
- TV 워드클라우드를 구현하지 않는다. Phase 09 범위다.
- 관리자 검수 UI를 구현하지 않는다. Phase 10 범위다.
- TV에 원문을 반환하는 API를 만들지 않는다.
- 안전 필터 결과가 review/exclude라고 해서 참가자 완료 자체를 막지 않는다.
```

## 완료 기준

```txt
- 마음카드 작성 API와 화면이 동작한다.
- 타인 카드 선택 API와 화면이 동작한다.
- 응원 문장 작성 API와 화면이 동작한다.
- safety_status와 public_status가 저장된다.
- 카드/응원 저장 시 keyword_jobs가 생성된다.
- 세션 상태가 card_created, reply_created로 전이된다.
- 관련 테스트가 통과한다.
```

## 테스트 방법

```bash
cd api
pytest tests/test_cards_api.py tests/test_replies_api.py tests/test_safety_filter.py tests/test_keyword_job_creation.py
```

프론트엔드:

```bash
cd web
npm run build
npm run test -- --run
```

수동 확인:

```txt
1. summary_viewed 세션 준비
2. 마음카드 작성
3. DB에서 mind_cards와 keyword_jobs 확인
4. 다른 세션으로 공개 카드 목록 조회
5. 타인 카드 선택
6. 응원 문장 작성
7. session.status가 reply_created인지 확인
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
