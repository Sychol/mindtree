# PHASE 04. 문항 선로딩·척도 응답·점수화

이 문서는 VS Code Codex에 그대로 붙여넣어 사용할 수 있는 구현 지시서다.

## 목표

CSV에서 변환한 JSON 기준 1~77번 문항을 서버에서 제공하고, 참가자의 응답을 bulk 저장하며, 서버 기준으로 척도 점수와 기본 위험 플래그를 계산한다.

```txt
- docs/data/questions_fire_expo_2026.json
docs/data/scoring_rules_v1.json 기반 문항 seed
- 문항 전체 조회 API
- 응답 bulk 저장 API
- answer upsert/idempotent 처리
- K-PHQ-9, K-PCL-5, K-MIES, K-SCS 점수화
- K-SCS 역채점
- 척도별 절단점 적용
- 기본 위험 플래그 계산
- session.status consented → questions_completed 전이
```

## 작업 전 확인 사항

Codex는 작업 전에 반드시 아래를 수행한다.

```txt
1. docs/codex-common-rules.md를 읽는다.
2. docs/05-api-spec.md의 Question and Answer API를 읽는다.
3. docs/09-scoring-risk-policy.md를 읽는다.
4. docs/04-data-model.md의 questions, answers, scale_scores, risk_flags를 확인한다.
5. docs/data/questions_fire_expo_2026.json을 읽는다.
6. Phase 03의 세션/동의 API가 구현되어 있는지 확인한다.
7. 현재 코드베이스에서 seed 방식과 ORM 구조를 확인한다.
```

## 참조 문서

```txt
- docs/04-data-model.md
- docs/05-api-spec.md
- docs/08-session-state.md
- docs/09-scoring-risk-policy.md
- docs/data/questions_fire_expo_2026.json
- docs/codex-common-rules.md
```

## 수정 또는 생성할 파일

권장 backend 파일:

```txt
api/app/api/routes/questions.py
api/app/api/routes/answers.py
api/app/schemas/questions.py
api/app/schemas/answers.py
api/app/repositories/questions.py
api/app/repositories/answers.py
api/app/repositories/scale_scores.py
api/app/repositories/risk_flags.py
api/app/services/questions.py
api/app/services/answers.py
api/app/services/scoring.py
api/app/services/risk_rules.py
api/app/seed/questions_fire_expo_2026.json 또는 api/app/seeds/questions_fire_expo_2026.json
api/app/scripts/seed_questions.py
api/app/tests/test_questions_scoring.py
```

권장 frontend 파일:

```txt
web/src/api/questions.ts
web/src/api/answers.ts
web/src/types/question.ts
web/src/types/answer.ts
```

프론트엔드 화면 구현은 Phase 05에서 진행한다. 이 Phase에서는 API client와 type 정도만 준비한다.

## 구현 내용

### 1. 문항 seed 구현

문항 seed source:

```txt
docs/data/questions_fire_expo_2026.json
```

MVP 문항 범위:

```txt
1~13번   profile
14~22번  phq9 / K-PHQ-9
23~42번  pcl5 / K-PCL-5
43~51번  kmies / K-MIES
52~77번  kscs / K-SCS
```

구현 기준:

```txt
- 문항은 프론트에 하드코딩하지 않는다.
- seed script는 JSON의 questions 배열을 읽어 questions 테이블에 upsert한다.
- question_no와 display_order를 명확히 둔다.
- options와 score_map을 저장한다.
- JSON의 scaleMetadata는 scoring service의 rule config로 참조한다.
- 실제 문항 문구를 임의로 바꾸지 않는다.
```

Seed upsert 기준:

```txt
UNIQUE(event_id, question_no)
UNIQUE(event_id, question_key)
```

기존 문항이 있으면 question_no 기준으로 title, options, score_map, required, display_order를 갱신한다.

### 2. 문항 전체 조회 API

다음 endpoint를 구현한다.

```http
GET /api/events/{eventSlug}/questions
```

기준:

```txt
- eventSlug 기준 event를 찾는다.
- display_order 오름차순으로 1~77번 문항을 반환한다.
- options는 프론트가 바로 렌더링할 수 있는 JSON으로 반환한다.
- score_map은 응답에 포함하지 않아도 된다. 최종 점수화는 서버가 수행한다.
- responseRaw, section, itemLocalNo는 필요하면 포함할 수 있다.
```

### 3. 응답 bulk 저장 API

다음 endpoint를 구현한다.

```http
PUT /api/sessions/{sessionId}/answers/bulk
```

구현 기준:

