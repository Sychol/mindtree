import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { getSession } from "../../api/sessions";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { NoticeBox } from "../../components/common/NoticeBox";
import { RetryNotice } from "../../components/common/RetryNotice";
import { ReplyForm } from "../../components/participant/ReplyForm";
import { useReply } from "../../hooks/useReply";
import { toUserMessage } from "../../lib/errors";
import { routeForSessionStatus, statusAtLeast } from "../../lib/routeGuards";
import {
  clearReplyDraft,
  getReplyDraft,
  getSelectedCardId,
  getStoredSessionId,
  setReplyDraft
} from "../../lib/storage";
import type { PublicCard } from "../../types/card";
import type { ReplyType } from "../../types/reply";
import type { SessionStatusResponse } from "../../types/session";

type LocationState = {
  selectedCard?: PublicCard;
};

export function ReplyPage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const selectedCard = (location.state as LocationState | null)?.selectedCard;
  const sessionId = eventSlug ? getStoredSessionId(eventSlug) : undefined;
  const selectedCardId = eventSlug && sessionId ? getSelectedCardId(eventSlug, sessionId) : undefined;
  const [sessionState, setSessionState] = useState<SessionStatusResponse | undefined>();
  const [loading, setLoading] = useState(true);
  const [guardError, setGuardError] = useState<string | undefined>();
  const [replyType, setReplyType] = useState<ReplyType>("comfort");
  const [content, setContent] = useState(() =>
    eventSlug && sessionId ? getReplyDraft(eventSlug, sessionId) : ""
  );
  const reply = useReply(sessionId);

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
        if (!statusAtLeast(next.session.status, "card_created")) {
          navigate(routeForSessionStatus(eventSlug, next.session, next.progress), { replace: true });
          return;
        }
        if (!selectedCardId) {
          navigate(`/e/${encodeURIComponent(eventSlug)}/cards/select`, { replace: true });
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
  }, [eventSlug, navigate, selectedCardId, sessionId]);

  function updateContent(value: string) {
    setContent(value);
    if (eventSlug && sessionId) {
      setReplyDraft(eventSlug, sessionId, value);
    }
  }

  async function submit() {
    if (!eventSlug || !sessionId || !selectedCardId) {
      return;
    }
    const result = await reply.submit({
      targetCardId: selectedCardId,
      replyType,
      content
    });
    if (result) {
      clearReplyDraft(eventSlug, sessionId);
      navigate(`/e/${encodeURIComponent(eventSlug)}/complete`);
    }
  }

  async function retry() {
    if (!eventSlug || !sessionId) {
      return;
    }
    const result = await reply.retry();
    if (result) {
      clearReplyDraft(eventSlug, sessionId);
      navigate(`/e/${encodeURIComponent(eventSlug)}/complete`);
    }
  }

  if (loading) {
    return (
      <main className="screen">
        <LoadingState title="응원 문장 단계를 준비하고 있습니다" />
      </main>
    );
  }

  if (guardError || !eventSlug || !sessionId || !sessionState || !selectedCardId) {
    return (
      <main className="screen">
        <ErrorState message={guardError ?? "선택된 카드를 확인할 수 없습니다."} />
      </main>
    );
  }

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">응원 문장</p>
        <h1>선택한 마음카드에 건네고 싶은 말을 남겨 주세요.</h1>
      </div>

      {selectedCard ? (
        <section className="panel peer-card peer-card--selected">
          <p className="peer-card__eyebrow">선택한 카드</p>
          <p className="peer-card__content">{selectedCard.content}</p>
        </section>
      ) : (
        <NoticeBox tone="info">
          <p>선택한 카드에 대한 응원 문장을 작성합니다.</p>
        </NoticeBox>
      )}

      <section className="panel">
        <ReplyForm
          content={content}
          onContentChange={updateContent}
          onReplyTypeChange={setReplyType}
          onSubmit={submit}
          pending={reply.pending}
          replyType={replyType}
        />
      </section>

      {reply.error ? (
        <RetryNotice
          message={reply.error}
          onRetry={reply.canRetry ? retry : submit}
          pending={reply.pending}
        />
      ) : null}
    </main>
  );
}
