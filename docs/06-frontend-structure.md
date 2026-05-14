# 06. Frontend Structure

## 1. 목적

이 문서는 마음나무 MVP의 프론트엔드 구현 기준을 정의한다. 프론트엔드는 하나의 React 앱 안에서 참가자 모바일 화면, TV 디스플레이 화면, 관리자 화면을 라우트로 분리한다.

프론트엔드의 핵심 목표는 다음이다.

```txt
- 참가자는 QR 접속 후 짧고 끊김 없이 완료 코드까지 도달한다.
- 이벤트 진입 시 1~77번 문항을 선로딩한다.
- 네트워크 실패 시 입력값을 잃지 않고 재시도할 수 있다.
- LLM 키워드 추출을 기다리지 않고 다음 단계로 이동한다.
- TV 화면은 SSE 연결이 끊겨도 마지막 데이터를 유지한다.
- 관리자 화면은 검수, 키워드 상태, 완료 코드 지급에 집중한다.
```

## 2. 고정 기술 스택

```txt
React
Vite
TypeScript
react-router-dom
Browser Fetch API 또는 얇은 API client wrapper
CSS Modules 또는 일반 CSS
```

MVP에서 다음은 도입하지 않는다.

```txt
- Next.js
- Redux, Zustand 등 대형 전역 상태 관리 라이브러리
- WebSocket 기반 TV 통신
- 모바일 네이티브 앱
- 복잡한 UI component framework 강제 도입
```

전역 상태는 최소화한다. 세션, 이벤트 설정, 문항 캐시, 관리자 인증 토큰 정도만 context 또는 custom hook으로 관리한다.

## 3. 권장 폴더 구조

```txt
web/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  src/
    main.tsx
    App.tsx
    router.tsx

    api/
      client.ts
      publicEventsApi.ts
      sessionsApi.ts
      questionsApi.ts
      answersApi.ts
      summariesApi.ts
      cardsApi.ts
      repliesApi.ts
      displayApi.ts
      adminAuthApi.ts
      adminReviewApi.ts
      adminKeywordsApi.ts
      adminRewardsApi.ts

    types/
      api.ts
      event.ts
      session.ts
      question.ts
      scoring.ts
      card.ts
      keyword.ts
      display.ts
      admin.ts

    lib/
      storage.ts
      routeGuards.ts
      validation.ts
      retry.ts
      date.ts
      errors.ts

    hooks/
      useEventBootstrap.ts
      useParticipantSession.ts
      useQuestionFlow.ts
      useRetryableSubmit.ts
      useDisplayStream.ts
      useAdminAuth.ts

    components/
      common/
        Button.tsx
        Input.tsx
        Textarea.tsx
        LoadingState.tsx
        ErrorState.tsx
        ProgressBar.tsx
        NoticeBox.tsx
      participant/
        ConsentPanel.tsx
        QuestionCard.tsx
        ScaleSection.tsx
        SummaryCard.tsx
        MindCardForm.tsx
        PublicCardPicker.tsx
        ReplyForm.tsx
        CompletionCodeBox.tsx
      display/
        TreeWordCloud.tsx
        KeywordRanking.tsx
        DisplayConnectionStatus.tsx
      admin/
        AdminLayout.tsx
        ReviewStatusBadge.tsx
        KeywordJobStatusBadge.tsx
        RewardCodeSearch.tsx

    pages/
      participant/
        EventLandingPage.tsx
        ConsentPage.tsx
        QuestionsPage.tsx
        SummaryPage.tsx
        MindCardNewPage.tsx
        PublicCardSelectPage.tsx
        ReplyNewPage.tsx
        CompletePage.tsx
        HelpPage.tsx
      display/
        DisplayPage.tsx
      admin/
        AdminLoginPage.tsx
        AdminDashboardPage.tsx
        AdminCardsPage.tsx
        AdminRepliesPage.tsx
        AdminKeywordsPage.tsx
        AdminKeywordJobsPage.tsx
        AdminRewardsPage.tsx
        AdminAuditLogsPage.tsx
```

## 4. 라우트 구조

### 4.1 참가자 라우트

```txt
/e/:eventSlug
/e/:eventSlug/consent
/e/:eventSlug/questions
/e/:eventSlug/summary
/e/:eventSlug/cards/new
/e/:eventSlug/cards/select
/e/:eventSlug/replies/new
/e/:eventSlug/complete
/e/:eventSlug/help
```

