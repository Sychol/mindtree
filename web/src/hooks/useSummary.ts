import { useCallback, useEffect, useState } from "react";

import { getSummary, markSummaryViewed } from "../api/summaries";
import { toUserMessage } from "../lib/errors";
import type { SummaryResponse, SummaryViewedResponse } from "../types/summary";

type SummaryState = {
  summary?: SummaryResponse;
  viewed?: SummaryViewedResponse;
  loading: boolean;
  error?: string;
  viewing: boolean;
  viewError?: string;
};

export function useSummary(sessionId: string | undefined, enabled = true) {
  const [state, setState] = useState<SummaryState>({
    loading: Boolean(sessionId && enabled),
    viewing: false
  });

  const load = useCallback(async () => {
    if (!sessionId || !enabled) {
      setState((current) => ({
        ...current,
        loading: false,
        error: sessionId ? undefined : "세션을 확인할 수 없습니다."
      }));
      return;
    }

    setState((current) => ({ ...current, loading: true, error: undefined }));
    try {
      const summary = await getSummary(sessionId);
      setState((current) => ({
        ...current,
        summary,
        loading: false,
        error: undefined
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: toUserMessage(error)
      }));
    }
  }, [enabled, sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  const markViewed = useCallback(async (): Promise<SummaryViewedResponse | undefined> => {
    if (!sessionId || state.viewing) {
      return undefined;
    }

    setState((current) => ({ ...current, viewing: true, viewError: undefined }));
    try {
      const viewed = await markSummaryViewed(sessionId);
      setState((current) => ({
        ...current,
        viewed,
        viewing: false,
        viewError: undefined
      }));
      return viewed;
    } catch (error) {
      setState((current) => ({
        ...current,
        viewing: false,
        viewError: toUserMessage(error)
      }));
      return undefined;
    }
  }, [sessionId, state.viewing]);

  return {
    ...state,
    retry: load,
    markViewed
  };
}
