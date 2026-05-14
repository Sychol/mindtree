# 11. TV Display Policy

## 1. 목적

이 문서는 부스 현장 TV에 표시되는 마음나무 화면의 데이터 범위, 화면 구성, SSE 연결, 장애 대응 기준을 정의한다.

TV 화면은 공용 디스플레이이므로 공개 범위를 가장 엄격하게 관리한다.

```txt
TV의 역할:
- 참가자들이 남긴 마음카드와 응원 문장에서 추출된 익명 키워드를 나무 잎 형태 워드클라우드로 보여준다.
- 현장 참여감을 만든다.
- 개인 결과, 원문, 점수, 위험 정보를 절대 보여주지 않는다.
```

## 2. 라우트

```txt
/display/:eventSlug
```

TV는 React 앱의 별도 라우트로 운영한다. 운영자는 현장 TV 또는 노트북 브라우저에서 해당 URL을 띄운다.

후속 보안이 필요하면 다음 중 하나를 추가할 수 있다.

```txt
- display 전용 token
- 현장 네트워크 제한
- reverse proxy basic auth
```

MVP에서는 우선 URL 기반 표시로 시작할 수 있다.

## 3. 표시 가능 데이터

TV에는 다음만 표시한다.

```txt
- 전체 참여자 수
- 완료자 수 또는 참여 흐름 수치
- 마음신호 키워드 TOP 5
- 응원·회복 키워드 TOP 5
- 나무 잎 형태 워드클라우드
- 본 이벤트는 진단이나 치료가 아닌 체험이라는 안내문
- TV에는 원문이 아닌 익명 키워드만 표시된다는 안내문
- 연결 상태 안내
```

## 4. 표시 금지 데이터

TV에는 다음을 표시하지 않는다.

```txt
- 참가자 개인 결과
- 척도 점수
- 위험 플래그
- 마음카드 원문
- 응원 문장 원문
- content_raw
- content_redacted
- session_id
- resumeToken
- 완료 코드
- 관리자 검수 상태
- 위기 표현
- 개인정보 또는 식별 가능한 사건 정보
```

Display API도 위 데이터를 반환하지 않아야 한다.

## 5. 화면 구성

권장 레이아웃:

```txt
┌────────────────────────────────────────────┐
│ 마음나무                                  │
│ 오늘 남겨진 마음의 잎들이 자라고 있습니다 │
├──────────────────────────────┬─────────────┤
│                              │ 참여자 수   │
│                              │ 완료자 수   │
│        Tree Word Cloud       │             │
│                              │ 마음신호 TOP│
│                              │ 응원회복 TOP│
├──────────────────────────────┴─────────────┤
│ 본 이벤트는 진단이나 치료가 아닌 체험입니다 │
│ TV에는 원문이 아닌 익명 키워드만 표시됩니다 │
└────────────────────────────────────────────┘
```

## 6. Word Cloud 정책

### 6.1 형태

```txt
- 나무 또는 잎 형태를 연상시키는 배치
- 키워드는 잎처럼 분산 배치
- 너무 빠른 애니메이션은 피함
- 현장 TV에서 3~5m 거리에서도 읽을 수 있는 크기 사용
```

### 6.2 키워드 수

권장값:

```txt
cloudKeywords max: 40
rankingKeywords max: 5 per category
minWeight: 1
```

키워드가 너무 적으면 seed 또는 empty state를 사용한다.

```txt
아직 마음나무가 자라는 중입니다.
첫 번째 잎을 남겨보세요.
```

### 6.3 Weight 처리

```txt
- normalized_keyword 기준 집계
- weight가 높을수록 큰 글자
- 과도한 크기 차이는 제한
- hidden/excluded 키워드는 제외
```

## 7. Display Snapshot

초기 진입 시 snapshot API를 호출한다.

```http
GET /api/events/{eventSlug}/display/snapshot
```

응답은 원문 없는 집계 데이터만 포함한다.

```json
{
  "eventSlug": "fire-expo-2026",
  "participantCount": 124,
  "completedCount": 78,
  "topMindKeywords": [
    { "text": "긴장", "weight": 16 }
  ],
  "topSupportKeywords": [
    { "text": "쉼", "weight": 18 }
  ],
  "cloudKeywords": [
    { "text": "쉼", "weight": 18, "category": "support" }
  ],
  "generatedAt": "2026-05-13T09:00:00Z"
}
```

