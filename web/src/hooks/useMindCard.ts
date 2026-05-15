import { useCallback, useState } from "react";

import { createMindCard } from "../api/cards";
import { toUserMessage } from "../lib/errors";
import type { CreateMindCardRequest, CreateMindCardResponse } from "../types/card";

export function useMindCard(sessionId: string | undefined) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [lastPayload, setLastPayload] = useState<CreateMindCardRequest | undefined>();

  const submit = useCallback(
    async (payload: CreateMindCardRequest): Promise<CreateMindCardResponse | undefined> => {
      if (!sessionId || pending) {
        return undefined;
      }
      setPending(true);
      setError(undefined);
      setLastPayload(payload);
      try {
        return await createMindCard(sessionId, payload);
      } catch (submitError) {
        setError(toUserMessage(submitError));
        return undefined;
      } finally {
        setPending(false);
      }
    },
    [pending, sessionId]
  );

  const retry = useCallback(async () => {
    if (!lastPayload) {
      return undefined;
    }
    return submit(lastPayload);
  }, [lastPayload, submit]);

  return {
    pending,
    error,
    canRetry: Boolean(lastPayload),
    submit,
    retry
  };
}
