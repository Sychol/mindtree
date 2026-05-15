import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getSession } from "../../api/sessions";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { NoticeBox } from "../../components/common/NoticeBox";
import { RetryNotice } from "../../components/common/RetryNotice";
import { MindCardForm } from "../../components/participant/MindCardForm";
import { useMindCard } from "../../hooks/useMindCard";
import { toUserMessage } from "../../lib/errors";
import { routeForSessionStatus, statusAtLeast } from "../../lib/routeGuards";
import {
  clearMindCardDraft,
  getMindCardDraft,
  getStoredSessionId,
  setMindCardDraft
} from "../../lib/storage";
import type { MindCardPromptType } from "../../types/card";
import type { SessionStatusResponse } from "../../types/session";

export function MindCardPage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const sessionId = eventSlug ? getStoredSessionId(eventSlug) : undefined;
  const [sessionState, setSessionState] = useState<SessionStatusResponse | undefined>();
  const [loading, setLoading] = useState(true);
  const [guardError, setGuardError] = useState<string | undefined>();
  const [promptType, setPromptType] = useState<MindCardPromptType>("to_now_me");
  const [content, setContent] = useState(() =>
    eventSlug && sessionId ? getMindCardDraft(eventSlug, sessionId) : ""
  );
  const mindCard = useMindCard(sessionId);

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
        if (!statusAtLeast(next.session.status, "summary_viewed")) {
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

  function updateContent(value: string) {
    setContent(value);
    if (eventSlug && sessionId) {
      setMindCardDraft(eventSlug, sessionId, value);
    }
  }

  async function submit() {
    if (!eventSlug || !sessionId) {
      return;
    }
    const result = await mindCard.submit({ promptType, content });
    if (result) {
      clearMindCardDraft(eventSlug, sessionId);
      navigate(`/e/${encodeURIComponent(eventSlug)}/cards/select`);
    }
  }

  async function retry() {
    if (!eventSlug || !sessionId) {
      return;
    }
    const result = await mindCard.retry();
    if (result) {
      clearMindCardDraft(eventSlug, sessionId);
      navigate(`/e/${encodeURIComponent(eventSlug)}/cards/select`);
    }
  }

  if (loading) {
    return (
      <main className="screen">
        <LoadingState title="마음카드 단계를 준비하고 있습니다" />
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

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">마음카드</p>
        <h1>지금 남기고 싶은 한 문장을 적어 주세요.</h1>
        <p>안전 필터 결과와 관계없이 다음 단계로 이동할 수 있습니다.</p>
      </div>

      <NoticeBox tone="info">
        <p>카드는 익명으로 다른 참가자에게 보일 수 있으며, TV에는 원문이 표시되지 않습니다.</p>
      </NoticeBox>

      <section className="panel">
        <MindCardForm
          content={content}
          onContentChange={updateContent}
          onPromptTypeChange={setPromptType}
          onSubmit={submit}
          pending={mindCard.pending}
          promptType={promptType}
        />
      </section>

      {mindCard.error ? (
        <RetryNotice
          message={mindCard.error}
          onRetry={mindCard.canRetry ? retry : submit}
          pending={mindCard.pending}
        />
      ) : null}
    </main>
  );
}
