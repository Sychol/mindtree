# docs/data

마음나무 문항 seed와 점수화 규칙 원본을 보관한다.

## 현재 최종 문항

```txt
questions_fire_expo_2026_final_260518.json
scoring_rules_v4_final_260518.json
```

`questions_fire_expo_2026_final_260518.json`은 260518 최종본 CSV를 구현용 JSON으로 변환한 파일이다. 총 64개 문항, K-MIES 9문항, 척도별 `scoreMap`, `options`, 표시 순서를 포함한다.

`scoring_rules_v4_final_260518.json`은 ruleVersion `v4-2026-05-18-kmies-9-items`와 척도별 metadata를 분리한 파일이다.

척도 구성은 다음과 같다.

- profile: 1~14
- kmies: 15~23
- phq9: 24~32
- pcl5: 33~52
- kscs: 53~64

K-MIES는 9문항 구조이며 총점 범위는 9~54, high signal 기준은 37 이상이다.
