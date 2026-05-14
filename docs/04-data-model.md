# 04. Data Model

## 1. 설계 원칙

PostgreSQL은 마음나무 MVP의 단일 데이터 저장소다. 정형 데이터와 원문 데이터를 모두 저장하되, 공개 범위는 서버 로직과 검수 상태로 엄격히 제한한다.

핵심 원칙은 다음이다.

```txt
- 원문 세션 키를 DB에 저장하지 않는다.
- 익명 세션은 해시 또는 토큰 기반으로 관리한다.
- 사용자 입력 원문은 TV에 직접 노출하지 않는다.
- TV에는 정제된 키워드만 제공한다.
- 위험 플래그와 공개 여부는 서버 규칙으로 계산한다.
- LLM 결과는 보조 데이터이며 최종 판단 데이터가 아니다.
- 관리자 주요 행위는 감사 로그로 남긴다.
```

## 2. Enum 값

구현 시 Python enum 또는 DB enum으로 관리한다.

```txt
event_status:
- draft
- open
- closed
- archived

session_status:
- created
- consented
- questions_completed
- summary_viewed
- card_created
- reply_created
- completed
- abandoned

question_type:
- single_select
- multi_select
- likert
- text
- number

scale_code:
- profile
- phq9
- pcl5
- kmies
- kscs

safety_status:
- safe
- review
- exclude

public_status:
- pending
- public
- hidden
- excluded

reply_type:
- comfort
- empathy
- small_coping

keyword_job_status:
- pending
- processing
- succeeded
- failed
- retry_wait

keyword_source_type:
- mind_card
- reply
- summary

keyword_category:
- mind_signal
- support
- recovery
- coping
- neutral

keyword_status:
- active
- hidden
- excluded

keyword_extraction_method:
- llm
- fallback
- admin

completion_code_status:
- issued
- redeemed
- void
```

## 3. 테이블 설계

## 3.1 events

이벤트 기본 정보를 저장한다.

