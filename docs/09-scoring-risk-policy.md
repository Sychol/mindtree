# 09. Scoring and Risk Policy

## 1. 목적

이 문서는 마음나무 MVP의 문항 점수화, 척도별 목적, 절단점, 마음신호 요약 기준, 위험 플래그, 공개 제한 정책을 정의한다.

중요한 전제는 다음이다.

```txt
- 마음나무는 진단, 상담, 치료 서비스가 아니다.
- 점수화는 참가자에게 진단명을 주기 위한 것이 아니라 마음신호 요약을 만들기 위한 내부 계산이다.
- 점수화와 위험 플래그는 서버 규칙으로 계산한다.
- LLM은 위험도, 자살위험, 공개 여부를 최종 판단하지 않는다.
- 위험 플래그가 있어도 참가자 완료와 상품 지급을 자동 차단하지 않는다.
- 위험 플래그가 있는 원문과 키워드는 공개 영역에서 제한한다.
```

## 2. 기준 데이터

문항 seed는 CSV를 JSON으로 변환한 아래 파일을 기준으로 한다.

```txt
docs/data/questions_fire_expo_2026.json
docs/data/scoring_rules_v1.json
```

원본 CSV 구조는 다음이다.

```txt
연번, 구분, 질문, 응답 방식, 비고
```

JSON은 다음 구조를 가진다.

```txt
metadata
scaleMetadata
questions
```

Codex는 문항을 프론트엔드에 하드코딩하지 않는다. Phase 04에서 이 JSON을 읽어 `questions` 테이블 seed로 등록하고, 백엔드 scoring service가 `scaleMetadata`와 `scoreMap`을 기준으로 점수화한다.

현재 scoring rule version은 다음을 사용한다.

```txt
v2-2026-05-13-scale-cutoffs
```

## 3. 문항 범위

MVP는 CSV 기준 1~77번 문항을 사용한다.

```txt
1~13번   profile / 인구통계·직무·사건 기준 문항
14~22번  phq9 / K-PHQ-9
23~42번  pcl5 / K-PCL-5
43~51번  kmies / K-MIES
52~77번  kscs / K-SCS
```

## 4. 점수화 공통 원칙

```txt
- 최종 점수는 서버에서 계산한다.
- 프론트엔드는 점수 결과를 확정하지 않는다.
- question_id가 event에 속하는지 검증한다.
- answer_value는 question_type과 options에 맞는지 검증한다.
- score_value는 questions.score_map 또는 명시적 scoring rule로 계산한다.
- 계산 결과는 scale_scores에 저장한다.
- 모든 계산에는 rule_version을 기록한다.
- 절단점은 코드 곳곳에 흩뿌리지 않고 scoring service 상수 또는 JSON rule config로 관리한다.
```

## 5. 척도별 목적과 절단점

### 5.1 profile

Profile 문항은 점수화 대상이 아니라 비식별 문맥 정보다.

범위:

```txt
1~13번
```

포함 내용:

```txt
- 인구통계
- 소방 직무
- 사건 기준
- 지원 이력
- 노출 수준
- 외부 준거
- 지원 필요도
- 개입 라우팅
```

처리 기준:

```txt
- scale_scores를 생성하지 않는다.
- 마음신호 요약 문장 톤 조정에 제한적으로 사용할 수 있다.
- 개인 식별 가능한 수준의 정보는 수집하거나 공개하지 않는다.
- 4~5번 문항은 3번에서 일반인으로 응답한 경우 스킵 가능하다.
```

### 5.2 K-PHQ-9

공식명:

```txt
한국판 우울 증상 척도
Korean Version of Patient Health Questionnaire-9 : K-PHQ-9
```

목적:

```txt
성인의 우울 정도를 측정하는 데 사용되는 자가보고 설문지.
```

문항 범위:

```txt
14~22번
```

점수화:

```txt
- 각 문항 0~3점
- 총점 범위 0~27점
- 14~22번 문항의 score_value 합산
- 22번 문항은 PHQ-9 item9에 해당한다.
```

절단점:

| 총점 | 코드 | 표시명 | 내부 해석 |
|---:|---|---|---|
| 0~4 | `no_specific_findings` | 특이소견 없음 | 특이소견 없음 |
| 5~9 | `mild_depressive_symptoms` | 가벼운 우울증상 | 가벼운 우울증상 |
| 10~19 | `moderate_depression_suspected` | 중간 정도 우울증 의심 | 중간 정도 우울증 의심 |
| 20~27 | `severe_depression_score_range` | 심한 우울증 의심 점수 구간 | 20점 이상이며 item9가 1점 이상이면 심한 우울증 의심과 위기관리 필요로 처리 |

