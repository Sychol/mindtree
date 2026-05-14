# PHASE 10. 관리자 검수·키워드 상태·완료 코드·상품 지급

이 문서는 VS Code Codex에 그대로 붙여넣어 사용할 수 있는 Phase 작업 지시서다.  
모든 작업은 `docs/codex-common-rules.md`를 우선 기준으로 삼는다.


## 목표

현장 운영자가 사용할 관리자 기능을 구현한다.  
관리자는 카드/응원 검수, 위험 플래그 확인, 키워드 상태 확인과 숨김/재계산, 완료 코드 조회, 상품 지급 처리, 감사 로그 확인을 할 수 있어야 한다.

## 작업 전 확인 사항

```txt
- Phase 09까지 참가자/키워드/TV 흐름이 동작하는지 확인한다.
- docs/12-admin-policy.md를 반드시 읽는다.
- docs/13-security-privacy-policy.md의 관리자 권한과 감사 로그 기준을 확인한다.
- 관리자 API는 JWT Bearer 인증을 적용한다는 기준을 확인한다.
```

## 참조 문서

```txt
- docs/codex-common-rules.md
- docs/04-data-model.md
- docs/05-api-spec.md
- docs/06-frontend-structure.md
- docs/07-backend-structure.md
- docs/09-scoring-risk-policy.md
- docs/10-llm-keyword-policy.md
- docs/11-tv-display-policy.md
- docs/12-admin-policy.md
- docs/13-security-privacy-policy.md
```

## 수정 또는 생성할 파일

```txt
api/app/
├── api/routes/admin_auth.py
├── api/routes/admin_events.py
├── api/routes/admin_moderation.py
├── api/routes/admin_keywords.py
├── api/routes/admin_rewards.py
├── schemas/admin.py
├── services/admin_auth.py
├── services/admin_moderation.py
├── services/admin_keywords.py
├── services/rewards.py
├── services/audit_log.py
├── repositories/admin_users.py
├── repositories/admin_audit_logs.py
├── repositories/completion_codes.py
└── repositories/admin_queries.py

api/tests/
├── test_admin_auth.py
├── test_admin_moderation.py
├── test_admin_keywords.py
├── test_admin_rewards.py
└── test_admin_audit_logs.py

web/src/
├── api/admin.ts
├── routes/AdminRoutes.tsx
├── pages/admin/AdminLoginPage.tsx
├── pages/admin/AdminDashboardPage.tsx
├── pages/admin/AdminCardsPage.tsx
├── pages/admin/AdminRepliesPage.tsx
├── pages/admin/AdminKeywordsPage.tsx
├── pages/admin/AdminRewardsPage.tsx
├── components/admin/ModerationTable.tsx
├── components/admin/KeywordJobStatusBadge.tsx
├── components/admin/RewardCodeLookup.tsx
└── state/adminAuth.ts
```

## 구현 내용

### 1. 관리자 인증

구현 endpoint 예시:

```http
POST /api/admin/auth/login
GET /api/admin/auth/me
```

구현 기준:

```txt
- 관리자 API는 JWT Bearer Token을 사용한다.
- 비밀번호는 hash로 저장한다.
- 운영 secret은 환경변수로 관리한다.
- 기본 admin 계정은 개발 seed 또는 bootstrap script로만 만든다.
- 코드에 기본 운영 비밀번호를 넣지 않는다.
```

권장 bootstrap:

```txt
- ADMIN_BOOTSTRAP_EMAIL
- ADMIN_BOOTSTRAP_PASSWORD
```

값이 없으면 bootstrap을 실행하지 않는다.

### 2. 관리자 대시보드

구현 endpoint 예시:

```http
GET /api/admin/events/{eventSlug}/dashboard
```

표시 항목:

```txt
- 이벤트 상태
- 참여자 수
- 완료 수
- 검수 대기 카드 수
- 검수 대기 응원 수
- keyword job pending/failed 수
- 완료 코드 발급/지급 수
```

주의:

```txt
- 대시보드는 운영 요약만 제공한다.
- 복잡한 통계 대시보드는 MVP 범위가 아니다.
```

### 3. 마음카드·응원 문장 검수

구현 endpoint 예시:

```http
GET /api/admin/events/{eventSlug}/mind-cards
PATCH /api/admin/mind-cards/{cardId}/moderation
GET /api/admin/events/{eventSlug}/replies
PATCH /api/admin/replies/{replyId}/moderation
```

검수 상태:

```txt
safe
review
exclude
```

공개 상태:

```txt
public
hidden
excluded
pending
```

관리자 조치:

```txt
- 공개
- 숨김
- 수정 후 공개
- 삭제 또는 제외
- 복구
```

구현 기준:

