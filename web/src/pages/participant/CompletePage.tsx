import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getSession } from "../../api/sessions";
import { Button } from "../../components/common/Button";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { NoticeBox } from "../../components/common/NoticeBox";
import { RetryNotice } from "../../components/common/RetryNotice";
import { CompletionCodeBox } from "../../components/participant/CompletionCodeBox";
import { useCompletionCode } from "../../hooks/useCompletionCode";
import { toUserMessage } from "../../lib/errors";
import { routeForSessionStatus, statusAtLeast } from "../../lib/routeGuards";
import { getStoredSessionId } from "../../lib/storage";
import type { SessionStatusResponse } from "../../types/session";
import { cleanupCompletedParticipantStorage } from "../../utils/storageCleanup";

export function CompletePage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const sessionId = eventSlug ? getStoredSessionId(eventSlug) : undefined;
  const [sessionState, setSessionState] = useState<SessionStatusResponse | undefined>();
  const [loading, setLoading] = useState(true);
  const [guardError, setGuardError] = useState<string | undefined>();
  const [showRewardNotice, setShowRewardNotice] = useState(false);

  const completion = useCompletionCode(
    sessionId,
    Boolean(
      sessionState &&
        (statusAtLeast(sessionState.session.status, "completed") ||
          sessionState.progress.completionCodeIssued)
    )
  );

  useEffect(() => {
    if (eventSlug && sessionId && completion.data) {
      cleanupCompletedParticipantStorage(eventSlug, sessionId);
    }
  }, [completion.data, eventSlug, sessionId]);

  useEffect(() => {
    if (!eventSlug || !sessionId) {
      navigate(`/e/${encodeURIComponent(eventSlug ?? "fire-expo-2026")}`, { replace: true });
      return;
    }
    let alive = true;
    setLoading(true);
    getSession(sessionId)
      .then((next) => {
        if (!alive) {
          return;
        }
        setSessionState(next);
        if (!statusAtLeast(next.session.status, "completed") && !next.progress.completionCodeIssued) {
          navigate(routeForSessionStatus(eventSlug, next.session, next.progress), { replace: true });
        }
      })
      .catch((error) => {
        if (alive) {
          setGuardError(toUserMessage(error));
        }
      })
      .finally(() => {
        if (alive) {
          setLoading(false);
        }
      });

    return () => {
      alive = false;
    };
  }, [eventSlug, navigate, sessionId]);

  if (loading || completion.loading) {
    return (
      <main className="screen">
        <LoadingState title="완료 코드를 확인하고 있습니다" />
      </main>
    );
  }

  if (guardError || !eventSlug || !sessionId || !sessionState) {
    return (
      <main className="screen">
        <ErrorState message={guardError ?? "세션을 확인할 수 없습니다."} />
      </main>
    );
  }

  if (completion.error || !completion.data) {
    return (
      <main className="screen">
        <div className="screen__header">
          <p className="eyebrow">완료</p>
          <h1>완료 코드를 불러오지 못했습니다.</h1>
        </div>
        <RetryNotice message={completion.error} onRetry={completion.retry} />
      </main>
    );
  }

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">완료</p>
        <h1>참여가 완료되었습니다.</h1>
        <p>현장 운영자에게 아래 코드를 보여 주세요.</p>
      </div>

      <CompletionCodeBox code={completion.data.completionCode.code} />

      <NoticeBox tone="safe">
        <p>상품 지급 과정에서 이름, 전화번호, 소속 같은 개인정보를 요구하지 않습니다.</p>
      </NoticeBox>

      <section className="panel completion-actions" aria-label="완료 후 이동">
        <a
          className="button button--secondary button--full"
          href={`/display/${encodeURIComponent(eventSlug)}`}
          rel="noreferrer"
          target="_blank"
        >
          TV 마음나무 보기
        </a>
        <Button disabled fullWidth type="button" variant="secondary">
          리본톡 더 알아보기
        </Button>
        <Button fullWidth onClick={() => setShowRewardNotice(true)} type="button">
          참여 상품 받기
        </Button>
      </section>

      {showRewardNotice ? (
        <NoticeBox tone="info" title="참여 상품 받기">
          <p>현장 운영자에게 완료 코드를 보여 주세요. 지급 확인은 이름이나 전화번호가 아니라 완료 코드로 진행됩니다.</p>
        </NoticeBox>
      ) : null}
    </main>
  );
}