추가 신호:

```txt
if phq9_total_score >= 16:
  risk_flags.details.phq9_high_instability_signal = true
```

Item9 처리:

```txt
if phq9_item9_score >= 1:
  risk_flags.phq9_item9_positive = true
  risk_flags.help_notice_required = true
  risk_flags.public_restriction = true
```

20점 이상과 item9 양성이 동시에 나타나는 경우:

```txt
if phq9_total_score >= 20 and phq9_item9_score >= 1:
  risk_flags.details.phq9_severe_with_item9 = true
```

주의:

```txt
- item9는 자살·자해 의도 포함 문항이다.
- 1점 이상이면 위기관리 또는 도움 안내가 필요하다.
- 참가자 화면에는 진단명이나 공포를 유발하는 표현을 쓰지 않는다.
```

표현 예시:

```txt
권장:
- 최근 기분과 활력에 부담 신호가 보일 수 있습니다.
- 일상 에너지가 낮아진 느낌이 있을 수 있습니다.

금지:
- 우울증입니다.
- 자살위험입니다.
```

### 5.3 K-PCL-5

공식명:

```txt
한국판 외상 후 스트레스 장애 체크리스트
K-PCL-5
```

목적:

```txt
지난 한 달 동안 겪은 고통스러운 사건으로 인한 PTSD 증상의 심각도를 측정한다.
```

문항 범위:

```txt
23~42번
```

점수화:

```txt
- 각 문항 0~4점
- 총점 범위 0~80점
- 23~42번 문항의 score_value 합산
```

절단점:

| 총점 | 코드 | 표시명 | 내부 해석 |
|---:|---|---|---|
| 0~30 | `normal_range` | 정상범위 | 일상적 수준의 스트레스이거나 임상적으로 유의미한 PTSD 증상은 낮은 상태 |
| 31~33 | `threshold` | 임계치 | PTSD를 의심해 볼 수 있는 경계 지점으로 정밀진단을 권장하는 상태 |
| 34~80 | `high_risk` | 고위험군 | PTSD 증상이 뚜렷하고 심각할 가능성이 높은 상태로 즉각적인 심리상담 및 치료가 필요한 상태 |

위험 플래그:

```txt
if pcl5_total_score >= 34:
  risk_flags.trauma_high_signal = true

if 31 <= pcl5_total_score <= 33:
  risk_flags.details.pcl5_threshold_signal = true
```

주의:

```txt
- `trauma_high_signal`은 공개용 데이터가 아니다.
- TV에는 PCL-5 점수, 구간, 위험 플래그를 표시하지 않는다.
- 참가자 화면에는 PTSD 진단명 대신 마음신호 언어를 사용한다.
```

표현 예시:

```txt
권장:
- 반복적으로 떠오르는 장면이나 긴장 신호가 있을 수 있습니다.
- 몸과 마음이 아직 그 경험에 예민하게 반응하고 있을 수 있습니다.

금지:
- PTSD입니다.
- 고위험군입니다.
```

### 5.4 K-MIES

공식명:

```txt
한국판 도덕손상 사건 척도
Korean Version of Moral Injury Events Scale : K-MIES
```

목적:

```txt
재난 현장에서 도덕적 신념에 어긋나는 상황을 겪은 후 느끼는 심리적 고통을 측정하기 위한 척도.
```

문항 범위:

```txt
43~51번
```

점수화:

```txt
- 각 문항 1~6점
- 총점 범위 9~54점
- 43~51번 문항의 score_value 합산
```

절단점:

| 총점 | 코드 | 표시명 | 내부 해석 |
|---:|---|---|---|
| 9~18 | `low` | 낮음 | 도덕적 갈등 사건을 거의 겪지 않았거나 심리적 영향이 미미한 상태 |
| 19~36 | `moderate` | 중간 | 현장 업무 중 도덕적 딜레마나 배신감을 경험했으며 심리적 불편감이 잔존해 있을 가능성이 있는 상태 |
| 37~54 | `high` | 높음 | 심각한 도덕적 손상을 입었을 가능성이 있으며 강한 죄책감, 수치심, 조직에 대한 불신이 나타날 수 있으며 전문적인 상담을 권장하는 상태 |

위험 플래그:

```txt
if kmies_total_score >= 37:
  risk_flags.moral_injury_high_signal = true
```

주의:

```txt
- 참가자 화면에는 도덕손상이라는 진단·낙인 표현을 직접 쓰지 않는다.
- TV에는 K-MIES 점수, 구간, 위험 플래그를 표시하지 않는다.
```

표현 예시:

```txt
권장:
- 책임감이나 자기비난이 무겁게 느껴질 수 있습니다.
- 마음속에 오래 남은 장면이나 판단이 있을 수 있습니다.
- 신뢰나 배신감과 관련된 마음의 부담이 남아 있을 수 있습니다.

금지:
- 도덕적 손상입니다.
- 문제가 심각합니다.
```

### 5.5 K-SCS

공식명:

```txt
한국판 자기자비 척도
Korean-version of Self-Compassion Scale : K-SCS
```

목적:

```txt
고통스러운 상황에서 자신을 얼마나 친절하고 객관적으로 대하는지를 측정하는 척도.
```

문항 범위:

```txt
52~77번
```

점수화:

```txt
- 각 문항 1~5점
- 역채점 문항은 reversed_score = 6 - answer_value 적용
- 역채점 후 26개 문항의 평균값을 계산
- 수준 판정은 평균값을 소수점 1자리로 반올림한 뒤 적용
```

역채점 문항:

| K-SCS local item no | CSV/global question no |
|---:|---:|
| 2 | 53 |
| 3 | 54 |
| 5 | 56 |
| 6 | 57 |
| 8 | 59 |
| 14 | 65 |
| 15 | 66 |
| 19 | 70 |
| 20 | 71 |
| 23 | 74 |
| 25 | 76 |

절단점:

| 평균값 | 코드 | 표시명 | 내부 해석 |
|---:|---|---|---|
| 1.0~2.4 | `low` | 낮은 수준 | 자신에게 비판적이고 엄격한 편 |
| 2.5~3.5 | `medium` | 보통 | 상황에 따라 자신을 돌보기도 하지만 큰 시련 앞에서 자기비판이나 고립감을 느낄 수 있음 |
| 3.6~5.0 | `high` | 높음 | 자신에 대해 너그럽고 수용적이며 고통을 보편적 인간 경험으로 이해하는 능력이 뛰어남 |

저장 기준:

```txt
scale_scores.scale_code = kscs
scale_scores.raw_score = mean_score
scale_scores.severity_level = low | medium | high
scale_scores.sub_scores.sum_score = 역채점 후 합계
scale_scores.sub_scores.mean_score = 역채점 후 평균
scale_scores.sub_scores.reverse_scored_question_nos = [53,54,56,57,59,65,66,70,71,74,76]
```

주의:

```txt
- K-SCS는 위험 플래그가 아니라 회복 자원 해석에 사용한다.
- 낮은 수준이어도 상품 지급이나 완료를 막지 않는다.
- 참가자 화면에는 자기비난을 강화하는 표현을 쓰지 않는다.
```

표현 예시:

```txt
권장:
- 지금은 스스로에게 조금 더 부드럽게 말해보는 연습이 필요할 수 있습니다.
- 작은 쉼이나 도움 요청이 회복의 시작이 될 수 있습니다.

금지:
- 자기자비가 부족합니다.
- 스스로를 잘 돌보지 못합니다.
```

## 6. Risk Flags

`risk_flags`는 다음 필드를 사용한다.

```txt
phq9_item9_positive
crisis_expression_detected
trauma_high_signal
moral_injury_high_signal
public_restriction
help_notice_required
details
rule_version
```

추가 세부 신호는 `details`에 저장한다.

```json
{
  "phq9_high_instability_signal": true,
  "phq9_severe_with_item9": true,
  "pcl5_threshold_signal": true,
  "kscs_level": "low"
}
```

## 7. 위험 플래그 계산 규칙

### 7.1 PHQ-9 item9

```txt
if phq9_item9_score >= 1:
  phq9_item9_positive = true
  help_notice_required = true
  public_restriction = true
```

이 플래그는 공개 제한과 도움 안내를 위한 운영 플래그다. 진단 또는 위기 개입 판단을 자동 확정하지 않는다.

### 7.2 자유입력 위기 표현

마음카드나 응원 문장에 자해, 자살, 죽음 관련 직접 표현이 감지되면 다음을 적용한다.

```txt
crisis_expression_detected = true
public_restriction = true
help_notice_required = true
safety_status = exclude 또는 review
public_status = excluded 또는 pending
keyword job 생성 제한 또는 키워드 제외
```

감지 방식은 LLM이 아니라 규칙 기반 필터를 기본으로 한다.

```txt
- 금칙어 사전
- 정규식
- 한국어 변형 표현 사전
- 관리자 검수
```

### 7.3 Trauma high signal

```txt
if pcl5_total_score >= 34:
  trauma_high_signal = true
```

31~33점은 임계치로 `risk_flags.details.pcl5_threshold_signal = true`에 기록하되, `trauma_high_signal`은 34점 이상에서만 true로 둔다.

### 7.4 Moral injury high signal

```txt
if kmies_total_score >= 37:
  moral_injury_high_signal = true
```