## 8. SSE Stream

SSE endpoint:

```http
GET /api/events/{eventSlug}/stream
```

SSE event 예시:

```txt
event: keyword_snapshot
data: {"eventSlug":"fire-expo-2026","participantCount":124,"cloudKeywords":[{"text":"쉼","weight":18,"category":"support"}],"generatedAt":"2026-05-13T09:00:00Z"}
```

권장 이벤트:

```txt
keyword_snapshot:
- 최신 TV snapshot

heartbeat:
- 연결 유지 확인용
```

## 9. SSE 재연결 정책

TV 네트워크는 끊길 수 있다. 화면은 빈 상태가 되면 안 된다.

프론트엔드 기준:

```txt
1. EventSource 연결
2. 연결 성공 시 connected 표시
3. message 수신 시 lastSnapshot 업데이트
4. error 발생 시 reconnecting 표시
5. 마지막 snapshot은 계속 화면에 유지
6. EventSource 자동 재연결 또는 수동 재생성
7. 장시간 실패 시 polling fallback
```

표시 문구는 작고 방해되지 않게 둔다.

```txt
연결 재시도 중입니다. 마지막 데이터를 표시하고 있습니다.
```

## 10. Polling Fallback

SSE가 장시간 실패하면 polling fallback을 사용할 수 있다.

```txt
조건:
- SSE error가 연속 발생
- 일정 시간 이상 새 snapshot 없음

동작:
- GET /display/snapshot을 10~30초 간격으로 호출
- SSE 복구 시 polling 중단
```

Polling fallback은 MVP 필수는 아니지만 현장 안정성 측면에서 권장한다.

## 11. TV 반영 지연 정책

TV 반영은 즉시성이 아니라 안정성을 우선한다.

```txt
마음카드/응원 저장:
참가자 즉시 다음 단계 이동

keyword job:
비동기 처리

TV 반영:
수 초~수십 초 지연 허용

LLM 실패:
fallback 키워드 또는 미반영
```

참가자가 완료했는데 TV에 바로 키워드가 보이지 않아도 정상이다.

## 12. 집계 제외 조건

다음 데이터는 TV 집계에서 제외한다.

```txt
- safety_status != safe
- public_status = hidden 또는 excluded
- keywords.status != active
- risk_flags.public_restriction = true
- crisis_expression_detected = true
- 개인정보 또는 사건 식별정보가 포함된 keyword
- 관리자에 의해 숨김 처리된 keyword
```

## 13. 관리자 변경 반영

관리자가 키워드를 숨기거나 수정하면 다음 중 하나로 TV에 반영한다.

```txt
- 다음 snapshot 주기 때 반영
- keyword 변경 후 즉시 snapshot broadcast
```

MVP에서는 단순 주기 갱신으로 충분하다. 단, 숨김/삭제는 가능한 빠르게 반영하는 것이 좋다.

## 14. 구현 파일 기준

```txt
web/src/pages/display/DisplayPage.tsx
web/src/components/display/TreeWordCloud.tsx
web/src/components/display/KeywordRanking.tsx
web/src/components/display/DisplayConnectionStatus.tsx
web/src/hooks/useDisplayStream.ts
web/src/api/displayApi.ts

api/app/routers/display.py
api/app/services/display_service.py
api/app/repositories/keyword_repository.py
api/app/schemas/display.py
api/app/tests/test_display.py
```

## 15. 운영 체크

TV 화면을 행사 전 다음 조건으로 테스트한다.

```txt
- display snapshot 정상 표시
- SSE 연결 정상
- SSE 서버 재시작 후 자동 재연결
- 네트워크 차단 후 마지막 데이터 유지
- keyword hidden 처리 후 TV에서 제거
- 원문이 network response에 포함되지 않음
- 참가자 수와 TOP 키워드가 갱신됨
```

## 16. 금지 사항

```txt
- TV에 마음카드 원문을 표시하지 않는다.
- TV에 응원 문장 원문을 표시하지 않는다.
- TV에 척도 점수, 위험 플래그, 세션 정보를 표시하지 않는다.
- EventSource 오류 발생 시 화면을 초기화하지 않는다.
- LLM job pending 상태를 참가자 개인과 연결해 표시하지 않는다.
- 관리자 검수 상태를 TV에 표시하지 않는다.
- WebSocket을 MVP 구조로 임의 변경하지 않는다.
```
