import type { AnswerValue } from "../types/answer";
import type { Question } from "../types/question";

export function isAnswered(value: AnswerValue | undefined): boolean {
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (typeof value === "string") {
    return value.trim().length > 0;
  }
  return value !== undefined && value !== null;
}

export function isGeneralPublicAnswer(question: Question, value: AnswerValue | undefined): boolean {
  if (question.questionNo !== 3) {
    return false;
  }
  if (value === "q03_opt05") {
    return true;
  }
  return question.options.some((option) => option.value === value && option.label === "일반인");
}

export function isQuestionVisible(
  question: Question,
  getAnswerValue: (questionId: string) => AnswerValue | undefined,
  questions: Question[]
): boolean {
  if (question.questionNo !== 4 && question.questionNo !== 5) {
    return true;
  }
  const q3 = questions.find((candidate) => candidate.questionNo === 3);
  if (!q3) {
    return true;
  }
  return !isGeneralPublicAnswer(q3, getAnswerValue(q3.id));
}
