import { useCallback, useState } from "react";

import { createReply } from "../api/replies";
import { toUserMessage } from "../lib/errors";
import type { CreateReplyRequest, CreateReplyResponse } from "../types/reply";

export function useReply(sessionId: string | undefined) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [lastPayload, setLastPayload] = useState<CreateReplyRequest | undefined>();

  const submit = useCallback(
    async (payload: CreateReplyRequest): Promise<CreateReplyResponse | undefined> => {
      if (!sessionId || pending) {
        return undefined;
      }
      setPending(true);
      setError(undefined);
      setLastPayload(payload);
      try {
        return await createReply(sessionId, payload);
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