19~36점은 중간 구간으로 `scale_scores.severity_level = moderate`에 기록하되, `moral_injury_high_signal`은 37점 이상에서만 true로 둔다.

## 8. 공개 제한 정책

`public_restriction = true`이면 다음 정책을 적용한다.

```txt
- TV 키워드 집계 제외
- 마음카드 공개 후보 제외
- 응원 문장 공개 후보 제외
- 관리자 검수 대상으로 표시
- 참가자 완료와 완료 코드 발급은 막지 않음
- 도움 안내 표시 가능
```

위험 플래그는 TV와 일반 참가자에게 표시하지 않는다.

## 9. 마음신호 요약 정책

요약은 다음 입력을 사용한다.

```txt
- scale_scores
- risk_flags
- profile 응답 중 비식별 문맥
- template rule
- 선택적 LLM 보정 결과
```

요약 생성 순서:

```txt
1. 서버가 템플릿 기반 요약을 즉시 생성한다.
2. LLM이 활성화되어 있으면 문장 톤 보정을 시도할 수 있다.
3. LLM 실패 또는 timeout 시 템플릿 요약을 final_text로 사용한다.
4. 참가자는 요약 생성을 오래 기다리지 않는다.
```

요약은 진단명 대신 마음신호 언어를 사용한다.

## 10. 문장 톤 규칙

### 10.1 허용 표현

```txt
- 신호가 나타납니다.
- 부담이 커졌을 수 있습니다.
- 마음이 예민하게 반응하고 있을 수 있습니다.
- 지금은 작은 회복 행동이 도움이 될 수 있습니다.
- 혼자 감당하기 어렵다면 주변 도움을 요청해도 좋습니다.
```

### 10.2 금지 표현

```txt
- 진단명 확정
- 치료 지시
- 공포를 유발하는 위험 단정
- 참가자 책임을 묻는 표현
- 특정 기관 방문 강제
- LLM이 만든 임의 의학 조언
```

## 11. 도움 안내 정책

`help_notice_required = true`이면 참가자에게 별도 도움 안내를 보여줄 수 있다.

도움 안내 원칙:

```txt
- 차분하고 비판단적으로 표현한다.
- 본 이벤트가 진단/치료가 아님을 명시한다.
- 급박한 위험이 있으면 현장 운영자 또는 주변 도움을 요청하도록 안내한다.
- 공개 화면에는 표시하지 않는다.
```

MVP에서는 지역별 상담기관 연동이나 자동 신고 기능을 구현하지 않는다.

## 12. 구현 파일 기준

```txt
api/app/services/scoring_service.py
api/app/services/risk_service.py
api/app/services/summary_service.py
api/app/services/safety_filter_service.py
api/app/repositories/scoring_repository.py
api/app/repositories/risk_repository.py
api/app/schemas/scoring.py
api/app/schemas/summary.py
api/app/tests/test_scoring.py
api/app/tests/test_risk.py
api/app/tests/test_summary.py
```

## 13. 테스트 기준

```txt
- 필수 문항 누락 시 questions_completed 전이 금지
- answer_value가 options 밖이면 거부
- K-PHQ-9 0~4, 5~9, 10~19, 20~27 구간 판정
- K-PHQ-9 total >= 16이면 details.phq9_high_instability_signal true
- K-PHQ-9 item9 >= 1이면 phq9_item9_positive true
- K-PCL-5 0~30, 31~33, 34~80 구간 판정
- K-PCL-5 total >= 34이면 trauma_high_signal true
- K-MIES 9~18, 19~36, 37~54 구간 판정
- K-MIES total >= 37이면 moral_injury_high_signal true
- K-SCS 역채점 문항 53,54,56,57,59,65,66,70,71,74,76 처리
- K-SCS 평균값 기준 1.0~2.4, 2.5~3.5, 3.6~5.0 구간 판정
- 위기 표현 감지 시 public_restriction true
- public_restriction true인 source는 TV 집계 제외
- LLM disabled 상태에서도 template summary 반환
- LLM timeout 상태에서도 사용자 흐름 계속 진행
- 위험 플래그가 있어도 완료 코드 발급 조건이 충족되면 완료 가능
```

## 14. 금지 사항

```txt
- LLM으로 위험 플래그를 최종 판단하지 않는다.
- LLM으로 공개 여부를 결정하지 않는다.
- 척도 절단점을 근거 없이 바꾸지 않는다.
- 참가자에게 진단명으로 결과를 표시하지 않는다.
- TV에 위험 플래그, 점수, 원문을 표시하지 않는다.
- 위험 플래그가 있다는 이유만으로 상품 지급을 자동 차단하지 않는다.
```
