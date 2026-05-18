import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getSession } from "../../api/sessions";
import { Button } from "../../components/common/Button";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { NoticeBox } from "../../components/common/NoticeBox";
import { RetryNotice } from "../../components/common/RetryNotice";
import { PeerCardList } from "../../components/participant/PeerCardList";
import { usePublicCards } from "../../hooks/usePublicCards";
import { toUserMessage } from "../../lib/errors";
import { routeForSessionStatus, statusAtLeast } from "../../lib/routeGuards";
import { getStoredSessionId, setSelectedCardId } from "../../lib/storage";
import type { SessionStatusResponse } from "../../types/session";

export function SelectPeerCardPage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const sessionId = eventSlug ? getStoredSessionId(eventSlug) : undefined;
  const [sessionState, setSessionState] = useState<SessionStatusResponse | undefined>();
  const [loading, setLoading] = useState(true);
  const [guardError, setGuardError] = useState<string | undefined>();

  const publicCards = usePublicCards(
    eventSlug,
    sessionId,
    Boolean(sessionState && statusAtLeast(sessionState.session.status, "card_created"))
  );

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

  async function handleSelect(cardId: string) {
    if (!eventSlug || !sessionId) {
      return;
    }
    const selected = await publicCards.choose(cardId);
    if (selected) {
      const selectedCard = publicCards.data?.cards.find((card) => card.id === selected.selectedCardId);
      setSelectedCardId(eventSlug, sessionId, selected.selectedCardId);
      navigate(`/e/${encodeURIComponent(eventSlug)}/replies/new`, {
        state: { selectedCard }
      });
    }
  }

  if (loading || publicCards.loading) {
    return (
      <main className="screen">
        <LoadingState title="공개 가능한 카드를 불러오고 있습니다" />
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

  if (publicCards.error || !publicCards.data) {
    return (
      <main className="screen">
        <div className="screen__header">
          <p className="eyebrow">타인 카드 선택</p>
          <h1>카드 목록을 불러오지 못했습니다.</h1>
        </div>
        <RetryNotice message={publicCards.error} onRetry={publicCards.retry} />
      </main>
    );
  }

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">타인 카드 선택</p>
        <h1>익명 마음카드 하나를 골라 주세요.</h1>
        <p>본인이 작성한 카드는 목록에서 제외됩니다.</p>
      </div>

      {publicCards.data.fallbackUsed ? (
        <NoticeBox tone="warning" title="아직 공개 카드가 부족합니다">
          <p>{publicCards.data.message}</p>
          <p>잠시 후 다시 시도해 주세요. 운영자 예시 카드가 준비되면 이곳에 표시됩니다.</p>
        </NoticeBox>
      ) : (
        <PeerCardList
          cards={publicCards.data.cards}
          onSelect={handleSelect}
          selectingId={publicCards.selectingId}
        />
      )}

      {publicCards.selectError ? (
        <RetryNotice message={publicCards.selectError} pending={Boolean(publicCards.selectingId)} />
      ) : null}

      <div className="action-row action-row--single">
        <Button onClick={publicCards.retry} variant="secondary">
          목록 새로고침
        </Button>
      </div>
    </main>
  );
}
