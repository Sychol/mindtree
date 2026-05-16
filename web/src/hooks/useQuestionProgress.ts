import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getQuestionSectionById,
  getQuestionSectionForQuestionNo,
  getQuestionsForSurveySection,
  QUESTION_SURVEY_SECTIONS
} from "../lib/surveySections";
import { isAnswered, isQuestionVisible } from "../lib/validation";
import {
  getCurrentQuestionNo,
  getCurrentSurveySectionId,
  getQuestionDraft,
  setCurrentQuestionNo,
  setCurrentSurveySectionId,
  setQuestionDraft
} from "../lib/storage";
import type { SurveySectionId } from "../lib/surveySections";
import type { AnswerValue, BulkAnswersRequest, DraftAnswerMap } from "../types/answer";
import type { Question } from "../types/question";

const FIRST_QUESTION_SECTION_ID: SurveySectionId = "profile";

export function useQuestionProgress(
  eventSlug: string | undefined,
  sessionId: string | undefined,
  questions: Question[]
) {
  const [draft, setDraft] = useState<DraftAnswerMap>({});
  const [currentQuestionNo, setCurrentNo] = useState<number | undefined>(questions[0]?.questionNo);
  const [currentSectionId, setCurrentSectionId] =
    useState<SurveySectionId>(FIRST_QUESTION_SECTION_ID);

  useEffect(() => {
    if (!eventSlug || !sessionId || !questions.length) {
      return;
    }
    const restoredDraft = getQuestionDraft(eventSlug, sessionId);
    const restoredNo = getCurrentQuestionNo(eventSlug, sessionId);
    const restoredSectionId = getCurrentSurveySectionId(eventSlug, sessionId);
    const restoredQuestionSection = restoredNo ? getQuestionSectionForQuestionNo(restoredNo) : undefined;
    const nextSection =
      getQuestionSectionById(restoredSectionId)?.id ??
      restoredQuestionSection?.id ??
      FIRST_QUESTION_SECTION_ID;

    setDraft(restoredDraft);
    setCurrentNo(restoredNo ?? questions[0].questionNo);
    setCurrentSectionId(nextSection);
  }, [eventSlug, sessionId, questions]);

  const getAnswerValue = useCallback(
    (questionId: string) => draft[questionId]?.answerValue,
    [draft]
  );

  const visibleQuestions = useMemo(
    () => questions.filter((question) => isQuestionVisible(question, getAnswerValue, questions)),
    [getAnswerValue, questions]
  );

  const currentSection =
    getQuestionSectionById(currentSectionId) ?? getQuestionSectionById(FIRST_QUESTION_SECTION_ID);

  const currentSectionQuestions = useMemo(
    () => getQuestionsForSurveySection(visibleQuestions, currentSection),
    [currentSection, visibleQuestions]
  );

  const currentSectionIndex = Math.max(
    0,
    QUESTION_SURVEY_SECTIONS.findIndex((section) => section.id === currentSection?.id)
  );

  useEffect(() => {
    if (!currentSection) {
      return;
    }
    const firstInSection = currentSectionQuestions[0];
    if (!firstInSection) {
      return;
    }
    if (
      !currentQuestionNo ||
      !currentSectionQuestions.some((question) => question.questionNo === currentQuestionNo)
    ) {
      setCurrentNo(firstInSection.questionNo);
    }
  }, [currentQuestionNo, currentSection, currentSectionQuestions]);

  useEffect(() => {
    if (!eventSlug || !sessionId || !currentQuestionNo) {
      return;
    }
    setCurrentQuestionNo(eventSlug, sessionId, currentQuestionNo);
  }, [currentQuestionNo, eventSlug, sessionId]);

  useEffect(() => {
    if (!eventSlug || !sessionId || !currentSection) {
      return;
    }
    setCurrentSurveySectionId(eventSlug, sessionId, currentSection.id);
  }, [currentSection, eventSlug, sessionId]);

  const currentIndex = Math.max(
    0,
    visibleQuestions.findIndex((question) => question.questionNo === currentQuestionNo)
  );
  const currentQuestion = visibleQuestions[currentIndex];

  const updateAnswer = useCallback(
    (question: Question, answerValue: AnswerValue | undefined) => {
      setDraft((current) => {
        const next = { ...current };
        if (answerValue === undefined || (Array.isArray(answerValue) && answerValue.length === 0)) {
          delete next[question.id];
        } else {
          next[question.id] = {
            questionId: question.id,
            questionNo: question.questionNo,
            answerValue
          };
        }
        if (eventSlug && sessionId) {
          setQuestionDraft(eventSlug, sessionId, next);
        }
        return next;
      });
    },
    [eventSlug, sessionId]
  );

  const goToQuestionNo = useCallback(
    (questionNo: number) => {
      const target = visibleQuestions.find((question) => question.questionNo === questionNo);
      const targetSection = getQuestionSectionForQuestionNo(questionNo);
      if (target && targetSection) {
        setCurrentNo(target.questionNo);
        setCurrentSectionId(targetSection.id);
      }
    },
    [visibleQuestions]
  );

  const goToSectionId = useCallback(
    (sectionId: SurveySectionId) => {
      const targetSection = getQuestionSectionById(sectionId);
      if (!targetSection) {
        return;
      }
      const firstQuestion = getQuestionsForSurveySection(visibleQuestions, targetSection)[0];
      setCurrentSectionId(targetSection.id);
      if (firstQuestion) {
        setCurrentNo(firstQuestion.questionNo);
      }
    },
    [visibleQuestions]
  );

  const goPrevious = useCallback(() => {
    const previous = visibleQuestions[currentIndex - 1];
    if (previous) {
      setCurrentNo(previous.questionNo);
      const previousSection = getQuestionSectionForQuestionNo(previous.questionNo);
      if (previousSection) {
        setCurrentSectionId(previousSection.id);
      }
    }
  }, [currentIndex, visibleQuestions]);

  const goNext = useCallback(() => {
    const next = visibleQuestions[currentIndex + 1];
    if (next) {
      setCurrentNo(next.questionNo);
      const nextSection = getQuestionSectionForQuestionNo(next.questionNo);
      if (nextSection) {
        setCurrentSectionId(nextSection.id);
      }
    }
  }, [currentIndex, visibleQuestions]);

  const goPreviousSection = useCallback(() => {
    const previousSection = QUESTION_SURVEY_SECTIONS[currentSectionIndex - 1];
    if (previousSection) {
      goToSectionId(previousSection.id);
    }
  }, [currentSectionIndex, goToSectionId]);

  const goNextSection = useCallback(() => {
    const nextSection = QUESTION_SURVEY_SECTIONS[currentSectionIndex + 1];
    if (nextSection) {
      goToSectionId(nextSection.id);
    }
  }, [currentSectionIndex, goToSectionId]);

  const getMissingRequiredQuestionNosForSection = useCallback(
    (section = currentSection) =>
      getQuestionsForSurveySection(visibleQuestions, section)
        .filter((question) => question.required && !isAnswered(draft[question.id]?.answerValue))
        .map((question) => question.questionNo),
    [currentSection, draft, visibleQuestions]
  );

  const missingRequiredQuestionNos = useMemo(
    () =>
      visibleQuestions
        .filter((question) => question.required && !isAnswered(draft[question.id]?.answerValue))
        .map((question) => question.questionNo),
    [draft, visibleQuestions]
  );

  const missingRequiredQuestionNosForSection = useMemo(
    () => getMissingRequiredQuestionNosForSection(currentSection),
    [currentSection, getMissingRequiredQuestionNosForSection]
  );

  const currentAnswered = currentQuestion
    ? !currentQuestion.required || isAnswered(draft[currentQuestion.id]?.answerValue)
    : false;

  const sectionAnsweredCount = currentSectionQuestions.filter((question) =>
    isAnswered(draft[question.id]?.answerValue)
  ).length;

  const answeredCount = visibleQuestions.filter((question) =>
    isAnswered(draft[question.id]?.answerValue)
  ).length;

  const toBulkRequest = useCallback((): BulkAnswersRequest => {
    const answers = visibleQuestions
      .map((question) => draft[question.id])
      .filter((answer): answer is NonNullable<typeof answer> => Boolean(answer))
      .map((answer) => ({
        questionId: answer.questionId,
        answerValue: answer.answerValue
      }));

    return {
      answers,
      clientProgress: {
        lastQuestionNo: visibleQuestions.at(-1)?.questionNo
      }
    };
  }, [draft, visibleQuestions]);

  return {
    draft,
    visibleQuestions,
    currentQuestion,
    currentIndex,
    currentAnswered,
    currentSection,
    currentSectionId: currentSection?.id ?? FIRST_QUESTION_SECTION_ID,
    currentSectionIndex,
    currentSectionQuestions,
    sectionAnsweredCount,
    sectionTotalCount: currentSectionQuestions.length,
    totalCount: visibleQuestions.length,
    answeredCount,
    missingRequiredQuestionNos,
    missingRequiredQuestionNosForSection,
    getMissingRequiredQuestionNosForSection,
    getAnswerValue,
    updateAnswer,
    goPrevious,
    goNext,
    goPreviousSection,
    goNextSection,
    goToQuestionNo,
    goToSectionId,
    toBulkRequest,
    isFirst: currentIndex <= 0,
    isLast: currentIndex === visibleQuestions.length - 1,
    isFirstQuestionSection: currentSectionIndex <= 0,
    isLastQuestionSection: currentSectionIndex === QUESTION_SURVEY_SECTIONS.length - 1
  };
}
