import type { QuestionType, ScaleCode } from "./question";

export type SurveyIntroConfig = {
  title: string;
  subtitle?: string | null;
  paragraphs: string[];
  showLogo: boolean;
  showAppScreens: boolean;
};

export type SurveyConsentSection = {
  heading: string;
  paragraphs: string[];
};

export type SurveyConsentItemKey =
  | "researchParticipationConsent"
  | "personalDataUseConsent"
  | "sensitiveInfoConsent"
  | "deidentifiedAiRagUseConsent";

export type SurveyConsentItem = {
  key: SurveyConsentItemKey;
  label: string;
  description: string;
  required: boolean;
};

export type SurveyConsentConfig = {
  title: string;
  sections: SurveyConsentSection[];
  items: SurveyConsentItem[];
};

export type SurveySectionConfig = {
  id: string;
  sectionNo: number;
  title: string;
  description?: string | null;
  questionNoRange?: [number, number] | null;
};

export type SurveyQuestionOverride = {
  title?: string | null;
  description?: string | null;
};

export type SurveyThanksConfig = {
  title: string;
  paragraphs: string[];
};

export type SurveyConfig = {
  version: string;
  intro: SurveyIntroConfig;
  consent: SurveyConsentConfig;
  sections: SurveySectionConfig[];
  questionOverrides: Record<string, SurveyQuestionOverride>;
  thanks: SurveyThanksConfig;
};

export type SurveySectionSummary = SurveySectionConfig & {
  questionCount: number;
  requiredCount: number;
};

export type AdminSurveyQuestionItem = {
  id: string;
  questionNo: number;
  questionKey: string;
  scaleCode: ScaleCode;
  questionType: QuestionType;
  title: string;
  displayTitle: string;
  description?: string | null;
  displayDescription?: string | null;
  required: boolean;
  optionsCount: number;
  editable: {
    title: boolean;
    description: boolean;
    questionNo: boolean;
    questionKey: boolean;
    scaleCode: boolean;
    questionType: boolean;
    scoreMap: boolean;
    options: boolean;
    required: boolean;
  };
};

export type AdminSurveyQuestionsBySection = {
  sectionId: string;
  sectionNo: number;
  title: string;
  questions: AdminSurveyQuestionItem[];
};

export type AdminSurveyResponse = {
  event: {
    slug: string;
    name: string;
    status: string;
    consentVersion: string;
  };
  surveyConfig: SurveyConfig;
  sectionSummaries: SurveySectionSummary[];
  questionsBySection: AdminSurveyQuestionsBySection[];
};

export type PublicSurveyContentResponse = {
  eventSlug: string;
  surveyConfig: SurveyConfig;
};

export type SurveyIntroUpdateRequest = SurveyIntroConfig & {
  reason?: string | null;
};

export type SurveyConsentUpdateRequest = SurveyConsentConfig & {
  reason?: string | null;
};

export type SurveySectionUpdateRequest = {
  title: string;
  description?: string | null;
  reason?: string | null;
};

export type SurveyQuestionPresentationUpdateRequest = {
  title?: string | null;
  description?: string | null;
  reason?: string | null;
};

export type SurveyThanksUpdateRequest = SurveyThanksConfig & {
  reason?: string | null;
};

export type SurveyResetRequest = {
  reason?: string | null;
};

export type AdminSurveyMutationResponse = {
  surveyConfig: SurveyConfig;
  auditLogCreated: boolean;
};