```sql
CREATE TABLE events (
  id UUID PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  starts_at TIMESTAMPTZ,
  ends_at TIMESTAMPTZ,
  consent_version TEXT NOT NULL DEFAULT 'v1',
  settings JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`settings` 예시:

```json
{
  "displayEnabled": true,
  "llmEnabled": false,
  "maxMindCardsPerSession": 3,
  "completionCodePrefix": "TREE",
  "helpNoticeEnabled": true
}
```

## 3.2 sessions

익명 참가 세션을 저장한다.

```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  anonymous_key_hash TEXT NOT NULL,
  resume_token_hash TEXT,
  status TEXT NOT NULL DEFAULT 'created',
  last_step TEXT,
  client_meta JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  UNIQUE(event_id, anonymous_key_hash)
);
```

주의 사항:

```txt
- 원문 session key 또는 resume token은 DB에 저장하지 않는다.
- 동일 브라우저 재접속 시 token hash로 세션을 복구한다.
- 중복 참여를 완벽히 막기보다 완료 코드 중복 지급을 통제한다.
```

## 3.3 consent_logs

동의 기록을 저장한다.

```sql
CREATE TABLE consent_logs (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  session_id UUID NOT NULL REFERENCES sessions(id),
  consent_version TEXT NOT NULL,
  accepted_items JSONB NOT NULL,
  ip_hash TEXT,
  user_agent_hash TEXT,
  accepted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`accepted_items` 예시:

```json
{
  "eventIsNotDiagnosis": true,
  "anonymousKeywordDisplay": true,
  "cardMayBeShownAnonymously": true,
  "noIdentifyingInfo": true,
  "adminModeration": true
}
```

## 3.4 questions

문항 설정을 저장한다.

```sql
CREATE TABLE questions (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  question_no INTEGER NOT NULL,
  scale_code TEXT NOT NULL,
  question_key TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  question_type TEXT NOT NULL,
  options JSONB NOT NULL DEFAULT '[]',
  score_map JSONB NOT NULL DEFAULT '{}',
  required BOOLEAN NOT NULL DEFAULT true,
  display_order INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(event_id, question_no),
  UNIQUE(event_id, question_key)
);
```

`options` 예시:

```json
[
  { "label": "전혀 아니다", "value": 0 },
  { "label": "며칠 동안", "value": 1 },
  { "label": "일주일 이상", "value": 2 },
  { "label": "거의 매일", "value": 3 }
]
```

## 3.5 answers

참가자의 문항 응답을 저장한다.

```sql
CREATE TABLE answers (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  session_id UUID NOT NULL REFERENCES sessions(id),
  question_id UUID NOT NULL REFERENCES questions(id),
  answer_value JSONB NOT NULL,
  score_value NUMERIC,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(session_id, question_id)
);
```

`UNIQUE(session_id, question_id)`를 통해 같은 문항 응답을 upsert한다. 제출 재시도와 중복 클릭에 대비한 idempotent 처리에 필요하다.

## 3.6 scale_scores

척도별 점수를 저장한다.

```sql
CREATE TABLE scale_scores (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  session_id UUID NOT NULL REFERENCES sessions(id),
  scale_code TEXT NOT NULL,
  raw_score NUMERIC NOT NULL,
  severity_level TEXT,
  sub_scores JSONB NOT NULL DEFAULT '{}',
  rule_version TEXT NOT NULL DEFAULT 'v1',
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(session_id, scale_code)
);
```

`sub_scores` 예시:

```json
{
  "intrusion": 8,
  "avoidance": 5,
  "negativeMood": 10,
  "arousal": 9
}
```

## 3.7 risk_flags

위험 플래그를 저장한다.

```sql
CREATE TABLE risk_flags (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  session_id UUID NOT NULL REFERENCES sessions(id),
  phq9_item9_positive BOOLEAN NOT NULL DEFAULT false,
  crisis_expression_detected BOOLEAN NOT NULL DEFAULT false,
  trauma_high_signal BOOLEAN NOT NULL DEFAULT false,
  moral_injury_high_signal BOOLEAN NOT NULL DEFAULT false,
  public_restriction BOOLEAN NOT NULL DEFAULT false,
  help_notice_required BOOLEAN NOT NULL DEFAULT false,
  details JSONB NOT NULL DEFAULT '{}',
  rule_version TEXT NOT NULL DEFAULT 'v1',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(session_id)
);
```

위험 플래그는 LLM이 아니라 서버 규칙으로 계산한다.

## 3.8 summaries

마음신호 요약을 저장한다.

```sql
CREATE TABLE summaries (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  session_id UUID NOT NULL REFERENCES sessions(id),
  template_text TEXT NOT NULL,
  llm_text TEXT,
  final_text TEXT NOT NULL,
  generation_mode TEXT NOT NULL DEFAULT 'template',
  llm_job_id UUID,
  viewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(session_id)
);
```

`generation_mode` 값:

```txt
- template
- llm
- fallback
```

## 3.9 mind_cards

참가자가 작성한 마음카드를 저장한다.

```sql
CREATE TABLE mind_cards (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  session_id UUID NOT NULL REFERENCES sessions(id),
  prompt_type TEXT NOT NULL,
  content_raw TEXT NOT NULL,
  content_redacted TEXT,
  safety_status TEXT NOT NULL DEFAULT 'review',
  public_status TEXT NOT NULL DEFAULT 'pending',
  moderation_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_at TIMESTAMPTZ,
  reviewed_by UUID
);
```

`prompt_type` 예시:

```txt
- to_past_me
- to_now_me
- to_colleague
- stress_memory
```

공개 가능한 카드만 타인 카드 선택 화면에 노출한다.

```txt
노출 조건:
- safety_status = safe
- public_status = public
- crisis 관련 제한 없음
- 자기 세션 카드 제외
```

## 3.10 card_selections

참가자가 선택한 타인 카드를 저장한다.

```sql
CREATE TABLE card_selections (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  session_id UUID NOT NULL REFERENCES sessions(id),
  selected_card_id UUID NOT NULL REFERENCES mind_cards(id),
  selected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(session_id)
);
```

## 3.11 replies

타인 카드에 대한 응원·공감·작은 대처법 문장을 저장한다.

```sql
CREATE TABLE replies (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  session_id UUID NOT NULL REFERENCES sessions(id),
  target_card_id UUID NOT NULL REFERENCES mind_cards(id),
  reply_type TEXT NOT NULL,
  content_raw TEXT NOT NULL,
  content_redacted TEXT,
  safety_status TEXT NOT NULL DEFAULT 'review',
  public_status TEXT NOT NULL DEFAULT 'pending',
  moderation_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_at TIMESTAMPTZ,
  reviewed_by UUID
);
```

`reply_type` 값:

```txt
- comfort
- empathy
- small_coping
```

## 3.12 keyword_jobs

LLM 또는 fallback 키워드 추출 작업을 저장한다.

```sql
CREATE TABLE keyword_jobs (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  source_type TEXT NOT NULL,
  source_id UUID NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 2,
  provider TEXT,
  fallback_used BOOLEAN NOT NULL DEFAULT false,
  input_snapshot JSONB NOT NULL DEFAULT '{}',
  output_snapshot JSONB NOT NULL DEFAULT '{}',
  error_message TEXT,
  locked_at TIMESTAMPTZ,
  next_run_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`source_type` 값:

```txt
- mind_card
- reply
- summary
```

## 3.13 keywords

정제된 키워드를 저장한다.

```sql
CREATE TABLE keywords (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  source_type TEXT NOT NULL,
  source_id UUID NOT NULL,
  keyword_text TEXT NOT NULL,
  normalized_keyword TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'neutral',
  weight NUMERIC NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'active',
  extraction_method TEXT NOT NULL,
  job_id UUID REFERENCES keyword_jobs(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

TV 집계에는 다음 조건의 키워드만 포함한다.

```txt
- keywords.status = active
- source의 safety_status = safe
- source의 public_status가 excluded가 아님
- 위험 플래그로 공개 제한되지 않음
```

## 3.14 completion_codes

이벤트 완료 코드와 상품 지급 상태를 저장한다.

```sql
CREATE TABLE completion_codes (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES events(id),
  session_id UUID NOT NULL REFERENCES sessions(id),
  code TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'issued',
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  redeemed_at TIMESTAMPTZ,
  redeemed_by UUID,
  notes TEXT,
  UNIQUE(event_id, session_id)
);
```

`status` 값:

```txt
- issued
- redeemed
- void
```

## 3.15 admin_users

관리자 계정을 저장한다.

```sql
CREATE TABLE admin_users (
  id UUID PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'operator',
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`role` 예시:

```txt
- owner
- operator
- reviewer
```

## 3.16 admin_audit_logs

관리자 행위 로그를 저장한다.

```sql
CREATE TABLE admin_audit_logs (
  id UUID PRIMARY KEY,
  event_id UUID REFERENCES events(id),
  admin_user_id UUID REFERENCES admin_users(id),
  action TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id UUID,
  before_value JSONB,
  after_value JSONB,
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

감사 로그 대상 예시:

```txt
- card.publish
- card.hide
- card.edit
- card.delete
- reply.publish
- reply.hide
- keyword.hide
- keyword.edit
- keyword.recalculate
- keyword_job.retry
- completion_code.redeem
- completion_code.void
```

## 3.17 question seed JSON

문항 seed는 아래 파일을 기준으로 한다.

```txt
docs/data/questions_fire_expo_2026.json
docs/data/scoring_rules_v1.json
```

이 파일은 DB 테이블이 아니라 seed source다. Codex는 Phase 04에서 이 JSON을 읽어 `questions` 테이블에 upsert한다.

JSON 주요 필드:

```txt
metadata.ruleVersion = v2-2026-05-13-scale-cutoffs
scaleMetadata.profile
scaleMetadata.phq9
scaleMetadata.pcl5
scaleMetadata.kmies
scaleMetadata.kscs
questions[]
```

`questions[]`의 주요 필드:

```txt
questionNo
scaleCode
section
itemLocalNo
questionKey
title
questionType
options
scoreMap
validation
scoring
riskTrigger
note
```

K-SCS 점수화 저장 기준:

```txt
scale_scores.scale_code = kscs
scale_scores.raw_score = 역채점 후 평균값
scale_scores.sub_scores.sum_score = 역채점 후 합계
scale_scores.sub_scores.mean_score = 역채점 후 평균값
scale_scores.sub_scores.rounded_mean_score = 소수점 1자리 반올림 평균값
scale_scores.sub_scores.reverse_scored_question_nos = [53,54,56,57,59,65,66,70,71,74,76]
```

위험 플래그 details 예시:

```json
{
  "phq9_high_instability_signal": true,
  "phq9_severe_with_item9": true,
  "pcl5_threshold_signal": true,
  "kscs_level": "low"
}
```

## 4. 권장 인덱스

```sql
CREATE INDEX idx_sessions_event_status ON sessions(event_id, status);
CREATE INDEX idx_questions_event_order ON questions(event_id, display_order);
CREATE INDEX idx_answers_session ON answers(session_id);
CREATE INDEX idx_scale_scores_session ON scale_scores(session_id);
CREATE INDEX idx_risk_flags_event ON risk_flags(event_id, public_restriction, help_notice_required);
CREATE INDEX idx_mind_cards_event_public ON mind_cards(event_id, safety_status, public_status, created_at DESC);
CREATE INDEX idx_replies_event_public ON replies(event_id, safety_status, public_status, created_at DESC);
CREATE INDEX idx_keyword_jobs_status ON keyword_jobs(status, next_run_at, created_at);
CREATE INDEX idx_keywords_event_status ON keywords(event_id, status, normalized_keyword);
CREATE INDEX idx_completion_codes_event_code ON completion_codes(event_id, code);
CREATE INDEX idx_admin_audit_logs_event_created ON admin_audit_logs(event_id, created_at DESC);
```

## 5. 삭제와 보존 정책

MVP에서는 실제 삭제보다 상태 변경을 기본으로 한다.

```txt
마음카드 삭제:
- public_status = hidden 또는 excluded
- 원문은 관리자 권한에서만 확인 가능

키워드 숨김:
- keywords.status = hidden

완료 코드 무효화:
- completion_codes.status = void

관리자 감사 로그:
- 삭제하지 않음
```

운영 종료 후 데이터 보존 기간과 파기 정책은 별도 운영 정책으로 확정한다.
