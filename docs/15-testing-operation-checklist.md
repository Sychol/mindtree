# 15. Testing and Operation Checklist

## 1. 목적

이 문서는 마음나무 MVP의 개발 테스트, 현장 리허설, 이벤트 당일 운영, 운영 후 점검 체크리스트를 정의한다.

마음나무는 박람회 현장 이벤트 서비스이므로 다음 상황을 정상 운영 조건으로 본다.

```txt
- 모바일 네트워크 지연
- 참가자 새로고침과 재접속
- 제출 실패와 재시도
- LLM 지연 또는 실패
- TV SSE 연결 끊김
- 관리자 검수 지연
- 완료 코드 중복 제시
```

## 2. 개발 테스트 범위

### 2.1 Backend Unit Test

```txt
- 세션 생성/복구
- 동의 저장
- 문항 응답 upsert
- 필수 문항 누락 검증
- 점수화 계산
- PHQ-9 item9 위험 플래그
- 자유입력 위기 표현 필터
- 템플릿 마음신호 요약
- 마음카드 저장 후 keyword job 생성
- 응원 문장 저장 후 completion code 발급
- fallback keyword extraction
- TV snapshot 원문 미포함
- 관리자 검수 audit log
- 완료 코드 중복 지급 방지
```

### 2.2 Frontend Test

```txt
- QR 진입 route 렌더링
- 이벤트 설정 조회 실패 처리
- 문항 선로딩 성공
- 문항 draft 유지
- 제출 실패 시 재시도 UI
- 세션 상태별 route guard
- TV SSE 연결 상태 표시
- 관리자 로그인 상태 처리
```

### 2.3 Integration Smoke Test

```txt
1. docker compose up --build
2. migration 실행
3. seed 실행
4. 참가자 플로우 완료
5. keyword job 처리 확인
6. TV display에 키워드 반영 확인
7. 관리자에서 완료 코드 지급 처리
```

## 3. 참가자 플로우 테스트

### 3.1 정상 완료

```txt
QR/URL 접속
→ 세션 생성
→ 동의
→ 1~77번 문항 응답
→ 서버 점수화
→ 마음신호 요약 확인
→ 마음카드 작성
→ 타인 카드 선택
→ 응원 문장 작성
→ 완료 코드 확인
```

완료 기준:

```txt
- session.status = completed
- completion_codes.status = issued
- 마음카드 또는 응원 문장에 keyword job 생성
- 참가자는 LLM job 완료를 기다리지 않음
```

### 3.2 새로고침 복구

테스트 지점:

```txt
- 동의 직후 새로고침
- 문항 응답 중 새로고침
- 요약 화면 새로고침
- 카드 작성 후 새로고침
- 완료 화면 새로고침
```

확인:

```txt
- resumeToken으로 세션 복구
- 백엔드 status 기준 화면 이동
- 완료 코드는 중복 발급되지 않음
```

### 3.3 제출 실패 재시도

시나리오:

```txt
- 문항 응답 완료 후 네트워크 차단
- 제출 버튼 클릭
- 실패 메시지 확인
- 입력값 유지 확인
- 네트워크 복구
- 재시도 성공 확인
```

동일하게 마음카드와 응원 문장 제출도 테스트한다.

## 4. 점수화와 위험 플래그 테스트

```txt
- 모든 필수 문항이 있으면 questions_completed 전이
- 필수 문항 누락 시 missingQuestionNos 반환
- PHQ-9 item9 score >= 1이면 phq9_item9_positive true
- 위기 표현 포함 자유입력은 public_restriction true
- public_restriction true인 source는 TV 집계 제외
- 위험 플래그가 있어도 완료 조건 충족 시 완료 코드 발급 가능
```

주의:

```txt
테스트 문장은 실제 참가자 데이터와 섞지 않는다.
위기 표현 테스트는 seed/test fixture로만 수행한다.
```


### 4.1 척도별 절단점 테스트