참가자 라우트는 세션 상태를 기준으로 guard를 둔다. 프론트엔드 guard는 사용자 경험을 위한 보조 장치이며, 최종 상태 검증은 백엔드가 한다.

예시:

```txt
summary 페이지 접근 조건:
- session.status >= questions_completed

cards/new 페이지 접근 조건:
- session.status >= summary_viewed

complete 페이지 접근 조건:
- completion code가 발급되었거나 session.status = completed
```

### 4.2 TV 라우트

```txt
/display/:eventSlug
```

TV 화면은 다음 순서로 동작한다.

```txt
1. display snapshot 조회
2. snapshot을 화면에 즉시 표시
3. SSE EventSource 연결
4. keyword_snapshot event 수신 시 화면 갱신
5. SSE 연결 끊김 시 마지막 snapshot 유지
6. 자동 재연결 또는 polling fallback 수행
```

### 4.3 관리자 라우트

```txt
/admin/login
/admin/events/:eventSlug/dashboard
/admin/events/:eventSlug/cards
/admin/events/:eventSlug/replies
/admin/events/:eventSlug/keywords
/admin/events/:eventSlug/jobs
/admin/events/:eventSlug/rewards
/admin/events/:eventSlug/audit-logs
```

관리자 API는 JWT Bearer Token이 필요하다. 프론트엔드에서 토큰이 없어도 관리자 원문 데이터를 조회할 수 있는 우회 라우트를 만들지 않는다.

## 5. 참가자 Bootstrap 흐름

`/e/:eventSlug` 진입 시 다음을 수행한다.

```txt
1. eventSlug로 이벤트 공개 설정 조회
2. localStorage에서 resumeToken 조회
3. 세션 생성 또는 복구 요청
4. 1~77번 문항 전체 조회
5. 문항 설정을 메모리와 sessionStorage에 캐시
6. 백엔드 session.status와 lastStep 기준으로 다음 화면 이동
```

문항 설정은 공개 가능한 설정 데이터이므로 선로딩한다. 단, 참가자 응답값과 자유입력 원문은 민감 데이터로 간주한다.

## 6. 브라우저 저장 정책

### 6.1 localStorage

장기 복구가 필요한 최소 정보만 저장한다.

```txt
maeumnamu:{eventSlug}:resumeToken
maeumnamu:{eventSlug}:sessionId
```

원문 마음카드, 응원 문장, 위험 플래그, 점수 결과는 localStorage에 저장하지 않는다.

### 6.2 sessionStorage

탭 단위 임시 진행 상태를 저장한다.

```txt
maeumnamu:{eventSlug}:questionDraft
maeumnamu:{eventSlug}:currentQuestionNo
maeumnamu:{eventSlug}:questionsCache
```

사용 목적은 네트워크 실패와 새로고침 대응이다. 이벤트 완료 후 삭제한다.

### 6.3 메모리 상태

현재 화면 렌더링에 필요한 데이터는 React state 또는 custom hook 내부에서 관리한다.

```txt
- 현재 문항 index
- 현재 입력값
- submit loading 상태
- API error 상태
- SSE connection 상태
```

## 7. 문항 응답 UX

문항 페이지는 1~77번을 전부 한 화면에 노출하지 않는다. 섹션 단위 또는 단계 단위로 나눈다.

```txt
profile: 1~13
phq9: 14~22
pcl5: 23~42
kmies: 43~51
kscs: 52~77
```

구현 기준:

```txt
- 진행률을 표시한다.
- 뒤로 가기와 새로고침을 견딜 수 있어야 한다.
- 필수 문항 누락 시 서버 제출 전 클라이언트 검증을 한다.
- 최종 제출은 서버 bulk API를 호출한다.
- 제출 실패 시 입력값을 유지하고 재시도 버튼을 제공한다.
```

프론트엔드는 점수를 최종 계산하지 않는다. UI 안내용으로 임시 합계를 만들 수 있더라도 서버 점수화 결과를 최종값으로 사용한다.

## 8. 재시도 처리

`useRetryableSubmit` hook은 다음을 담당한다.

```txt
- 제출 중 중복 클릭 방지
- 네트워크 실패 시 error state 표시
- 재시도 버튼 제공
- 재시도 시 동일 payload 재전송
- 가능하면 Idempotency-Key 헤더 포함
```

예시 header:

```txt
Idempotency-Key: client-generated-uuid
```

프론트엔드가 중복 클릭을 막더라도 백엔드는 반드시 idempotent하게 처리해야 한다.

## 9. 마음카드와 응원 문장 UX

