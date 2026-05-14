# PHASE 06. 위험 플래그 기반 마음신호 요약과 LLM fallback

이 문서는 VS Code Codex에 그대로 붙여넣어 실행할 수 있는 구현 지시서다.

## 목표

문항 응답 완료 후 참가자에게 개인 마음신호 요약을 제공한다.

이 Phase의 핵심은 LLM이 느리거나 실패해도 사용자가 기다리지 않게 하는 것이다. 마음신호 요약은 서버 규칙 기반 템플릿으로 즉시 제공 가능해야 하며, LLM은 선택적으로 문장을 부드럽게 보정하는 보조 역할만 한다.

구현 범위는 다음이다.

```txt
- 템플릿 기반 마음신호 요약 생성
- 선택적 LLM 요약 보정 구조
- LLM disabled/mock 모드
- LLM 실패 시 템플릿 fallback 유지
- summary_viewed 상태 전이
- 위험 플래그가 있는 경우 도움 안내 제공
- 참가자 summary 화면 구현
```

## 작업 전 확인 사항

Codex는 먼저 아래를 수행한다.

```txt
1. Phase 04의 scale_scores와 risk_flags 구현 결과를 확인한다.
2. Phase 05의 참가자 라우트 구현 결과를 확인한다.
3. docs/codex-common-rules.md를 읽는다.
4. docs/05-api-spec.md에서 Summary API를 확인한다.
5. docs/08-session-state.md를 읽는다.
6. docs/09-scoring-risk-policy.md를 읽는다.
7. docs/10-llm-keyword-policy.md에서 LLM 역할 제한을 확인한다.
```

## 참조 문서

```txt
docs/codex-common-rules.md
docs/05-api-spec.md
docs/08-session-state.md
docs/09-scoring-risk-policy.md
docs/10-llm-keyword-policy.md
docs/13-security-privacy-policy.md
```

## 수정 또는 생성할 파일

상황에 따라 아래 파일을 생성 또는 보완한다.

```txt
api/app/api/routes/summaries.py
api/app/schemas/summaries.py
api/app/services/summaries.py
api/app/services/summary_templates.py
api/app/services/llm/__init__.py
api/app/services/llm/base.py
api/app/services/llm/disabled.py
api/app/services/llm/mock.py
api/app/services/llm/provider.py
api/app/repositories/summaries.py
api/tests/test_summary_api.py
api/tests/test_summary_templates.py
web/src/pages/participant/SummaryPage.tsx
web/src/components/participant/HelpNotice.tsx
web/src/hooks/useSummary.ts
web/src/routes/ParticipantRoutes.tsx
```

## 구현 내용

### 1. Summary API 구현

아래 API를 구현한다.

```http
GET /api/sessions/{sessionId}/summary
```

응답 예시:

```json
{
  "summary": {
    "id": "uuid",
    "mainMessage": "최근 마음에 긴장 신호가 나타납니다.",
    "signals": [
      "반복적으로 떠오르는 생각이 있을 수 있습니다.",
      "스스로를 다그치기보다 회복을 위한 작은 행동이 필요할 수 있습니다."
    ],
    "recommendedAction": "잠시 숨을 고르고, 믿을 수 있는 사람에게 현재 상태를 말해보는 것이 도움이 될 수 있습니다.",
    "method": "template",
    "isDiagnosis": false
  },
  "helpNotice": {
    "enabled": true,
    "message": "위기감을 느끼거나 자신을 해치고 싶은 생각이 든다면 현장 운영자나 가까운 전문가에게 도움을 요청해 주세요."
  }
}
```

구현 기준:

```txt
- session.status가 questions_completed 이상이어야 한다.
- scale_scores와 risk_flags를 기준으로 요약을 생성한다.
- 이미 생성된 summary가 있으면 재사용한다.
- summary 조회 또는 확인 시 session.status를 summary_viewed로 전이한다.
- 이미 이후 상태이면 역전이하지 않는다.
```

### 2. 템플릿 기반 요약 생성

LLM 없이도 항상 요약을 생성할 수 있어야 한다.

요약 문장은 진단명이 아니라 마음신호 언어를 사용한다.

예시 문장:

```txt
- 최근 마음에 긴장 신호가 나타납니다.
- 반복적으로 떠오르는 생각이 있을 수 있습니다.
- 자기비난이나 책임감이 무겁게 느껴질 수 있습니다.
- 지금은 스스로를 다그치기보다 회복을 위한 작은 행동이 필요할 수 있습니다.
```

구현 기준:

```txt
- PHQ-9, PCL-5, K-MIES, K-SCS 점수와 flag를 읽는다.
- 절단점이 미정인 항목은 docs 기준의 TODO를 남긴다.
- 참가자에게 점수 숫자와 진단명을 직접 강조하지 않는다.
- summary.method는 template, llm_refined, fallback 중 하나로 관리한다.
```

### 3. 선택적 LLM 요약 보정

LLM은 보조 역할만 한다.

