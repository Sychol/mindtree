# 12. Admin Policy

## 1. 목적

이 문서는 마음나무 MVP의 관리자 기능, 검수 정책, 키워드 관리, 완료 코드 지급, 감사 로그 기준을 정의한다.

관리자의 목표는 다음이다.

```txt
- 현장 운영 상태를 확인한다.
- 공개 영역에 노출될 수 있는 문장을 안전하게 검수한다.
- 키워드와 keyword job 상태를 관리한다.
- 완료 코드 기준으로 상품 지급을 처리한다.
- 관리자 변경 행위를 감사 로그로 남긴다.
```

MVP 관리자는 RAG 후보 승인, 데이터 export, 기관형 통계가 아니라 현장 운영 안정성에 집중한다.

## 2. 관리자 역할

권장 role:

```txt
owner:
- 모든 관리자 기능 접근
- 관리자 계정 관리 가능

operator:
- 대시보드, 검수, 키워드, 완료 코드 지급 가능

reviewer:
- 카드/응원 검수와 키워드 검토 가능
```

MVP에서는 세분화가 부담되면 `operator` 단일 역할로 시작할 수 있다. 단, 관리자 API는 인증이 필요해야 한다.

## 3. 관리자 라우트

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

## 4. 대시보드

Dashboard에서 표시할 최소 지표:

```txt
- 이벤트 상태
- 전체 세션 수
- 완료 세션 수
- 마음카드 수
- 응원 문장 수
- 검수 대기 수
- keyword job pending 수
- keyword job failed 수
- 완료 코드 발급 수
- 상품 지급 완료 수
```

복잡한 통계 차트는 MVP에서 제외한다.

## 5. 마음카드 검수 정책

### 5.1 상태

```txt
safety_status:
- safe
- review
- exclude

public_status:
- pending
- public
- hidden
- excluded
```

### 5.2 자동 처리 기준

```txt
safe:
- 자동 공개 가능
- keyword job 생성 가능

review:
- 관리자 확인 필요
- 참가자 흐름은 계속 진행
- TV 키워드 반영은 보류 가능

exclude:
- 공개 불가
- TV 키워드 반영 제외
- 관리자 검수 대상
```

### 5.3 관리자 조치

```txt
- 공개
- 숨김
- 수정 후 공개
- 삭제 또는 제외
- 복구
- 키워드 재계산
```

`수정 후 공개`는 원문 자체를 바꾸는 것이 아니라 공개용 `content_redacted`를 만드는 방식이 우선이다.

## 6. 응원 문장 검수 정책

응원 문장도 마음카드와 같은 검수 상태를 사용한다.

검수 주의 대상:

```txt
- 개인정보
- 실명/소속/연락처
- 구체적 사건명/장소/날짜
- 자해·자살·죽음 관련 직접 표현
- 욕설/혐오/비난
- 특정 개인 공격
- 의료적 단정 표현
```

MVP에서 응원 문장 원문은 TV에 표시하지 않는다. 키워드만 반영할 수 있다.

## 7. 위험 플래그 확인

관리자는 위험 플래그가 있는 세션 또는 문장을 확인할 수 있다.

표시 기준:

```txt
- phq9_item9_positive
- crisis_expression_detected
- trauma_high_signal
- moral_injury_high_signal
- public_restriction
- help_notice_required
```

주의:

```txt
- 위험 플래그는 공개 화면에 표시하지 않는다.
- 위험 플래그가 있어도 참가자 완료와 상품 지급을 자동 차단하지 않는다.
- 관리자는 공개 제한과 필요 시 현장 안내를 위해 확인한다.
```

## 8. 키워드 관리

관리자 키워드 화면의 기능:

```txt
- 키워드 목록 조회
- category 확인
- normalized_keyword 확인
- extraction_method 확인
- 키워드 숨김
- normalized_keyword 수정
- category 수정
- 유사어 병합
- 키워드 재계산
```

키워드 상태:

```txt
active:
- TV 집계 가능

hidden:
- TV 집계 제외

excluded:
- 부적절하거나 정책상 제외
```

관리자 수정은 audit log에 남긴다.

## 9. Keyword Job 관리

관리자는 LLM/keyword job 상태를 볼 수 있어야 한다.

표시 상태:

```txt
pending
processing
succeeded
failed
retry_wait
fallback_used
```

운영자가 확인해야 할 항목:

```txt
- 대기 중인 job 수
- 실패한 job 수
- fallback 사용 비율
- source_type
- attempts
- error_message
- created_at
- updated_at
```

관리자 조치:

```txt
- failed job 재시도
- source 검수 후 재계산
- 특정 source의 키워드 제외
```

