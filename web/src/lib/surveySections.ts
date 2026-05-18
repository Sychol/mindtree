import type { Question } from "../types/question";
import type { SurveyConfig, SurveySectionConfig } from "../types/survey";

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

export const DEFAULT_SURVEY_CONFIG: SurveyConfig = {
  version: "v1",
  intro: {
    title: "리본톡 소개 및 설문",
    subtitle: "소방안전박람회 마음 점검",
    paragraphs: [
      "리본톡은 소방공무원 등 재난 현장에서 강한 외상 사건을 반복적으로 경험하는 분들의 트라우마 예방과 회복을 돕기 위한 공감 기반 AI 심리상담 앱입니다.",
      "리본톡은 진단이나 치료를 대신하는 의료서비스가 아니라, 언제든지 접근 가능한 심리적 지지 도구로서 추후 필요 시 전문 상담·치료로 연결되는 다리 역할을 목표로 하고 있습니다."
    ],
    showLogo: true,
    showAppScreens: true
  },
  consent: {
    title: "연구 참여 동의설명문 및 동의서",
    sections: [
      {
        heading: "1. 연구 목적",
        paragraphs: [
          "본 설문은 소방 및 재난 대응 관련 종사자의 심리적 어려움을 파악하여 회복을 돕는 AI 상담 서비스 리본톡 개발 및 학술연구의 기초자료로 활용하기 위한 것입니다."
        ]
      },
      {
        heading: "2. 연구대상자의 참여기간, 절차 및 방법",
        paragraphs: [
          "본 연구는 온라인 설문 방식으로 진행됩니다. 연구대상자는 연구 설명문을 확인한 뒤 연구 참여 동의 여부를 선택합니다. 동의한 경우에만 설문 문항으로 이동하며, 설문은 1회 참여로 진행되고 예상 소요시간은 약 15~20분입니다."
        ]
      },
      {
        heading: "3. 연구대상자에게 예상되는 위험 및 이득",
        paragraphs: [
          "본 연구 참여로 인한 특별한 신체적 위험은 없습니다. 다만 일부 문항은 심리적 어려움과 관련된 내용을 포함하므로 응답 중 일시적인 불편감을 느낄 수 있습니다. 불편감이 느껴질 경우 언제든지 설문을 중단할 수 있으며 이에 따른 불이익은 없습니다."
        ]
      },
      {
        heading: "4. 개인정보 보호에 관한 사항",
        paragraphs: [
          "본 연구는 이름, 연락처, 주민등록번호 등 직접 식별정보를 수집하지 않습니다. 수집된 자료는 연구 목적에 한하여 사용되며, 연구 결과는 개인을 식별할 수 없는 통계자료 또는 비식별화된 형태로만 제시됩니다."
        ]
      },
      {
        heading: "5. 연구 참여에 따른 손실에 대한 보상",
        paragraphs: ["본 연구 참여로 인한 특별한 손실이나 위험은 없습니다. 다만 설문 작성에 약 15~20분 정도가 소요될 수 있습니다."]
      },
      {
        heading: "6. 개인정보 제공 및 보관기간에 관한 내용",
        paragraphs: [
          "수집된 설문 자료는 비식별화하여 연구 목적에 한해 사용합니다. 자료는 접근 권한이 제한된 연구자 계정 또는 암호화된 저장공간에 보관하며, 연구 종료 후 3년간 보관한 뒤 복구가 불가능한 방식으로 삭제 또는 폐기합니다."
        ]
      },
      {
        heading: "7. 동의의 철회에 관한 사항",
        paragraphs: [
          "연구 참여는 자발적이며, 언제든지 불이익 없이 중단할 수 있습니다. 제출 전에는 설문 작성을 중단하거나 창을 닫는 방식으로 참여를 철회할 수 있습니다. 제출 이후에는 특정 응답을 식별하기 어려워 개별 자료 삭제가 제한될 수 있습니다."
        ]
      },
      {
        heading: "8. 연구 관련 문의",
        paragraphs: ["담당연구원: 최동혁 / 소속: 트래시스(주) / 이메일: trasys21@nate.com / 연락처: 062-653-5151"]
      }
    ],
    items: [
      {
        key: "researchParticipationConsent",
        label: "[필수] 연구 참여 동의",
        description:
          "본인은 연구의 목적, 절차, 예상 소요시간, 예상되는 불편감, 연구 참여 중단 및 철회 가능성에 대한 설명을 확인하였으며, 자발적으로 본 연구에 참여하는 것에 동의합니다.",
        required: true
      },
      {
        key: "personalDataUseConsent",
        label: "[필수] 개인정보 수집·이용 동의",
        description:
          "본인은 연구자가 연령대, 성별, 직무 관련 정보, 사건 경험 관련 정보, 설문 응답자료를 수집하고, 이를 연구 목적의 통계 분석, 학술연구 및 서비스 개선에 이용하는 것에 동의합니다.",
        required: true
      },
      {
        key: "sensitiveInfoConsent",
        label: "[필수] 민감정보 처리 동의",
        description:
          "본인은 본 설문에 우울감, 자해 관련 생각, 외상 경험, 심리적 고통, 상담·병원 이용 경험 등 건강 또는 정신건강과 관련될 수 있는 문항이 포함되어 있음을 확인하였으며, 해당 정보를 연구 목적의 분석에 이용하는 것에 동의합니다.",
        required: true
      },
      {
        key: "deidentifiedAiRagUseConsent",
        label: "[필수] 비식별 자료의 AI 학습/RAG 활용 동의",
        description:
          "본인은 본 설문에서 수집된 응답자료가 익명화·가명화 등 비식별 처리된 후, AI 상담 서비스 리본톡의 성능 개선, AI 학습 데이터 구축 또는 RAG 데이터 구축에 활용될 수 있음에 동의합니다.",
        required: true
      }
    ]
  },
  sections: SURVEY_SECTIONS,
  questionOverrides: {},
  thanks: {
    title: "참여해주셔서 감사합니다.",
    paragraphs: ["응답이 저장되었습니다.", "이제 마음신호 요약을 확인할 수 있습니다."]
  }
};

export function getConfiguredSurveySection(
  config: SurveyConfig | undefined,
  fallback: SurveySection | undefined
): SurveySection | undefined {
  if (!fallback) {
    return undefined;
  }
  const override = config?.sections.find((section) => section.id === fallback.id);
  if (!override) {
    return fallback;
  }
  return {
    ...fallback,
    title: override.title || fallback.title,
    description: override.description ?? fallback.description,
    questionNoRange: (override.questionNoRange as SurveySection["questionNoRange"]) ?? fallback.questionNoRange
  };
}

export function getConfiguredSectionById(
  config: SurveyConfig | undefined,
  sectionId: string
): SurveySectionConfig | undefined {
  return config?.sections.find((section) => section.id === sectionId);
}

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
