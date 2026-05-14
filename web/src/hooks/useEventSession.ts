import { useCallback, useEffect, useState } from "react";

import { getPublicEvent } from "../api/events";
import { createOrResumeSession, getSession } from "../api/sessions";
import { toUserMessage } from "../lib/errors";
import {
  getStoredResumeToken,
  setStoredResumeToken,
  setStoredSessionId
} from "../lib/storage";
import type { PublicEventResponse } from "../types/event";
import type { SessionStatusResponse } from "../types/session";

type EventSessionState = {
  event?: PublicEventResponse;
  sessionState?: SessionStatusResponse;
  loading: boolean;
  error?: string;
};

function clientMeta() {
  return {
    device: "mobile",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
  };
}

export function useEventSession(eventSlug: string | undefined) {
  const [state, setState] = useState<EventSessionState>({ loading: true });

  const bootstrap = useCallback(async () => {
    if (!eventSlug) {
      setState({ loading: false, error: "이벤트 주소가 올바르지 않습니다." });
      return;
    }

    setState((current) => ({ ...current, loading: true, error: undefined }));
    try {
      const event = await getPublicEvent(eventSlug);
      const resumeToken = getStoredResumeToken(eventSlug);
      const sessionResponse = await createOrResumeSession(eventSlug, {
        resumeToken,
        clientMeta: clientMeta()
      });

      setStoredResumeToken(eventSlug, sessionResponse.resumeToken);
      setStoredSessionId(eventSlug, sessionResponse.session.id);

      const sessionState = await getSession(sessionResponse.session.id);
      setState({
        event,
        sessionState,
        loading: false
      });
    } catch (error) {
      setState({
        loading: false,
        error: toUserMessage(error)
      });
    }
  }, [eventSlug]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  return {
    ...state,
    retry: bootstrap
  };
}