### 9.1 마음카드 작성

```txt
- promptType 선택
- 짧은 문장 작성
- 실명, 소속, 연락처, 구체적 사건명 입력 금지 안내
- 제출
- 안전 필터 결과에 따라 다음 단계 이동
```

안전 필터가 review 또는 exclude를 반환해도 참가자 흐름을 막지 않는다. 공개 여부만 제한한다.

### 9.2 타인 카드 선택

```txt
- 자기 카드 제외
- public 상태 카드만 표시
- 카드 부족 시 seed card 또는 안내 문구 표시
```

### 9.3 응원 문장 작성

```txt
replyType:
- comfort
- empathy
- small_coping
```

응원 문장 제출 후 keyword job 상태를 기다리지 않는다. 완료 조건이 충족되면 완료 코드 화면으로 이동한다.

## 10. 마음신호 요약 화면

요약 화면은 진단명이나 확정적 표현을 쓰지 않는다.

권장 문장 톤:

```txt
- 최근 마음에 긴장 신호가 나타납니다.
- 스스로를 다그치기보다 회복을 위한 작은 행동이 필요할 수 있습니다.
- 지금은 잠시 멈추고 도움을 요청할 수 있는 상태를 살펴보는 것이 좋습니다.
```

금지 표현:

```txt
- 우울증입니다.
- PTSD입니다.
- 위험합니다.
- 치료가 필요합니다.
- 반드시 상담을 받아야 합니다.
```

위험 플래그가 있는 경우 도움 안내를 노출하되, 공개 영역에는 전달하지 않는다.

## 11. TV Display 구현 기준

`useDisplayStream` hook은 다음 상태를 관리한다.

```txt
connectionStatus:
- connecting
- connected
- reconnecting
- polling
- disconnected

lastSnapshot:
- 마지막 정상 snapshot

lastUpdatedAt:
- 마지막 정상 수신 시각
```

SSE 이벤트 타입:

```txt
keyword_snapshot
heartbeat
```

TV 화면은 데이터가 없어도 빈 화면이 되면 안 된다.

```txt
- 초기 데이터 없음: 준비 중 안내와 빈 나무 표시
- 연결 끊김: 마지막 snapshot 유지
- 장시간 실패: 작은 연결 재시도 안내 표시
```

TV에는 원문, 점수, 세션 ID, 위험 플래그, 관리자 검수 상태를 표시하지 않는다.

## 12. 관리자 화면 구현 기준

관리자 화면은 운영 편의성을 우선한다.

```txt
Dashboard:
- 참여자 수
- 완료 수
- 검수 대기 수
- keyword job pending/failed 수
- 지급 완료 수

Cards:
- 마음카드 검수 목록
- safe/review/exclude 상태 변경
- contentRedacted 수정

Replies:
- 응원 문장 검수 목록
- 상태 변경

Keywords:
- 키워드 목록
- 숨김/수정/유사어 병합

Jobs:
- pending/processing/failed/retry_wait 목록
- 실패 job 재시도

Rewards:
- 완료 코드 조회
- 지급 처리
- 중복 지급 경고
```

관리자 원문 데이터는 필요한 화면에서만 표시하고, 일반 참가자 또는 TV API와 공유하지 않는다.

## 13. 프론트엔드 금지 사항

```txt
- 프론트엔드에서 최종 점수화 결과를 확정하지 않는다.
- 프론트엔드에서 위험 여부 또는 공개 여부를 최종 판단하지 않는다.
- 원문 마음카드와 응원 문장을 localStorage에 장기 저장하지 않는다.
- TV 화면에 원문, 점수, 위험 플래그, 세션 정보를 표시하지 않는다.
- 관리자 인증 없이 원문 조회 화면을 만들지 않는다.
- SSE 실패 시 화면을 빈 상태로 만들지 않는다.
- LLM job이 끝날 때까지 참가자를 대기시키지 않는다.
```

## 14. 완료 기준

프론트엔드 구현은 다음을 만족해야 한다.

```txt
- QR 진입부터 완료 코드까지 흐름이 연결된다.
- 1~77번 문항을 초기에 선로딩한다.
- 제출 실패 시 입력값이 유지되고 재시도가 가능하다.
- 세션 재접속 시 백엔드 status 기준으로 복구된다.
- TV SSE 연결이 끊겨도 마지막 데이터가 유지된다.
- 관리자 화면에서 검수, 키워드 job, 완료 코드 지급을 처리할 수 있다.
```
