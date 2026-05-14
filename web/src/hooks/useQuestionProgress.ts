import { useCallback, useEffect, useMemo, useState } from "react";

import { isAnswered, isQuestionVisible } from "../lib/validation";
import {
  getCurrentQuestionNo,
  getQuestionDraft,
  setCurrentQuestionNo,
  setQuestionDraft
} from "../lib/storage";
import type { AnswerValue, BulkAnswersRequest, DraftAnswerMap } from "../types/answer";
import type { Question } from "../types/question";

export function useQuestionProgress(
  eventSlug: string | undefined,
  sessionId: string | undefined,
  questions: Question[]
) {
  const [draft, setDraft] = useState<DraftAnswerMap>({});
  const [currentQuestionNo, setCurrentNo] = useState<number | undefined>(questions[0]?.questionNo);

  useEffect(() => {
    if (!eventSlug || !sessionId || !questions.length) {
      return;
    }
    const restoredDraft = getQuestionDraft(eventSlug, sessionId);
    const restoredNo = getCurrentQuestionNo(eventSlug, sessionId);
    setDraft(restoredDraft);
    setCurrentNo(restoredNo ?? questions[0].questionNo);
  }, [eventSlug, sessionId, questions]);

  const getAnswerValue = useCallback(
    (questionId: string) => draft[questionId]?.answerValue,
    [draft]
  );

  const visibleQuestions = useMemo(
    () => questions.filter((question) => isQuestionVisible(question, getAnswerValue, questions)),
    [getAnswerValue, questions]
  );

  useEffect(() => {
    if (!visibleQuestions.length) {
      return;
    }
    if (!currentQuestionNo || !visibleQuestions.some((question) => question.questionNo === currentQuestionNo)) {
      setCurrentNo(visibleQuestions[0].questionNo);
    }
  }, [currentQuestionNo, visibleQuestions]);

  useEffect(() => {
    if (!eventSlug || !sessionId || !currentQuestionNo) {
      return;
    }
    setCurrentQuestionNo(eventSlug, sessionId, currentQuestionNo);
  }, [currentQuestionNo, eventSlug, sessionId]);

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
      if (target) {
        setCurrentNo(target.questionNo);
      }
    },
    [visibleQuestions]
  );

  const goPrevious = useCallback(() => {
    const previous = visibleQuestions[currentIndex - 1];
    if (previous) {
      setCurrentNo(previous.questionNo);
    }
  }, [currentIndex, visibleQuestions]);

  const goNext = useCallback(() => {
    const next = visibleQuestions[currentIndex + 1];
    if (next) {
      setCurrentNo(next.questionNo);
    }
  }, [currentIndex, visibleQuestions]);

  const missingRequiredQuestionNos = useMemo(
    () =>
      visibleQuestions
        .filter((question) => question.required && !isAnswered(draft[question.id]?.answerValue))
        .map((question) => question.questionNo),
    [draft, visibleQuestions]
  );

  const currentAnswered = currentQuestion
    ? !currentQuestion.required || isAnswered(draft[currentQuestion.id]?.answerValue)
    : false;

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
    totalCount: visibleQuestions.length,
    answeredCount: visibleQuestions.filter((question) => isAnswered(draft[question.id]?.answerValue)).length,
    missingRequiredQuestionNos,
    getAnswerValue,
    updateAnswer,
    goPrevious,
    goNext,
    goToQuestionNo,
    toBulkRequest,
    isFirst: currentIndex <= 0,
    isLast: currentIndex === visibleQuestions.length - 1
  };
}
