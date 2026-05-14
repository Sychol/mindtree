import { useCallback, useState } from "react";

import { submitAnswersBulk } from "../api/answers";
import { toUserMessage } from "../lib/errors";
import { createIdempotencyKey } from "../lib/retry";
import type { BulkAnswersRequest, BulkAnswersResponse } from "../types/answer";

export function useSubmitWithRetry(sessionId: string | undefined) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [lastPayload, setLastPayload] = useState<BulkAnswersRequest | undefined>();
  const [idempotencyKey, setIdempotencyKey] = useState<string | undefined>();

  const submit = useCallback(
    async (payload: BulkAnswersRequest): Promise<BulkAnswersResponse | undefined> => {
      if (!sessionId || pending) {
        return undefined;
      }

      const nextKey = createIdempotencyKey();
      setPending(true);
      setError(undefined);
      setLastPayload(payload);
      setIdempotencyKey(nextKey);

      try {
        return await submitAnswersBulk(sessionId, payload, nextKey);
      } catch (submitError) {
        setError(toUserMessage(submitError));
        return undefined;
      } finally {
        setPending(false);
      }
    },
    [pending, sessionId]
  );

  const retry = useCallback(async (): Promise<BulkAnswersResponse | undefined> => {
    if (!sessionId || !lastPayload || pending) {
      return undefined;
    }

    setPending(true);
    setError(undefined);
    try {
      return await submitAnswersBulk(sessionId, lastPayload, idempotencyKey ?? createIdempotencyKey());
    } catch (retryError) {
      setError(toUserMessage(retryError));
      return undefined;
    } finally {
      setPending(false);
    }
  }, [idempotencyKey, lastPayload, pending, sessionId]);

  return {
    pending,
    error,
    canRetry: Boolean(lastPayload),
    submit,
    retry
  };
}
