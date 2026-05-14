# 13. Security and Privacy Policy

## 1. 목적

이 문서는 마음나무 MVP의 보안, 개인정보, 공개 제한, 관리자 권한, LLM 사용, 로그 정책을 정의한다.

마음나무는 부스 현장 공용 TV와 자유입력 문장이 포함된 이벤트 서비스다. 따라서 “수집 최소화, 공개 최소화, 관리자 접근 통제”를 기본 원칙으로 한다.

## 2. 기본 원칙

```txt
- 이름, 전화번호, 소속 등 직접 식별정보는 기본 수집하지 않는다.
- 참가자에게 식별 가능한 정보를 입력하지 말라고 안내한다.
- 원문 문장은 TV에 표시하지 않는다.
- TV에는 익명화·정제된 키워드만 표시한다.
- 위험 플래그와 척도 점수는 공개하지 않는다.
- 관리자 원문 접근은 운영 목적에 한정한다.
- 관리자 주요 행위는 감사 로그로 남긴다.
- 실제 API key와 secret은 코드에 넣지 않는다.
```

## 3. 동의와 안내

참가자 동의 화면에는 다음 내용을 포함한다.

```txt
- 본 이벤트는 진단이나 치료가 아닌 체험형 마음 점검입니다.
- 척도 응답은 개인 결과 요약과 익명 통계에 활용됩니다.
- 마음카드는 익명 상태로 다른 참가자에게 보일 수 있습니다.
- TV 화면에는 원문이 아니라 키워드만 표시됩니다.
- 실명, 소속, 연락처, 구체적 장소, 날짜, 사건명, 피해자 정보는 적지 않습니다.
- 관리자는 개인정보, 위기 표현, 부적절 표현이 포함된 문장을 수정·숨김·삭제할 수 있습니다.
```

MVP 동의 문구에는 `RAG`, `pgvector` 같은 내부 개발 용어를 노출하지 않는다.

## 4. 데이터 분류

### 4.1 공개 가능 데이터

```txt
- 정제된 익명 키워드
- 키워드 집계 수
- 전체 참여자 수
- 완료자 수
- 이벤트 안내 문구
```

### 4.2 제한 데이터

```txt
- 마음카드 원문
- 응원 문장 원문
- content_redacted
- 척도 응답
- 척도 점수
- 위험 플래그
- 세션 상태
- 완료 코드
```

제한 데이터는 관리자 인증 또는 참가자 본인 세션 복구 범위에서만 접근한다.

### 4.3 비저장 또는 해시 저장 데이터

```txt
- 원문 resumeToken: DB 저장 금지
- session key: 원문 저장 금지
- IP address: 필요 시 hash만 저장
- user agent: 필요 시 hash만 저장
```

## 5. 익명 세션 정책

```txt
- 참가자는 회원가입하지 않는다.
- 세션 복구는 resumeToken 기반으로 처리한다.
- DB에는 resume_token_hash만 저장한다.
- 중복 참여를 완전히 차단하기보다 완료 코드 중복 지급을 통제한다.
```

프론트엔드 localStorage에는 resumeToken과 sessionId만 저장한다. 문항 응답 draft는 sessionStorage에 임시 저장하고 완료 후 삭제한다.

## 6. 자유입력 안전 정책

마음카드와 응원 문장은 다음 필터를 통과해야 공개 가능하다.

```txt
- 개인정보 패턴
- 실명/소속/연락처
- 구체적 사건명/장소/날짜
- 자해·자살·죽음 관련 직접 표현
- 욕설/혐오 표현
- 특정인 비난
- 의료적 단정 표현
```

안전 상태:

```txt
safe:
- 공개 가능
- keyword job 가능

review:
- 관리자 확인 필요
- 공개 보류

exclude:
- 공개 불가
- TV 키워드 반영 제외
```

## 7. TV 공개 제한

TV API와 화면은 다음 데이터를 반환하거나 표시하지 않는다.

```txt
- content_raw
- content_redacted
- 척도 응답
- 척도 점수
- 위험 플래그
- 세션 ID
- 완료 코드
- 관리자 검수 상태
- 위기 표현
```

TV snapshot response는 반드시 집계된 keyword object만 포함한다.

## 8. 관리자 접근 통제

```txt
- 관리자 API는 JWT Bearer Token 필요
- 관리자 비밀번호는 hash로 저장
- 관리자 계정 비활성화 가능
- 관리자 원문 조회는 필요한 화면에 한정
- 관리자 변경 행위는 audit log 기록
```

관리자 감사 로그는 다음을 포함한다.

```txt
admin_user_id
action
target_type
target_id
before_value
after_value
reason
created_at
```

