# 05. API Spec

## 1. 공통 규칙

## 1.1 Base URL

```txt
Local API: http://localhost:8000/api
```

## 1.2 응답 형식

성공 응답은 리소스별 JSON을 반환한다.

에러 응답은 다음 형식을 사용한다.

```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "세션을 찾을 수 없습니다.",
    "details": {}
  }
}
```

## 1.3 공통 에러 코드

```txt
BAD_REQUEST
UNAUTHORIZED
FORBIDDEN
EVENT_NOT_FOUND
EVENT_NOT_OPEN
SESSION_NOT_FOUND
INVALID_SESSION_STATUS
CONSENT_REQUIRED
QUESTIONS_NOT_COMPLETED
CARD_NOT_FOUND
REPLY_NOT_FOUND
COMPLETION_CODE_NOT_FOUND
COMPLETION_CODE_ALREADY_REDEEMED
RATE_LIMITED
INTERNAL_ERROR
```

## 1.4 인증

참가자 API는 회원 인증을 사용하지 않는다. `sessionId`와 `resumeToken` 기반으로 세션을 복구한다.

관리자 API는 JWT Bearer Token을 사용한다.

```txt
Authorization: Bearer <admin_access_token>
```

## 1.5 Idempotency

다음 API는 중복 호출에 안전해야 한다.

```txt
- 세션 생성/복구
- 동의 저장
- 응답 bulk 저장
- 점수화 실행
- 요약 조회
- 완료 코드 발급
- 상품 지급 처리
```

가능하면 `Idempotency-Key` 헤더를 지원한다.

```txt
Idempotency-Key: uuid-or-client-generated-key
```

## 2. Public Event API

## 2.1 이벤트 공개 설정 조회

```http
GET /api/events/{eventSlug}/public
```

응답:

```json
{
  "event": {
    "slug": "fire-expo-2026",
    "name": "마음나무",
    "status": "open",
    "description": "소방안전박람회 마음점검 이벤트",
    "consentVersion": "v1",
    "settings": {
      "displayEnabled": true,
      "maxMindCardsPerSession": 3,
      "helpNoticeEnabled": true
    }
  },
  "notices": {
    "notDiagnosis": "본 이벤트는 진단이나 치료가 아닌 체험형 마음 점검입니다.",
    "anonymousKeywordDisplay": "TV에는 원문이 아닌 익명 키워드만 표시됩니다."
  }
}
```

## 3. Session API

## 3.1 익명 세션 생성 또는 복구

```http
POST /api/events/{eventSlug}/sessions
```

요청:

```json
{
  "resumeToken": "client-generated-token-if-exists",
  "clientMeta": {
    "device": "mobile",
    "timezone": "Asia/Seoul"
  }
}
```

응답:

```json
{
  "session": {
    "id": "uuid",
    "eventSlug": "fire-expo-2026",
    "status": "created",
    "lastStep": "landing"
  },
  "resumeToken": "new-client-resume-token"
}
```

구현 기준:

```txt
- resumeToken이 없으면 새 세션을 만든다.
- resumeToken이 있으면 hash를 기준으로 기존 세션을 찾는다.
- DB에는 원문 resumeToken을 저장하지 않는다.
```

## 3.2 세션 상태 조회

```http
GET /api/sessions/{sessionId}
```

응답:

```json
{
  "session": {
    "id": "uuid",
    "eventSlug": "fire-expo-2026",
    "status": "summary_viewed",
    "lastStep": "cards/new",
    "completedAt": null
  },
  "progress": {
    "consentAccepted": true,
    "questionsCompleted": true,
    "summaryViewed": true,
    "mindCardCount": 1,
    "selectedCard": false,
    "replyCreated": false,
    "completionCodeIssued": false
  }
}
```

## 3.3 필수 동의 저장

```http
POST /api/sessions/{sessionId}/consent
```

요청:

```json
{
  "consentVersion": "v1",
  "acceptedItems": {
    "eventIsNotDiagnosis": true,
    "anonymousKeywordDisplay": true,
    "cardMayBeShownAnonymously": true,
    "noIdentifyingInfo": true,
    "adminModeration": true
  }
}
```

