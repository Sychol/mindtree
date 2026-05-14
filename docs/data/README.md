# docs/data

이 폴더는 마음나무 MVP의 문항 seed와 점수화 규칙을 보관한다.

## 파일

```txt
questions_fire_expo_2026.json
scoring_rules_v1.json
260508_소방박람회_조사항목_full_version.csv
```

## 기준

`questions_fire_expo_2026.json`은 첨부 CSV `260508_소방박람회 조사항목(full version).csv`를 구현용 JSON으로 변환한 파일이다. 77개 문항, 척도별 목적, 절단점, K-SCS 역채점 문항, `scoreMap`, `options`를 포함한다.

`scoring_rules_v1.json`은 구현 시 scoring service가 참조하기 쉽도록 `scaleMetadata`만 분리한 파일이다.

Codex는 Phase 04에서 이 파일을 기준으로 `questions` 테이블 seed, `scoring.py`, `risk_rules.py`를 구현한다.