LLM이 할 수 있는 것:

```txt
- 템플릿 문장을 더 부드럽게 다듬기
- 과도하게 딱딱한 표현을 현장 이벤트 톤으로 바꾸기
```

LLM이 하면 안 되는 것:

```txt
- 진단
- 위험도 최종 판정
- 자살위험 판단
- 공개 여부 결정
- 세션 상태 결정
- 점수 계산
```

구현 기준:

```txt
- LLM_ENABLED=false이면 LLM을 호출하지 않는다.
- LLM_PROVIDER=disabled이면 disabled provider를 사용한다.
- LLM_PROVIDER=mock이면 deterministic한 mock 결과를 반환한다.
- LLM timeout을 적용한다.
- LLM 실패 시 템플릿 요약을 그대로 사용한다.
- LLM 지연 때문에 참가자 화면이 오래 멈추면 안 된다.
```

MVP에서는 동기 호출을 하더라도 짧은 timeout을 두고 즉시 fallback한다. 별도 비동기 작업 큐로 확장하지 않는다.

### 4. 도움 안내

위험 플래그가 있거나 도움 안내가 활성화된 이벤트에서는 도움 안내를 제공한다.

구현 기준:

```txt
- 도움 안내는 진단 또는 상담 대체 문구로 쓰지 않는다.
- 자해/자살 위험 표현이 감지된 경우 더 직접적인 도움 요청 안내를 제공한다.
- 현장 운영자가 별도 연락처나 도움 문구를 설정할 수 있도록 event.settings 확장 여지를 둔다.
```

단, Phase 06에서 복잡한 상담 라우팅 기능은 구현하지 않는다.

### 5. 참가자 Summary 화면

`web/src/pages/participant/SummaryPage.tsx`를 구현한다.

구현 기준:

```txt
- GET /api/sessions/{sessionId}/summary 호출
- 요약 메시지, signals, recommendedAction 표시
- 본 이벤트는 진단/치료가 아니라는 안내 표시
- 위험 플래그가 있을 경우 도움 안내 표시
- 다음 단계는 마음카드 작성 화면으로 이동할 수 있게 준비
```

다음 단계 라우트:

```txt
/:eventSlug/cards/new
```

Phase 07 전이라면 해당 라우트는 placeholder 또는 TODO로 남겨도 된다.

### 6. 테스트

필수 테스트:

```txt
- questions_completed 이전 세션에서 summary 조회 시 적절한 에러
- scale_scores 기반 template summary 생성
- risk_flags가 있을 때 helpNotice 반환
- LLM_ENABLED=false이면 LLM 호출 없음
- LLM mock provider가 deterministic하게 동작
- LLM 실패 시 template fallback 사용
- summary 조회 후 session.status가 summary_viewed로 전이
- 웹 summary 화면 build 통과
```

## 금지 사항

```txt
- LLM이 위험도, 자살위험, 공개 여부를 판단하게 하지 않는다.
- LLM 응답을 기다리느라 사용자를 장시간 대기시키지 않는다.
- 마음카드, 응원 문장, 키워드 job을 구현하지 않는다.
- TV 화면이나 관리자 화면을 구현하지 않는다.
- 상담 라우팅, 전문가 배정, 긴급 알림을 구현하지 않는다.
```

## 완료 기준

```txt
- GET /api/sessions/{sessionId}/summary 동작
- 템플릿 기반 요약이 항상 생성 가능
- LLM disabled/mock/failure fallback이 동작
- summary_viewed 상태 전이가 동작
- 위험 플래그 기반 도움 안내가 표시됨
- 참가자 summary 화면이 동작
- 관련 테스트와 web build가 통과
```

## 테스트 방법

```bash
cd api
pytest

cd ../web
npm run build
```

수동 확인:

```txt
1. 참가자 플로우에서 문항 응답을 완료한다.
2. /:eventSlug/summary로 이동한다.
3. 요약이 표시되는지 확인한다.
4. LLM_ENABLED=false 상태에서도 요약이 표시되는지 확인한다.
5. LLM_PROVIDER=mock 상태에서 mock 보정이 동작하는지 확인한다.
```

## 작업 후 보고 형식

```md
## 작업 요약
- 템플릿 기반 마음신호 요약, 선택적 LLM 보정, fallback, summary 화면을 구현했다.

## 변경 파일
- api/app/services/summaries.py: 요약 생성 로직 추가
- api/app/services/llm/mock.py: mock LLM provider 추가
- web/src/pages/participant/SummaryPage.tsx: 요약 화면 추가
- ...

## 실행 방법
- cd api && pytest
- cd web && npm run build

## 테스트 결과
- ...

## 남은 작업 / TODO
- 마음카드와 응원 문장 플로우는 Phase 07에서 구현 필요
- 키워드 추출 job은 Phase 08에서 구현 필요

## 주의 사항
- LLM은 문장 보정에만 사용하고 위험 판단에는 사용하지 않음
```
