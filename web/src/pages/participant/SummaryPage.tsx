import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getSession } from "../../api/sessions";
import { Button } from "../../components/common/Button";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { NoticeBox } from "../../components/common/NoticeBox";
import { RetryNotice } from "../../components/common/RetryNotice";
import { HelpNotice } from "../../components/participant/HelpNotice";
import { useSummary } from "../../hooks/useSummary";
import { toUserMessage } from "../../lib/errors";
import { routeForSessionStatus, statusAtLeast } from "../../lib/routeGuards";
import { getStoredSessionId } from "../../lib/storage";
import type { SessionStatusResponse } from "../../types/session";

export function SummaryPage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const sessionId = eventSlug ? getStoredSessionId(eventSlug) : undefined;
  const [sessionState, setSessionState] = useState<SessionStatusResponse | undefined>();
  const [checkingSession, setCheckingSession] = useState(true);
  const [guardError, setGuardError] = useState<string | undefined>();

  const summaryState = useSummary(
    sessionId,
    Boolean(sessionState && statusAtLeast(sessionState.session.status, "questions_completed"))
  );

  useEffect(() => {
    if (!eventSlug || !sessionId) {
      navigate(`/e/${encodeURIComponent(eventSlug ?? "fire-expo-2026")}`, { replace: true });
      return;
    }

    let alive = true;
    setCheckingSession(true);
    getSession(sessionId)
      .then((nextSession) => {
        if (!alive) {
          return;
        }
        setSessionState(nextSession);
        if (!statusAtLeast(nextSession.session.status, "questions_completed")) {
          navigate(routeForSessionStatus(eventSlug, nextSession.session, nextSession.progress), {
            replace: true
          });
        }
      })
      .catch((error) => {
        if (alive) {
          setGuardError(toUserMessage(error));
        }
      })
      .finally(() => {
        if (alive) {
          setCheckingSession(false);
        }
      });

    return () => {
      alive = false;
    };
  }, [eventSlug, navigate, sessionId]);

  async function handleNext() {
    if (!eventSlug) {
      return;
    }
    const viewed = await summaryState.markViewed();
    if (viewed) {
      navigate(`/e/${encodeURIComponent(eventSlug)}/cards/new`);
    }
  }

  if (checkingSession || summaryState.loading) {
    return (
      <main className="screen">
        <LoadingState title="마음신호 요약을 준비하고 있습니다" />
      </main>
    );
  }

  if (guardError || !eventSlug || !sessionId) {
    return (
      <main className="screen">
        <ErrorState message={guardError ?? "세션을 확인할 수 없습니다."} />
      </main>
    );
  }

  if (summaryState.error || !summaryState.summary) {
    return (
      <main className="screen">
        <div className="screen__header">
          <p className="eyebrow">마음신호 요약</p>
          <h1>요약을 불러오지 못했습니다.</h1>
        </div>
        <RetryNotice message={summaryState.error} onRetry={summaryState.retry} />
      </main>
    );
  }

  const { summary, riskNotice } = summaryState.summary;

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">마음신호 요약</p>
        <h1>지금의 마음 신호를 살펴봤습니다.</h1>
        <p>이 결과는 진단이나 치료가 아닌 체험형 마음 점검 안내입니다.</p>
      </div>

      <section className="panel summary-panel">
        <p className="summary-panel__text">{summary.finalText}</p>
        {summary.generationMode ? (
          <p className="summary-panel__meta">요약 방식: {summary.generationMode}</p>
        ) : null}
      </section>

      {summary.signals?.length ? (
        <section className="panel summary-section">
          <h2>살펴볼 신호</h2>
          <ul className="signal-list">
            {summary.signals.map((signal) => (
              <li key={signal}>{signal}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {summary.recommendedAction ? (
        <NoticeBox tone="safe" title="지금 해볼 수 있는 작은 행동">
          <p>{summary.recommendedAction}</p>
        </NoticeBox>
      ) : null}

      <HelpNotice riskNotice={riskNotice} />

      {summaryState.viewError ? (
        <RetryNotice
          message={summaryState.viewError}
          onRetry={handleNext}
          pending={summaryState.viewing}
        />
      ) : null}

      <div className="action-row action-row--single">
        <Button fullWidth disabled={summaryState.viewing} onClick={handleNext}>
          {summaryState.viewing ? "확인 중" : "다음 단계로 이동"}
        </Button>
      </div>
    </main>
  );
}
