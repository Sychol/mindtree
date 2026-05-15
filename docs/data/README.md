# docs/data

마음나무 문항 seed와 점수화 규칙 원본을 보관한다.

## 최종본 파일

```txt
questions_fire_expo_2026_final_260515.json
scoring_rules_v3_final_260515.json
```

`questions_fire_expo_2026_final_260515.json`은 260515 최종본 CSV를 구현용 JSON으로 변환한 파일이다. 61개 문항, 척도별 목적, 절단점, K-SCS-SF 역채점 문항, `scoreMap`, `options`를 포함한다.

`scoring_rules_v3_final_260515.json`은 최종본 기준 ruleVersion `v3-2026-05-15-final-questions`와 척도별 metadata를 분리한 파일이다.

척도 구성은 다음과 같다.

- profile: 1~14
- kmies: 15~20
- phq9: 21~29
- pcl5: 30~49
- kscs: 50~61

K-MIES 6문항 절단점은 운영용 임시 기준이므로 운영 전 최종 검토가 필요하다.