```txt
K-PHQ-9:
- 총점 0~4 → no_specific_findings
- 총점 5~9 → mild_depressive_symptoms
- 총점 10~19 → moderate_depression_suspected
- 총점 20~27 → severe_depression_score_range
- 총점 16 이상 → details.phq9_high_instability_signal true
- 22번 문항 item9 >= 1 → phq9_item9_positive, help_notice_required, public_restriction true

K-PCL-5:
- 총점 0~30 → normal_range
- 총점 31~33 → threshold + details.pcl5_threshold_signal true
- 총점 34~80 → high_risk + trauma_high_signal true

K-MIES:
- 총점 9~18 → low
- 총점 19~36 → moderate
- 총점 37~54 → high + moral_injury_high_signal true

K-SCS:
- global question no 53,54,56,57,59,65,66,70,71,74,76 역채점
- 역채점 공식 6 - answer_value 적용
- 평균 1.0~2.4 → low
- 평균 2.5~3.5 → medium
- 평균 3.6~5.0 → high
```

## 5. LLM / Keyword 테스트

### 5.1 LLM disabled mode

환경:

```txt
LLM_ENABLED=false
KEYWORD_FALLBACK_ENABLED=true
```

확인:

```txt
- 참가자 완료 가능
- 템플릿 요약 반환
- fallback 키워드 생성
- keyword_jobs.fallback_used = true
```

### 5.2 Mock mode

환경:

```txt
LLM_ENABLED=true
LLM_PROVIDER=mock
```

확인:

```txt
- deterministic 키워드 생성
- job status succeeded
- TV snapshot 반영
```

### 5.3 LLM 실패

시나리오:

```txt
- provider timeout 유도
- rate limit 또는 mock failure 유도
```

확인:

```txt
- 참가자 흐름 중단 없음
- fallback keyword 사용
- failed 또는 succeeded/fallback_used 상태가 관리자에 표시
- 관리자 재시도 가능
```

## 6. TV Display 테스트

### 6.1 표시 범위

Network response에서 다음이 없는지 확인한다.

```txt
content_raw
content_redacted
session_id
completion_code
risk_flags
scale_scores
admin status
```

### 6.2 SSE 연결

```txt
- /display/:eventSlug 접속
- initial snapshot 표시
- SSE keyword_snapshot 수신
- 새 키워드 생성 후 화면 갱신
```

### 6.3 자동 재연결

시나리오:

```txt
- API 컨테이너 재시작
- TV 브라우저는 켜둠
- 연결 재시도 표시 확인
- 마지막 데이터 유지 확인
- API 복구 후 최신 snapshot 수신 확인
```

### 6.4 Polling fallback

구현한 경우 확인한다.

```txt
- SSE 장시간 실패
- snapshot polling 시작
- SSE 복구 시 polling 중단
```

## 7. 관리자 테스트

### 7.1 인증

```txt
- 정상 로그인 성공
- 잘못된 비밀번호 실패
- 토큰 없이 관리자 API 접근 차단
- 비활성 계정 접근 차단
```

### 7.2 검수

```txt
- review 카드 목록 조회
- 카드 public 처리
- 카드 hidden 처리
- content_redacted 수정 후 공개
- 응원 문장 검수 처리
- 각 처리에 audit log 생성
```

### 7.3 키워드와 job

```txt
- keyword 목록 조회
- keyword 숨김 후 TV 제외
- normalized_keyword 수정
- failed job 조회
- failed job 재시도
- audit log 생성
```

### 7.4 상품 지급

```txt
- 완료 코드 조회
- issued 코드 지급 처리
- status redeemed 확인
- 같은 코드 재지급 차단
- audit log 생성
```

## 8. 보안 점검

```txt
- .env에만 secret 존재
- .env.example에는 placeholder만 존재
- Dockerfile에 API key 없음
- 로그에 JWT, resumeToken, LLM API key 없음
- TV API에 원문 없음
- 관리자 API 인증 필수
- CORS origin 제한
- 자유입력 길이 제한
- 관리자 원문 조회는 필요한 화면에만 존재
```