## 9. API 보안

```txt
- CORS origin을 환경변수로 제한한다.
- 관리자 API와 public API를 router 수준에서 분리한다.
- 참가자 API는 sessionId만으로 원문 전체를 넓게 조회하지 못하게 한다.
- DB query는 repository function을 통해 수행한다.
- raw SQL이 필요하면 parameter binding을 사용한다.
- 요청 body 길이를 제한한다.
- 자유입력 글자 수를 제한한다.
```

권장 길이 제한:

```txt
mind_card.content: 300자 이내
reply.content: 300자 이내
admin reason: 500자 이내
```

## 10. Secret 관리

코드에 넣으면 안 되는 값:

```txt
- DATABASE_URL 운영 값
- SECRET_KEY
- ADMIN 초기 비밀번호
- LLM_API_KEY
- 외부 서비스 API key
```

`.env.example`에는 placeholder만 둔다.

```txt
LLM_API_KEY=replace-me
SECRET_KEY=replace-me
POSTGRES_PASSWORD=replace-me
```

## 11. LLM Privacy

LLM 호출 시 원문 전달을 최소화한다.

```txt
- content_redacted 우선 사용
- session_id 전달 금지
- 완료 코드 전달 금지
- 척도 점수 상세 전달 금지
- 개인정보가 감지된 텍스트는 LLM keyword 대상으로 사용하지 않음
```

LLM provider 로그 저장 정책은 운영 전 확인해야 한다. MVP 문서에는 실제 provider API key를 넣지 않는다.

## 12. 로그 정책

애플리케이션 로그에 남기면 안 되는 값:

```txt
- resumeToken 원문
- 자유입력 원문 전체
- 완료 코드 전체값
- LLM API key
- 관리자 비밀번호
- JWT token
```

남길 수 있는 값:

```txt
- request path
- status code
- error code
- eventSlug
- hashed session reference
- job id
- admin action type
```

완료 코드는 로그에 필요하면 일부 마스킹한다.

```txt
TREE-****-9Q
```

## 13. 데이터 보존과 파기

MVP에서는 보존 기간을 별도 운영 정책으로 확정해야 한다.

권장 기준:

```txt
- 이벤트 종료 후 검수와 정산 완료
- 운영 결과 분석 후 원문 보존 필요성 검토
- 불필요한 원문은 삭제 또는 비식별화
- 감사 로그는 별도 기간 보존
```

실제 운영 전 보존 기간, 파기 절차, 운영 책임자를 문서화한다.

## 14. 장애와 사고 대응

### 14.1 개인정보 노출 의심

```txt
1. 해당 카드/응원/키워드 hidden 또는 excluded 처리
2. TV snapshot 재생성
3. 관리자 audit log 확인
4. 원인 파악
5. 필요 시 운영 보고
```

### 14.2 TV에 부적절 키워드 노출

```txt
1. 관리자 키워드 hidden 처리
2. SSE 또는 snapshot 갱신 확인
3. keyword extraction rule 수정
4. fallback/LLM prompt 보완
```

### 14.3 관리자 계정 유출 의심

```txt
1. 계정 비활성화
2. SECRET_KEY/JWT 만료 정책 확인
3. 감사 로그 확인
4. 비밀번호 재설정
```

## 15. 구현 파일 기준

```txt
api/app/core/security.py
api/app/core/config.py
api/app/services/safety_filter_service.py
api/app/services/admin_auth_service.py
api/app/services/audit_service.py
api/app/routers/admin_auth.py
api/app/routers/display.py
web/src/lib/storage.ts
web/src/hooks/useAdminAuth.ts
```

## 16. 테스트 기준

```txt
- TV snapshot에 원문이 포함되지 않음
- 관리자 인증 없이 원문 API 접근 불가
- resumeToken 원문이 DB에 저장되지 않음
- 위험 표현 포함 문장은 public_status excluded 또는 pending
- 개인정보 패턴 포함 문장은 review 또는 exclude
- 완료 코드 중복 지급 차단
- 로그에 JWT/API key/원문 token이 포함되지 않음
- LLM disabled mode에서도 정상 완료 가능
```

## 17. 금지 사항

```txt
- 직접 식별정보를 기본 수집하지 않는다.
- TV에 원문이나 위험 플래그를 표시하지 않는다.
- 원문 resumeToken을 DB나 로그에 저장하지 않는다.
- 실제 secret을 코드에 넣지 않는다.
- 관리자 인증 없는 원문 조회 API를 만들지 않는다.
- LLM에 공개 여부 판단을 맡기지 않는다.
- RAG 후보 활용 동의를 MVP 동의 문구에 내부 용어로 노출하지 않는다.
```