응답:

```json
{
  "sessionStatus": "consented",
  "acceptedAt": "2026-05-13T09:00:00Z"
}
```

## 4. Question and Answer API

## 4.1 문항 전체 조회

```http
GET /api/events/{eventSlug}/questions
```

응답:

```json
{
  "questions": [
    {
      "id": "uuid",
      "questionNo": 14,
      "scaleCode": "phq9",
      "questionKey": "phq9_01",
      "title": "지난 2주 동안 ...",
      "description": null,
      "questionType": "likert",
      "required": true,
      "displayOrder": 14,
      "options": [
        { "label": "전혀 아니다", "value": 0 },
        { "label": "며칠 동안", "value": 1 },
        { "label": "일주일 이상", "value": 2 },
        { "label": "거의 매일", "value": 3 }
      ]
    }
  ]
}
```

구현 기준:

```txt
- 참가자 진입 초기에 전체 문항을 한 번에 선로딩한다.
- 프론트엔드는 questionNo 또는 displayOrder 기준으로 렌더링한다.
- 점수화 기준은 프론트가 아니라 서버가 가진 score_map과 scoring service를 기준으로 한다.
```

## 4.2 응답 bulk 저장

```http
PUT /api/sessions/{sessionId}/answers/bulk
```

요청:

```json
{
  "answers": [
    {
      "questionId": "uuid",
      "answerValue": 2
    },
    {
      "questionId": "uuid",
      "answerValue": "firefighter"
    }
  ],
  "clientProgress": {
    "lastQuestionNo": 77
  }
}
```

응답:

```json
{
  "savedCount": 77,
  "sessionStatus": "questions_completed",
  "scoring": {
    "calculated": true,
    "scaleScores": [
      { "scaleCode": "phq9", "rawScore": 8, "severityLevel": "mild" }
    ],
    "riskFlags": {
      "phq9Item9Positive": false,
      "crisisExpressionDetected": false,
      "publicRestriction": false,
      "helpNoticeRequired": false
    }
  }
}
```

구현 기준:

```txt
- 같은 sessionId/questionId 조합은 upsert한다.
- 전체 필수 문항이 충족되면 점수화와 위험 플래그 계산을 실행한다.
- 부분 저장이 필요한 경우 savedCount와 missingQuestionNos를 반환한다.
```

## 5. Summary API

## 5.1 마음신호 요약 조회

```http
GET /api/sessions/{sessionId}/summary
```

응답:

```json
{
  "summary": {
    "finalText": "최근 마음에 긴장 신호가 나타납니다. 지금은 스스로를 다그치기보다 회복을 위한 작은 행동이 필요할 수 있습니다.",
    "generationMode": "template",
    "helpNoticeRequired": false
  },
  "riskNotice": {
    "showHelpNotice": false,
    "text": null
  }
}
```

구현 기준:

```txt
- LLM이 비활성화되어도 템플릿 요약은 항상 제공한다.
- LLM 보정이 늦으면 템플릿 요약을 먼저 반환한다.
- 요약은 진단명이나 확정적 판단을 포함하지 않는다.
```

## 5.2 요약 확인 처리

```http
POST /api/sessions/{sessionId}/summary/viewed
```

응답:

```json
{
  "sessionStatus": "summary_viewed",
  "viewedAt": "2026-05-13T09:00:00Z"
}
```

## 6. Mind Card API

## 6.1 마음카드 작성

```http
POST /api/sessions/{sessionId}/cards
```

요청:

```json
{
  "promptType": "to_now_me",
  "content": "오늘은 조금 쉬어가도 괜찮다."
}
```

응답:

```json
{
  "card": {
    "id": "uuid",
    "promptType": "to_now_me",
    "content": "오늘은 조금 쉬어가도 괜찮다.",
    "safetyStatus": "safe",
    "publicStatus": "public"
  },
  "keywordJob": {
    "id": "uuid",
    "status": "pending"
  },
  "sessionStatus": "card_created"
}
```

