import { useCallback, useEffect, useState } from "react";

import { getQuestions } from "../api/questions";
import { toUserMessage } from "../lib/errors";
import { getQuestionsCache, setQuestionsCache } from "../lib/storage";
import type { Question } from "../types/question";

type QuestionsState = {
  questions: Question[];
  loading: boolean;
  error?: string;
};

function sortQuestions(questions: Question[]): Question[] {
  return [...questions].sort((a, b) => a.displayOrder - b.displayOrder || a.questionNo - b.questionNo);
}

export function usePreloadedQuestions(eventSlug: string | undefined, sessionId: string | undefined) {
  const [state, setState] = useState<QuestionsState>({
    questions: [],
    loading: true
  });

  const load = useCallback(async () => {
    if (!eventSlug || !sessionId) {
      setState({ questions: [], loading: false, error: "세션을 확인할 수 없습니다." });
      return;
    }

    const cached = getQuestionsCache(eventSlug, sessionId);
    if (cached?.length) {
      setState({ questions: sortQuestions(cached), loading: false });
      return;
    }

    setState((current) => ({ ...current, loading: true, error: undefined }));
    try {
      const response = await getQuestions(eventSlug);
      const questions = sortQuestions(response.questions);
      setQuestionsCache(eventSlug, sessionId, questions);
      setState({ questions, loading: false });
    } catch (error) {
      setState({
        questions: [],
        loading: false,
        error: toUserMessage(error)
      });
    }
  }, [eventSlug, sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  return {
    ...state,
    retry: load
  };
}
