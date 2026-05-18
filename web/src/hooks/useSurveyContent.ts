import { useCallback, useEffect, useState } from "react";

import { getPublicSurveyContent } from "../api/events";
import { toUserMessage } from "../lib/errors";
import { DEFAULT_SURVEY_CONFIG } from "../lib/surveySections";
import type { SurveyConfig } from "../types/survey";

type SurveyContentState = {
  surveyConfig: SurveyConfig;
  loading: boolean;
  error?: string;
};

export function useSurveyContent(eventSlug: string | undefined) {
  const [state, setState] = useState<SurveyContentState>({
    surveyConfig: DEFAULT_SURVEY_CONFIG,
    loading: true
  });

  const load = useCallback(async () => {
    if (!eventSlug) {
      setState({ surveyConfig: DEFAULT_SURVEY_CONFIG, loading: false });
      return;
    }
    setState((current) => ({ ...current, loading: true, error: undefined }));
    try {
      const response = await getPublicSurveyContent(eventSlug);
      setState({ surveyConfig: response.surveyConfig, loading: false });
    } catch (error) {
      setState({
        surveyConfig: DEFAULT_SURVEY_CONFIG,
        loading: false,
        error: toUserMessage(error)
      });
    }
  }, [eventSlug]);

  useEffect(() => {
    void load();
  }, [load]);

  return {
    ...state,
    retry: load
  };
}