```txt
- 관리자 조치마다 admin_audit_logs를 남긴다.
- 수정 전/후를 과도하게 노출하지 않되, 감사 목적의 diff 또는 요약을 남길 수 있다.
- exclude 처리된 source의 키워드는 TV 집계에서 제외되도록 상태를 갱신한다.
```

### 4. 키워드와 job 상태 관리

구현 endpoint 예시:

```http
GET /api/admin/events/{eventSlug}/keywords
PATCH /api/admin/keywords/{keywordId}
GET /api/admin/events/{eventSlug}/keyword-jobs
POST /api/admin/keyword-jobs/{jobId}/retry
```

관리자 화면 표시:

```txt
- 키워드 텍스트
- normalized_text
- category
- weight
- status
- extraction_method
- fallback_used
- source_type
- job status
- attempts
- error_message 축약
```

관리자 조치:

```txt
- 키워드 숨김
- 키워드 복구
- normalized_text 수정
- job 재처리
```

주의:

```txt
- 원문은 필요한 검수 화면에서만 제한적으로 표시한다.
- TV display API에는 원문을 계속 반환하지 않는다.
```

### 5. 완료 코드 발급과 상품 지급

완료 코드 발급 endpoint는 참가자 완료 흐름에 필요하다.

구현 endpoint 예시:

```http
POST /api/sessions/{sessionId}/completion-code
GET /api/admin/events/{eventSlug}/completion-codes/{code}
POST /api/admin/events/{eventSlug}/completion-codes/{code}/redeem
```

완료 코드 발급 조건:

```txt
- consent 완료
- questions_completed
- summary_viewed
- mind_card 1개 이상
- selected peer card 있음
- reply 1개 이상
```

구현 기준:

```txt
- 세션당 완료 코드 1개만 발급한다.
- 중복 호출은 기존 코드를 반환한다.
- redeem은 미지급 코드에 대해서만 가능하다.
- 이미 지급된 코드는 중복 지급하지 않는다.
- 지급 처리 시 admin_audit_logs를 남긴다.
- 완료 코드로 개인정보를 대체하며 이름/전화번호를 요구하지 않는다.
```

### 6. 관리자 프론트엔드

라우트 예시:

```txt
/admin/login
/admin/events/:eventSlug/dashboard
/admin/events/:eventSlug/cards
/admin/events/:eventSlug/replies
/admin/events/:eventSlug/keywords
/admin/events/:eventSlug/rewards
```

구현 기준:

```txt
- 로그인 후 token을 저장한다.
- 관리자 API 호출 시 Authorization header를 붙인다.
- 검수 테이블에서 상태 변경이 가능하다.
- 키워드 job 상태 badge를 표시한다.
- 완료 코드를 입력해 지급 여부를 조회하고 지급 처리할 수 있다.
```

### 7. 테스트

필수 테스트:

```txt
- 관리자 로그인 성공/실패
- 인증 없는 관리자 API 접근 실패
- 검수 상태 변경 시 카드/응원 상태 갱신
- 검수 상태 변경 시 audit log 생성
- keyword hide/retry 동작
- 완료 코드 조건 충족 시 발급
- 완료 코드 중복 발급 시 같은 코드 반환
- 지급 처리 후 redeemed 상태
- 중복 지급 요청 실패
- 지급 처리 audit log 생성
```

## 금지 사항

```txt
- 관리자 인증 없이 관리자 API를 열지 않는다.
- 코드에 기본 운영 비밀번호를 넣지 않는다.
- RAG 후보 승인/export 기능을 구현하지 않는다.
- 복잡한 기관형 통계 대시보드를 구현하지 않는다.
- 상담 라우팅이나 장기 사용자 히스토리를 구현하지 않는다.
- TV API에 원문을 추가하지 않는다.
```

## 완료 기준

```txt
- 관리자 로그인과 JWT 인증이 동작한다.
- 관리자 대시보드가 기본 운영 지표를 보여준다.
- 카드/응원 검수 상태를 변경할 수 있다.
- 키워드와 keyword job 상태를 확인하고 필요한 조치를 할 수 있다.
- 완료 코드 발급, 조회, 지급, 중복 지급 방지가 동작한다.
- 관리자 주요 행위가 audit log에 기록된다.
- 관련 테스트가 통과한다.
```

## 테스트 방법

```bash
cd api
pytest tests/test_admin_auth.py tests/test_admin_moderation.py tests/test_admin_keywords.py tests/test_admin_rewards.py tests/test_admin_audit_logs.py
```

프론트엔드:

```bash
cd web
npm run build
npm run test -- --run
```

수동 확인:

```txt
1. 관리자 계정 bootstrap
2. /admin/login 접속 후 로그인
3. dashboard 확인
4. 검수 대기 카드 상태 변경
5. keyword job failed 항목 retry
6. 참가자 완료 코드 조회
7. 지급 처리 후 중복 지급 방지 확인
8. audit log 확인
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