## 9. 현장 리허설 체크리스트

행사 전 최소 1회 수행한다.

```txt
1. docker compose 또는 배포 환경 기동
2. DB migration 확인
3. 이벤트 상태 open 확인
4. 1~77번 문항 seed 확인
5. QR 코드가 올바른 eventSlug로 연결되는지 확인
6. 모바일 브라우저 2종 이상에서 참가자 플로우 완료
7. 네트워크 차단 후 재시도 확인
8. LLM disabled mode에서 완료 확인
9. mock/live mode 중 운영 설정 확인
10. TV 화면 연결
11. API 재시작 후 TV 자동 재연결 확인
12. 관리자 로그인 확인
13. 검수 처리 확인
14. 완료 코드 지급 처리 확인
15. 이미 지급된 코드 중복 지급 차단 확인
16. 도움 안내 문구 확인
17. seed card 확인
18. 현장 운영자에게 지급 절차 안내
```

## 10. 이벤트 당일 운영 체크리스트

### 10.1 시작 전

```txt
- 이벤트 상태 open
- TV display 정상 표시
- 관리자 로그인 정상
- QR 인쇄물/배너 확인
- 상품 지급 담당자 지정
- LLM mode 확인
- fallback keyword 활성화 확인
- 네트워크 연결 확인
- 비상 시 안내 문구 확인
```

### 10.2 운영 중

```txt
- dashboard 참여자 수 확인
- review 문장 수 확인
- failed keyword job 수 확인
- TV 연결 상태 확인
- 완료 코드 지급 현황 확인
- 부적절 키워드 노출 시 즉시 hidden 처리
- 네트워크 장애 시 TV 마지막 데이터 유지 확인
```

### 10.3 종료 후

```txt
- 이벤트 상태 closed
- TV 화면 종료
- 지급 코드 정산
- 위험/검수 대상 문장 재점검
- 키워드 통계 확인
- LLM 실패율 확인
- 네트워크 장애 로그 확인
- MVP 개선 사항 정리
```

## 11. 최소 수용 기준

MVP는 다음 조건을 만족해야 현장 운영 가능으로 본다.

```txt
참가자:
- 회원가입 없이 완료 가능
- 제출 실패 후 재시도 가능
- LLM disabled 상태에서도 완료 가능

TV:
- 원문 없이 키워드만 표시
- SSE 끊김 시 마지막 데이터 유지
- 자동 재연결 가능

관리자:
- 검수 처리 가능
- failed keyword job 확인 가능
- 완료 코드 지급과 중복 지급 방지 가능

보안:
- TV API 원문 없음
- 관리자 API 인증 필수
- secret 코드 삽입 없음
```

## 12. 장애 대응 기준

### 12.1 LLM 장애

```txt
조치:
- LLM_ENABLED=false 전환 가능
- fallback keyword 유지
- failed job은 관리자 화면에서 확인

참가자 영향:
- 없음 또는 최소화
```

### 12.2 TV 장애

```txt
조치:
- 브라우저 새로고침
- snapshot API 확인
- API health 확인
- display route 재접속

참가자 영향:
- 없음
```

### 12.3 DB 장애

```txt
조치:
- API health 확인
- postgres 컨테이너 상태 확인
- 로그 확인
- 필요 시 운영자에게 접수 지연 안내

참가자 영향:
- 제출과 완료 코드 발급 불가 가능성 있음
```

## 13. 금지 사항

```txt
- 리허설 없이 현장 운영하지 않는다.
- LLM live mode만 믿고 fallback을 끄지 않는다.
- TV에 원문 표시 테스트 코드를 남기지 않는다.
- 완료 코드 중복 지급 확인 없이 상품을 지급하지 않는다.
- 관리자 계정을 공유 비밀번호로 장기 운영하지 않는다.
- 테스트 데이터와 실제 이벤트 데이터를 섞지 않는다.
```