```txt
- session.status가 consented 이상인지 확인한다.
- session의 event에 속한 questionId만 허용한다.
- answer_value가 question.options/validation 범위에 맞는지 검증한다.
- 같은 sessionId/questionId 응답은 upsert한다.
- 중복 제출 또는 재시도에 안전해야 한다.
- 전체 필수 문항이 충족되면 scoring을 실행한다.
- 부분 저장이 필요한 경우 missingQuestionNos를 반환한다.
```

프론트엔드가 네트워크 실패 후 같은 요청을 다시 보내도 중복 answer row가 생성되면 안 된다.

### 4. 점수화 서비스

`api/app/services/scoring.py`에 척도별 점수화 함수를 구현한다.

필수 함수 예시:

```txt
calculate_scale_scores(session_id)
calculate_phq9(answers)
calculate_pcl5(answers)
calculate_kmies(answers)
calculate_kscs(answers)
get_scale_severity(scale_code, score, details)
```

공통 기준:

```txt
- answer_value와 question.score_map을 기준으로 score_value를 계산한다.
- scale_scores는 session_id + scale_code 기준 upsert한다.
- severity_level은 docs/09-scoring-risk-policy.md 기준을 따른다.
- rule_version은 v2-2026-05-13-scale-cutoffs을 사용한다.
```

### 5. K-PHQ-9 점수화

범위:

```txt
14~22번
```

계산:

```txt
phq9_total_score = 14~22번 score_value 합계
phq9_item9_score = 22번 score_value
```

절단점:

```txt
0~4    no_specific_findings / 특이소견 없음
5~9    mild_depressive_symptoms / 가벼운 우울증상
10~19  moderate_depression_suspected / 중간 정도 우울증 의심
20~27  severe_depression_score_range / 심한 우울증 의심 점수 구간
```

추가 details:

```txt
if phq9_total_score >= 16:
  details.phq9_high_instability_signal = true

if phq9_total_score >= 20 and phq9_item9_score >= 1:
  details.phq9_severe_with_item9 = true
```

### 6. K-PCL-5 점수화

범위:

```txt
23~42번
```

계산:

```txt
pcl5_total_score = 23~42번 score_value 합계
```

절단점:

```txt
0~30   normal_range / 정상범위
31~33  threshold / 임계치
34~80  high_risk / 고위험군
```

추가 details:

```txt
if 31 <= pcl5_total_score <= 33:
  details.pcl5_threshold_signal = true
```

### 7. K-MIES 점수화

범위:

```txt
43~51번
```

계산:

```txt
kmies_total_score = 43~51번 score_value 합계
```

절단점:

```txt
9~18   low / 낮음
19~36  moderate / 중간
37~54  high / 높음
```

### 8. K-SCS 점수화와 역채점

범위:

```txt
52~77번
```

역채점 문항:

```txt
local item no: 2, 3, 5, 6, 8, 14, 15, 19, 20, 23, 25
global question no: 53, 54, 56, 57, 59, 65, 66, 70, 71, 74, 76
```

계산:

```txt
if question_no in [53,54,56,57,59,65,66,70,71,74,76]:
  adjusted_score = 6 - answer_value
else:
  adjusted_score = answer_value

kscs_sum_score = adjusted_score 합계
kscs_mean_score = kscs_sum_score / 26
kscs_level_score = round(kscs_mean_score, 1)
```

절단점:

```txt
1.0~2.4  low / 낮은 수준
2.5~3.5  medium / 보통
3.6~5.0  high / 높음
```

저장 기준:

```txt
scale_scores.scale_code = kscs
scale_scores.raw_score = kscs_mean_score
scale_scores.severity_level = low | medium | high
scale_scores.sub_scores.sum_score = kscs_sum_score
scale_scores.sub_scores.mean_score = kscs_mean_score
scale_scores.sub_scores.rounded_mean_score = kscs_level_score
scale_scores.sub_scores.reverse_scored_question_nos = [53,54,56,57,59,65,66,70,71,74,76]
```

### 9. 기본 위험 플래그 계산

`api/app/services/risk_rules.py`에 기본 위험 플래그 계산을 구현한다.

필수 기준:

```txt
- PHQ-9 item9 점수가 1 이상이면 phq9_item9_positive = true
- phq9_item9_positive이면 help_notice_required = true
- phq9_item9_positive이면 public_restriction = true
- PCL-5 total >= 34이면 trauma_high_signal = true
- K-MIES total >= 37이면 moral_injury_high_signal = true
- PHQ-9 total >= 16, PCL-5 31~33, PHQ-9 20점 이상 + item9 양성 등은 details에 기록
```

