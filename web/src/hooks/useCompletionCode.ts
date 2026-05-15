import { useCallback, useEffect, useState } from "react";

import { getCompletionCode } from "../api/completion";
import { toUserMessage } from "../lib/errors";
import type { CompletionCodeResponse } from "../types/completion";

export function useCompletionCode(sessionId: string | undefined, enabled: boolean) {
  const [data, setData] = useState<CompletionCodeResponse | undefined>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  const load = useCallback(async () => {
    if (!sessionId || !enabled) {
      return;
    }
    setLoading(true);
    setError(undefined);
    try {
      setData(await getCompletionCode(sessionId));
    } catch (loadError) {
      setError(toUserMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [enabled, sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  return {
    data,
    loading,
    error,
    retry: load
  };
}