구현 기준:

```txt
- 안전 필터를 즉시 적용한다.
- safe이면 public 가능, review/exclude이면 공개 제한한다.
- keyword job을 생성하지만 참가자를 기다리게 하지 않는다.
```

## 6.2 공개 가능한 타인 카드 조회

```http
GET /api/events/{eventSlug}/cards/public?excludeSessionId={sessionId}&limit=10
```

응답:

```json
{
  "cards": [
    {
      "id": "uuid",
      "promptType": "to_colleague",
      "content": "당신의 하루가 누군가에게 큰 힘이 됩니다.",
      "createdAt": "2026-05-13T09:00:00Z"
    }
  ],
  "fallbackUsed": false
}
```

구현 기준:

```txt
- 자기 카드 제외
- safety_status = safe
- public_status = public
- 공개 카드가 부족하면 seed card 또는 fallback 안내를 반환할 수 있다.
```

## 6.3 타인 카드 선택 저장

```http
POST /api/sessions/{sessionId}/selected-card
```

요청:

```json
{
  "selectedCardId": "uuid"
}
```

응답:

```json
{
  "selectedCardId": "uuid",
  "selectedAt": "2026-05-13T09:00:00Z"
}
```

## 7. Reply API

## 7.1 응원·공감·작은 대처법 작성

```http
POST /api/sessions/{sessionId}/replies
```

요청:

```json
{
  "targetCardId": "uuid",
  "replyType": "comfort",
  "content": "그 시간을 버틴 것만으로도 충분히 애쓰셨습니다."
}
```

응답:

```json
{
  "reply": {
    "id": "uuid",
    "replyType": "comfort",
    "safetyStatus": "safe",
    "publicStatus": "public"
  },
  "keywordJob": {
    "id": "uuid",
    "status": "pending"
  },
  "completion": {
    "eligible": true,
    "code": "TREE-7K2P9Q"
  },
  "sessionStatus": "completed"
}
```

구현 기준:

```txt
- 응원 문장 저장 후 keyword job을 생성한다.
- 완료 조건이 충족되면 완료 코드를 발급한다.
- 완료 코드는 세션당 1개만 발급한다.
```

## 8. Completion API

## 8.1 완료 코드 조회

```http
GET /api/sessions/{sessionId}/completion-code
```

응답:

```json
{
  "completionCode": {
    "code": "TREE-7K2P9Q",
    "status": "issued",
    "issuedAt": "2026-05-13T09:00:00Z"
  }
}
```

## 9. Display API

## 9.1 TV snapshot 조회

```http
GET /api/events/{eventSlug}/display/snapshot
```

응답:

```json
{
  "eventSlug": "fire-expo-2026",
  "participantCount": 124,
  "completedCount": 78,
  "topMindKeywords": [
    { "text": "긴장", "weight": 16 },
    { "text": "피로", "weight": 12 }
  ],
  "topSupportKeywords": [
    { "text": "쉼", "weight": 18 },
    { "text": "괜찮아", "weight": 11 }
  ],
  "cloudKeywords": [
    { "text": "쉼", "weight": 18, "category": "support" }
  ],
  "generatedAt": "2026-05-13T09:00:00Z"
}
```

## 9.2 TV SSE stream

```http
GET /api/events/{eventSlug}/stream
```

SSE event 예시:

```txt
event: keyword_snapshot
data: {"eventSlug":"fire-expo-2026","participantCount":124,"cloudKeywords":[{"text":"쉼","weight":18,"category":"support"}],"generatedAt":"2026-05-13T09:00:00Z"}
```

구현 기준:

```txt
- 연결 직후 최신 snapshot을 보낸다.
- 일정 주기 또는 키워드 변경 시 snapshot을 보낸다.
- 클라이언트는 연결 끊김 시 자동 재연결한다.
- 재연결 중에도 마지막 snapshot을 유지한다.
```

## 10. Admin Auth API

## 10.1 관리자 로그인