자유입력 기반 `crisis_expression_detected`는 Phase 07에서 마음카드/응원 문장 안전 필터와 함께 보완한다.

### 10. 세션 상태 전이

전체 필수 문항이 충족되고 점수화가 완료되면:

```txt
session.status = questions_completed
session.last_step = summary
```

허용 전이:

```txt
consented → questions_completed
```

이미 questions_completed 이상인 세션이 재제출하면 응답을 upsert하고 점수화 결과를 다시 계산해도 된다. 단, 완료 코드가 이미 발급된 세션의 재점수화는 신중히 처리하고 TODO 또는 제한 정책을 둔다.

## 금지 사항

```txt
- 프론트엔드에 문항 1~77번을 하드코딩하지 않는다.
- CSV 원문을 그대로 런타임에서 매번 파싱하지 않는다. JSON seed를 기준으로 한다.
- 프론트엔드 점수 계산값을 최종값으로 저장하지 않는다.
- LLM으로 점수화 또는 위험 플래그를 계산하지 않는다.
- 척도 절단점을 임의로 바꾸지 않는다.
- 문항 문구를 임의의 임상 진단 문구로 창작하지 않는다.
- 카드, 응원 문장, 키워드, TV 기능을 이 Phase에서 구현하지 않는다.
- 사용자 입력에서 직접 SQL을 생성하지 않는다.
```

## 완료 기준

```txt
- docs/data/questions_fire_expo_2026.json 기반 seed가 동작한다.
- 1~77번 문항 조회 API가 동작한다.
- 응답 bulk 저장 API가 동작한다.
- 같은 응답 재제출 시 중복 row가 생기지 않는다.
- 필수 문항 완료 시 scale_scores가 생성 또는 갱신된다.
- K-PHQ-9, K-PCL-5, K-MIES, K-SCS 점수화가 동작한다.
- K-SCS 역채점이 정확히 반영된다.
- 기본 risk_flags가 생성 또는 갱신된다.
- session.status가 questions_completed로 전이된다.
- backend 테스트가 통과한다.
```

## 테스트 방법

```bash
cd api
pytest
```

API smoke test 예시:

```bash
curl http://localhost:8000/api/events/fire-expo-2026/questions

curl -X PUT http://localhost:8000/api/sessions/<sessionId>/answers/bulk   -H "Content-Type: application/json"   -d '{"answers":[{"questionId":"<questionId>","answerValue":2}],"clientProgress":{"lastQuestionNo":77}}'
```

DB 확인 예시:

```bash
docker compose exec postgres psql -U maeumnamu -d maeumnamu -c "select scale_code, raw_score, severity_level, sub_scores from scale_scores;"
docker compose exec postgres psql -U maeumnamu -d maeumnamu -c "select phq9_item9_positive, trauma_high_signal, moral_injury_high_signal, public_restriction, details from risk_flags;"
```

필수 단위 테스트:

```txt
- K-PHQ-9 0~4, 5~9, 10~19, 20~27 구간
- K-PHQ-9 item9 >= 1 플래그
- K-PHQ-9 total >= 16 details
- K-PCL-5 31~33 threshold details
- K-PCL-5 >= 34 trauma_high_signal
- K-MIES 37 이상 moral_injury_high_signal
- K-SCS 역채점 문항 53,54,56,57,59,65,66,70,71,74,76
- K-SCS 평균 1.0~2.4, 2.5~3.5, 3.6~5.0 구간
```

## 작업 후 보고 형식

```md
## 작업 결과 보고

### 변경 파일
- `api/app/api/routes/questions.py`: 문항 조회 API 구현
- `api/app/api/routes/answers.py`: 응답 bulk 저장 API 구현
- `api/app/services/scoring.py`: 척도 점수화 구현
- `api/app/services/risk_rules.py`: 기본 위험 플래그 구현
- `api/app/seeds/questions_fire_expo_2026.json`: 문항 seed 반영

### 구현 내용
- 1~77번 문항 seed/조회
- 응답 upsert
- 서버 점수화
- K-SCS 역채점
- 절단점 기반 severity_level
- 기본 위험 플래그

### 실행 방법
- `cd api && pytest`
- 문항 조회/응답 제출 curl

### 테스트 결과
- pytest 결과
- 중복 제출 테스트 결과
- scale_scores/risk_flags 생성 확인

### 남은 작업 / TODO
- Phase 05에서 참가자 모바일 플로우와 재시도 UX 구현
- Phase 06에서 마음신호 요약 구현
```