## 10. 상품 지급 정책

상품 지급은 완료 코드 기준으로 처리한다.

```txt
참가자가 완료 코드 제시
→ 운영자가 코드 검색
→ 코드가 issued 상태인지 확인
→ 지급 처리
→ status = redeemed
→ redeemed_at, redeemed_by 기록
→ audit log 기록
```

중복 지급 처리:

```txt
이미 redeemed 상태:
- 지급 불가
- redeemed_at 표시
- 이전 지급 관리자 표시 가능
```

개인정보 없이 운영 가능해야 한다. 이름, 전화번호, 소속을 요구하지 않는다.

## 11. 완료 코드 화면 정책

관리자 rewards 화면은 다음만 제공한다.

```txt
- 코드 입력
- 조회 버튼
- 코드 상태
- 발급 시각
- 지급 시각
- 지급 처리 버튼
- 운영 메모
```

참가자 원문이나 점수는 완료 코드 조회 화면에 노출하지 않는다.

## 12. 감사 로그

다음 행위는 audit log를 남긴다.

```txt
card.publish
card.hide
card.edit
card.delete
reply.publish
reply.hide
reply.edit
reply.delete
keyword.hide
keyword.edit
keyword.recalculate
keyword_job.retry
completion_code.redeem
completion_code.void
admin.login_failed
```

감사 로그 필드:

```txt
admin_user_id
event_id
action
target_type
target_id
before_value
after_value
reason
created_at
```

감사 로그는 관리자 화면에서 조회 가능하되 수정/삭제하지 않는다.

## 13. Seed Card 정책

이벤트 초기에는 공개 가능한 마음카드가 부족할 수 있다.

운영자는 seed card를 등록할 수 있다.

```txt
- 짧고 일반적인 응원 문장
- 개인정보 없음
- 특정 사건 없음
- 위기 표현 없음
- 진단/치료 표현 없음
```

Seed card는 일반 참가자의 카드와 구분 가능한 source를 둘 수 있다. TV 키워드 집계에 포함할지는 이벤트 설정으로 제어한다.

## 14. 관리자 API 보안

```txt
- JWT Bearer Token 사용
- 비밀번호 hash 저장
- 관리자 비활성화 가능
- 원문 조회 API는 관리자 인증 필수
- CORS 설정 제한
- 실패 로그인 rate limit 권장
- 운영 secret 코드 삽입 금지
```

## 15. 구현 파일 기준

```txt
web/src/pages/admin/AdminLoginPage.tsx
web/src/pages/admin/AdminDashboardPage.tsx
web/src/pages/admin/AdminCardsPage.tsx
web/src/pages/admin/AdminRepliesPage.tsx
web/src/pages/admin/AdminKeywordsPage.tsx
web/src/pages/admin/AdminKeywordJobsPage.tsx
web/src/pages/admin/AdminRewardsPage.tsx
web/src/pages/admin/AdminAuditLogsPage.tsx

api/app/routers/admin_auth.py
api/app/routers/admin_events.py
api/app/routers/admin_review.py
api/app/routers/admin_keywords.py
api/app/routers/admin_rewards.py
api/app/routers/admin_audit_logs.py
api/app/services/admin_auth_service.py
api/app/services/review_service.py
api/app/services/reward_service.py
api/app/services/audit_service.py
```

## 16. MVP 제외 관리자 기능

```txt
- RAG 후보 승인/반려
- RAG 데이터 export
- 기관별 장기 통계
- 상담 라우팅
- 고급 리포트 생성
- 관리자 실시간 알림 시스템
- 개인정보 기반 참가자 검색
```

## 17. 테스트 기준

```txt
- 관리자 로그인 성공/실패
- 인증 없이 관리자 API 접근 차단
- 마음카드 공개/숨김 처리
- 응원 문장 공개/숨김 처리
- 검수 처리 시 audit log 생성
- keyword hidden 후 TV snapshot 제외
- failed keyword job 재시도
- 완료 코드 조회
- 완료 코드 지급 처리
- 이미 지급된 코드 재지급 차단
- 지급 처리 audit log 생성
```

## 18. 금지 사항

```txt
- 관리자 인증 없이 원문을 반환하지 않는다.
- 완료 코드 조회 화면에 점수나 위험 플래그를 불필요하게 표시하지 않는다.
- 위험 플래그가 있다는 이유만으로 상품 지급을 자동 차단하지 않는다.
- 관리자 수정 이력을 로그 없이 처리하지 않는다.
- MVP에 RAG 승인/export 기능을 끼워 넣지 않는다.
- 개인정보 기반 운영 기능을 기본값으로 만들지 않는다.
```