```http
POST /api/admin/auth/login
```

요청:

```json
{
  "email": "operator@example.com",
  "password": "password"
}
```

응답:

```json
{
  "accessToken": "jwt",
  "tokenType": "bearer",
  "admin": {
    "id": "uuid",
    "email": "operator@example.com",
    "displayName": "운영자",
    "role": "operator"
  }
}
```

## 11. Admin Event API

## 11.1 관리자 대시보드

```http
GET /api/admin/events/{eventSlug}/dashboard
```

응답:

```json
{
  "event": {
    "slug": "fire-expo-2026",
    "status": "open"
  },
  "metrics": {
    "sessionCount": 124,
    "completedCount": 78,
    "cardCount": 82,
    "replyCount": 76,
    "reviewCount": 5,
    "keywordPendingCount": 12,
    "keywordFailedCount": 2,
    "redeemedCount": 40
  }
}
```

## 12. Admin Review API

## 12.1 마음카드 검수 목록

```http
GET /api/admin/events/{eventSlug}/cards?status=review
```

응답:

```json
{
  "items": [
    {
      "id": "uuid",
      "contentRaw": "...",
      "contentRedacted": null,
      "safetyStatus": "review",
      "publicStatus": "pending",
      "moderationReason": "personal_info_detected",
      "createdAt": "2026-05-13T09:00:00Z"
    }
  ]
}
```

## 12.2 마음카드 검수 처리

```http
PATCH /api/admin/cards/{cardId}/review
```

요청:

```json
{
  "safetyStatus": "safe",
  "publicStatus": "public",
  "contentRedacted": "수정된 공개 문장",
  "reason": "개인 식별 가능 표현 제거"
}
```

응답:

```json
{
  "card": {
    "id": "uuid",
    "safetyStatus": "safe",
    "publicStatus": "public"
  },
  "auditLogCreated": true
}
```

## 12.3 응원 문장 검수 목록

```http
GET /api/admin/events/{eventSlug}/replies?status=review
```

## 12.4 응원 문장 검수 처리

```http
PATCH /api/admin/replies/{replyId}/review
```

요청과 응답은 마음카드 검수 처리와 동일한 구조를 사용한다.

## 13. Admin Keyword API

## 13.1 키워드 목록 조회

```http
GET /api/admin/events/{eventSlug}/keywords?status=active
```

응답:

```json
{
  "items": [
    {
      "id": "uuid",
      "keywordText": "쉼",
      "normalizedKeyword": "쉼",
      "category": "support",
      "weight": 18,
      "status": "active",
      "extractionMethod": "fallback"
    }
  ]
}
```

## 13.2 키워드 수정/숨김

```http
PATCH /api/admin/keywords/{keywordId}
```

요청:

```json
{
  "normalizedKeyword": "휴식",
  "category": "recovery",
  "status": "active",
  "reason": "유사어 병합"
}
```

## 13.3 keyword job 목록 조회

```http
GET /api/admin/events/{eventSlug}/keyword-jobs?status=failed
```

응답:

```json
{
  "items": [
    {
      "id": "uuid",
      "sourceType": "mind_card",
      "sourceId": "uuid",
      "status": "failed",
      "attempts": 2,
      "fallbackUsed": true,
      "errorMessage": "LLM timeout",
      "createdAt": "2026-05-13T09:00:00Z"
    }
  ]
}
```

## 13.4 keyword job 재시도

```http
POST /api/admin/keyword-jobs/{jobId}/retry
```

응답:

```json
{
  "job": {
    "id": "uuid",
    "status": "pending",
    "attempts": 0
  },
  "auditLogCreated": true
}
```

## 14. Admin Reward API

## 14.1 완료 코드 조회

```http
GET /api/admin/events/{eventSlug}/completion-codes/{code}
```

응답:

```json
{
  "completionCode": {
    "code": "TREE-7K2P9Q",
    "status": "issued",
    "issuedAt": "2026-05-13T09:00:00Z",
    "redeemedAt": null
  }
}
```

## 14.2 상품 지급 처리

