import type { Question } from "../../types/question";

const SECTION_LABELS: Record<string, string> = {
  profile: "기본 정보",
  phq9: "기분",
  pcl5: "경험 반응",
  kmies: "현장 마음",
  kscs: "자기돌봄"
};

type QuestionSectionTabsProps = {
  questions: Question[];
  currentQuestionNo: number;
  onSelectQuestionNo: (questionNo: number) => void;
};

export function sectionLabel(scaleCode: string): string {
  return SECTION_LABELS[scaleCode] ?? scaleCode;
}

export function QuestionSectionTabs({
  questions,
  currentQuestionNo,
  onSelectQuestionNo
}: QuestionSectionTabsProps) {
  const sections = Array.from(
    questions.reduce((map, question) => {
      if (!map.has(question.scaleCode)) {
        map.set(question.scaleCode, question.questionNo);
      }
      return map;
    }, new Map<string, number>())
  );
  const current = questions.find((question) => question.questionNo === currentQuestionNo);

  return (
    <nav className="section-tabs" aria-label="문항 섹션">
      {sections.map(([scaleCode, firstQuestionNo]) => (
        <button
          type="button"
          key={scaleCode}
          className={scaleCode === current?.scaleCode ? "section-tabs__item is-active" : "section-tabs__item"}
          onClick={() => onSelectQuestionNo(firstQuestionNo)}
        >
          {sectionLabel(scaleCode)}
        </button>
      ))}
    </nav>
  );
}
