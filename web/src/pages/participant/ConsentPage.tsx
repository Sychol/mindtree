import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { submitConsent } from "../../api/sessions";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { RetryNotice } from "../../components/common/RetryNotice";
import { ConsentPanel, EMPTY_CONSENT } from "../../components/participant/ConsentPanel";
import { useEventSession } from "../../hooks/useEventSession";
import { toUserMessage } from "../../lib/errors";
import { statusAtLeast } from "../../lib/routeGuards";
import type { ConsentAcceptedItems } from "../../types/session";

export function ConsentPage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const { event, sessionState, loading, error, retry } = useEventSession(eventSlug);
  const [acceptedItems, setAcceptedItems] = useState<ConsentAcceptedItems>(EMPTY_CONSENT);
  const [submitError, setSubmitError] = useState<string | undefined>();
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!eventSlug || !sessionState) {
      return;
    }
    if (statusAtLeast(sessionState.session.status, "consented")) {
      navigate(`/e/${encodeURIComponent(eventSlug)}/questions`, { replace: true });
    }
  }, [eventSlug, navigate, sessionState]);

  async function handleSubmit() {
    if (!event || !sessionState) {
      return;
    }
    setPending(true);
    setSubmitError(undefined);
    try {
      await submitConsent(sessionState.session.id, {
        consentVersion: event.event.consentVersion,
        acceptedItems
      });
      navigate(`/e/${encodeURIComponent(event.event.slug)}/questions`);
    } catch (submitFailure) {
      setSubmitError(toUserMessage(submitFailure));
    } finally {
      setPending(false);
    }
  }

  if (loading) {
    return (
      <main className="screen">
        <LoadingState title="동의 화면을 준비하고 있습니다" />
      </main>
    );
  }

  if (error || !event || !sessionState) {
    return (
      <main className="screen">
        <ErrorState message={error ?? "세션 정보를 확인할 수 없습니다."} onRetry={retry} />
      </main>
    );
  }

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">{event.event.name}</p>
        <h1>참여 동의</h1>
        <p>{event.notices.notDiagnosis}</p>
      </div>
      {submitError ? <RetryNotice message={submitError} onRetry={handleSubmit} pending={pending} /> : null}
      <ConsentPanel
        value={acceptedItems}
        pending={pending}
        onChange={setAcceptedItems}
        onSubmit={handleSubmit}
      />
    </main>
  );
}