```http
POST /api/admin/events/{eventSlug}/completion-codes/{code}/redeem
```

요청:

```json
{
  "notes": "현장 부스 상품 지급"
}
```

응답:

```json
{
  "completionCode": {
    "code": "TREE-7K2P9Q",
    "status": "redeemed",
    "redeemedAt": "2026-05-13T09:00:00Z"
  },
  "auditLogCreated": true
}
```

이미 지급된 코드일 경우:

```json
{
  "error": {
    "code": "COMPLETION_CODE_ALREADY_REDEEMED",
    "message": "이미 지급 처리된 완료 코드입니다.",
    "details": {
      "redeemedAt": "2026-05-13T09:00:00Z"
    }
  }
}
```

## 15. Admin Audit API

## 15.1 감사 로그 조회

```http
GET /api/admin/events/{eventSlug}/audit-logs?limit=50
```

응답:

```json
{
  "items": [
    {
      "id": "uuid",
      "adminUserId": "uuid",
      "action": "completion_code.redeem",
      "targetType": "completion_code",
      "targetId": "uuid",
      "reason": "현장 부스 상품 지급",
      "createdAt": "2026-05-13T09:00:00Z"
    }
  ]
}
```

## 16. 세션 상태 전이 규칙

```txt
created
→ consented
→ questions_completed
→ summary_viewed
→ card_created
→ reply_created
→ completed
```

상태 전이 조건:

```txt
created → consented:
- 필수 동의 저장 완료

consented → questions_completed:
- 필수 문항 응답 완료
- 점수화 완료
- 위험 플래그 계산 완료

questions_completed → summary_viewed:
- 마음신호 요약 확인 처리 완료

summary_viewed → card_created:
- 마음카드 1개 이상 저장 완료

card_created → reply_created:
- 타인 카드 선택 완료
- 응원/공감/작은 대처법 1개 이상 저장 완료

reply_created → completed:
- 완료 코드 발급 완료
```

## 17. API 구현 금지 사항

```txt
- 사용자 입력을 그대로 SQL 문자열에 삽입하지 않는다.
- 프론트엔드에서 점수화 결과를 최종값으로 믿지 않는다.
- LLM 응답을 위험도 또는 공개 여부 판단에 사용하지 않는다.
- TV API에서 원문 문장을 반환하지 않는다.
- 관리자 인증 없이 원문 조회 API를 제공하지 않는다.
- 실제 API key 또는 운영 secret을 응답이나 로그에 포함하지 않는다.
```

## 18. Question Seed JSON and Scoring Rule

문항과 척도별 절단점은 아래 JSON seed를 기준으로 한다.

```txt
docs/data/questions_fire_expo_2026.json
docs/data/scoring_rules_v1.json
```

Phase 04 구현 시 Codex는 이 JSON을 읽어 `questions` 테이블을 seed한다.

Scoring rule version:

```txt
v2-2026-05-13-scale-cutoffs
```

척도별 severity code는 다음을 사용한다.

```txt
K-PHQ-9:
- no_specific_findings
- mild_depressive_symptoms
- moderate_depression_suspected
- severe_depression_score_range

K-PCL-5:
- normal_range
- threshold
- high_risk

K-MIES:
- low
- moderate
- high

K-SCS:
- low
- medium
- high
```

응답 bulk 저장 API는 점수화 완료 시 위 severity code를 `scaleScores[].severityLevel`에 반환할 수 있다. K-SCS의 `rawScore`는 합계가 아니라 역채점 후 평균값을 사용한다.

`riskFlags.details`에는 다음 보조 신호를 포함할 수 있다.

```txt
phq9HighInstabilitySignal
phq9SevereWithItem9
pcl5ThresholdSignal
kscsLevel
```

금지 사항:

```txt
- TV API에서 severityLevel, rawScore, riskFlags를 반환하지 않는다.
- 프론트엔드에서 점수화 결과를 최종 계산하지 않는다.
- LLM 응답으로 severityLevel 또는 riskFlags를 결정하지 않는다.
```
