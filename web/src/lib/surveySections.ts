import type { Question } from "../types/question";

export type SurveySectionId =
  | "intro"
  | "consent"
  | "profile"
  | "kmies"
  | "phq9"
  | "pcl5"
  | "kscs"
  | "thanks";

export type SurveySection = {
  id: SurveySectionId;
  sectionNo: number;
  totalSections: number;
  title: string;
  description?: string;
  questionNoRange?: [number, number];
};

export const SURVEY_TOTAL_SECTIONS = 8;

export const SURVEY_SECTIONS: SurveySection[] = [
  {
    id: "intro",
    sectionNo: 1,
    totalSections: SURVEY_TOTAL_SECTIONS,
    title: "리본톡 소개 및 설문"
  },
  {
    id: "consent",
    sectionNo: 2,
    totalSections: SURVEY_TOTAL_SECTIONS,
    title: "연구 참여 동의설명문 및 동의서"
  },
  {
    id: "profile",
    sectionNo: 3,
    totalSections: SURVEY_TOTAL_SECTIONS,
    title: "인구통계",
    questionNoRange: [1, 14]
  },
  {
    id: "kmies",
    sectionNo: 4,
    totalSections: SURVEY_TOTAL_SECTIONS,
    title: "앞서 떠올린 경험에 비추어 응답해주세요.",
    questionNoRange: [15, 20]
  },
  {
    id: "phq9",
    sectionNo: 5,
    totalSections: SURVEY_TOTAL_SECTIONS,
    title: "지난 2주 동안, 아래 나열되는 증상들에 얼마나 자주 시달렸습니까?",
    description: "최근 2주 동안의 상태를 기준으로 응답해 주세요.",
    questionNoRange: [21, 29]
  },
  {
    id: "pcl5",
    sectionNo: 6,
    totalSections: SURVEY_TOTAL_SECTIONS,
    title: "지난 2주 동안, 아래 나열되는 증상들에 얼마나 자주 시달렸습니까?",
    description: "앞서 떠올린 스트레스 경험과 관련해 응답해 주세요.",
    questionNoRange: [30, 49]
  },
  {
    id: "kscs",
    sectionNo: 7,
    totalSections: SURVEY_TOTAL_SECTIONS,
    title: "각 문항을 읽고 평소 자신과 얼마나 일치하는지 체크해 주십시오.",
    questionNoRange: [50, 61]
  },
  {
    id: "thanks",
    sectionNo: 8,
    totalSections: SURVEY_TOTAL_SECTIONS,
    title: "참여해주셔서 감사합니다."
  }
];

export const QUESTION_SURVEY_SECTIONS = SURVEY_SECTIONS.filter(
  (section): section is SurveySection & { questionNoRange: [number, number] } =>
    Boolean(section.questionNoRange)
);

export const TOTAL_SURVEY_SECTIONS = SURVEY_TOTAL_SECTIONS;

export function getQuestionSectionById(sectionId: SurveySectionId | undefined) {
  if (!sectionId) {
    return undefined;
  }
  return QUESTION_SURVEY_SECTIONS.find((section) => section.id === sectionId);
}

export function getQuestionSectionForQuestionNo(questionNo: number) {
  return QUESTION_SURVEY_SECTIONS.find((section) => {
    const [start, end] = section.questionNoRange;
    return questionNo >= start && questionNo <= end;
  });
}

export function getQuestionsForSurveySection(
  questions: Question[],
  section: SurveySection | undefined
) {
  if (!section?.questionNoRange) {
    return [];
  }
  const [start, end] = section.questionNoRange;
  return questions.filter((question) => question.questionNo >= start && question.questionNo <= end);
}
