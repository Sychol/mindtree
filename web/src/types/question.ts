export type QuestionType =
  | "single_select"
  | "multi_select"
  | "likert"
  | "text"
  | "number";

export type QuestionOptionValue = string | number;

export type QuestionOption = {
  label: string;
  value: QuestionOptionValue;
};

export type ScaleCode = "profile" | "phq9" | "pcl5" | "kmies" | "kscs" | string;

export type Question = {
  id: string;
  questionNo: number;
  scaleCode: ScaleCode;
  questionKey: string;
  title: string;
  description?: string | null;
  questionType: QuestionType;
  required: boolean;
  displayOrder: number;
  options: QuestionOption[];
};

export type QuestionsResponse = {
  questions: Question[];
};
