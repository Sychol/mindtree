import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { deleteMindCard, listMyMindCards, updateMindCard } from "../../api/cards";
import { getPublicEvent } from "../../api/events";
import { getSession } from "../../api/sessions";
import { Button } from "../../components/common/Button";
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
import type { CreateMindCardResponse, MindCard } from "../../types/card";
import type { SessionStatusResponse } from "../../types/session";

const DEFAULT_MAX_MIND_CARDS = 3;
const STRESS_MEMORY_PROMPT_TYPE = "stress_memory";

const SAFETY_LABELS: Record<string, string> = {
  safe: "안전",
  review: "검수 필요",
  exclude: "공개 제외"
};

const PUBLIC_LABELS: Record<string, string> = {
  public: "공개 가능",
  pending: "공개 보류",
  hidden: "숨김",
  excluded: "공개 제외"
};

function maxMindCardsFromSetting(value: number | undefined): number {
  const parsed = Number(value ?? DEFAULT_MAX_MIND_CARDS);
  if (!Number.isFinite(parsed)) {
    return DEFAULT_MAX_MIND_CARDS;
  }
  return Math.max(1, Math.min(Math.trunc(parsed), DEFAULT_MAX_MIND_CARDS));
}

function formatCreatedAt(value: string | null | undefined): string {
  if (!value) {
    return "방금 전";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "저장됨";
  }
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function statusBadgeTone(statusValue: string): string {
  if (statusValue === "safe" || statusValue === "public") {
    return "safe";
  }
  if (statusValue === "exclude" || statusValue === "excluded" || statusValue === "hidden") {
    return "danger";
  }
  return "warning";
}

function cardStatusMessage(card: MindCard): string {
  if (card.safetyStatus === "safe" && card.publicStatus === "public") {
    return "공개 가능한 카드로 저장되었습니다.";
  }
  if (card.safetyStatus === "exclude" || card.publicStatus === "excluded") {
    return "공개 영역에는 표시되지 않습니다. 다만 참여 흐름은 계속 진행할 수 있습니다.";
  }
  return "개인정보나 민감 표현이 포함될 수 있어 관리자 검수 후 공개될 수 있습니다.";
}

function statusNoticeTone(card: MindCard): "info" | "safe" | "warning" {
  if (card.safetyStatus === "safe" && card.publicStatus === "public") {
    return "safe";
  }
  return "warning";
}

export function MindCardPage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const sessionId = eventSlug ? getStoredSessionId(eventSlug) : undefined;
  const [sessionState, setSessionState] = useState<SessionStatusResponse | undefined>();
  const [cards, setCards] = useState<MindCard[]>([]);
  const [maxCards, setMaxCards] = useState(DEFAULT_MAX_MIND_CARDS);
  const [loading, setLoading] = useState(true);
  const [guardError, setGuardError] = useState<string | undefined>();
  const [cardsError, setCardsError] = useState<string | undefined>();
  const [actionError, setActionError] = useState<string | undefined>();
  const [actionPendingId, setActionPendingId] = useState<string | undefined>();
  const [lastSavedCard, setLastSavedCard] = useState<MindCard | undefined>();
  const [editingCardId, setEditingCardId] = useState<string | undefined>();
  const [editContent, setEditContent] = useState("");
  const [content, setContent] = useState(() =>
    eventSlug && sessionId ? getMindCardDraft(eventSlug, sessionId) : ""
  );
  const mindCard = useMindCard(sessionId);

  const refreshCards = useCallback(async () => {
    if (!sessionId) {
      return;
    }
    setCardsError(undefined);
    try {
      const response = await listMyMindCards(sessionId);
      setCards(response.cards);
    } catch (error) {
      setCardsError(toUserMessage(error));
    }
  }, [sessionId]);

  useEffect(() => {
    if (!eventSlug || !sessionId) {
      navigate(`/e/${encodeURIComponent(eventSlug ?? "fire-expo-2026")}`, { replace: true });
      return;
    }
    let alive = true;
    setLoading(true);
    setGuardError(undefined);
    setCardsError(undefined);

    Promise.all([getSession(sessionId), getPublicEvent(eventSlug), listMyMindCards(sessionId)])
      .then(([nextSession, publicEvent, myCards]) => {
        if (!alive) {
          return;
        }
        setSessionState(nextSession);
        setMaxCards(maxMindCardsFromSetting(publicEvent.event.settings.maxMindCardsPerSession));
        setCards(myCards.cards);
        if (!statusAtLeast(nextSession.session.status, "summary_viewed")) {
          navigate(routeForSessionStatus(eventSlug, nextSession.session, nextSession.progress), { replace: true });
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

  function startEditing(card: MindCard) {
    setActionError(undefined);
    setEditingCardId(card.id);
    setEditContent(card.content);
  }

  function cancelEditing() {
    setEditingCardId(undefined);
    setEditContent("");
  }

  async function afterSuccessfulSave(result: CreateMindCardResponse) {
    if (!eventSlug || !sessionId) {
      return;
    }
    setLastSavedCard(result.card);
    clearMindCardDraft(eventSlug, sessionId);
    setContent("");
    setSessionState((current) =>
      current
        ? {
            ...current,
            session: { ...current.session, status: result.sessionStatus },
            progress: {
              ...current.progress,
              mindCardCount: Math.max(current.progress.mindCardCount, cards.length + 1)
            }
          }
        : current
    );
    await refreshCards();
  }

  async function submitEdit(cardId: string) {
    if (!sessionId || actionPendingId) {
      return;
    }
    setActionPendingId(cardId);
    setActionError(undefined);
    try {
      const result = await updateMindCard(sessionId, cardId, {
        promptType: STRESS_MEMORY_PROMPT_TYPE,
        content: editContent
      });
      setLastSavedCard(result.card);
      setEditingCardId(undefined);
      setEditContent("");
      setSessionState((current) =>
        current
          ? {
              ...current,
              session: { ...current.session, status: result.sessionStatus }
            }
          : current
      );
      await refreshCards();
    } catch (error) {
      setActionError(toUserMessage(error));
    } finally {
      setActionPendingId(undefined);
    }
  }

  async function removeCard(cardId: string) {
    if (!sessionId || actionPendingId) {
      return;
    }
    if (!window.confirm("이 마음카드를 삭제할까요?")) {
      return;
    }
    setActionPendingId(cardId);
    setActionError(undefined);
    try {
      const result = await deleteMindCard(sessionId, cardId);
      const remainingCards = cards.filter((card) => card.id !== result.deletedCardId);
      setLastSavedCard(undefined);
      if (editingCardId === cardId) {
        cancelEditing();
      }
      setCards(remainingCards);
      setSessionState((current) =>
        current
          ? {
              ...current,
              session: { ...current.session, status: result.sessionStatus },
              progress: {
                ...current.progress,
                mindCardCount: remainingCards.length
              }
            }
          : current
      );
      await refreshCards();
      setCards((currentCards) => currentCards.filter((card) => card.id !== result.deletedCardId));
      setSessionState((current) =>
        current
          ? {
              ...current,
              session: { ...current.session, status: result.sessionStatus },
              progress: {
                ...current.progress,
                mindCardCount: remainingCards.length
              }
            }
          : current
      );
    } catch (error) {
      setActionError(toUserMessage(error));
    } finally {
      setActionPendingId(undefined);
    }
  }

  async function submit() {
    if (!eventSlug || !sessionId || cards.length >= maxCards) {
      return;
    }
    const result = await mindCard.submit({ promptType: STRESS_MEMORY_PROMPT_TYPE, content });
    if (result) {
      await afterSuccessfulSave(result);
    }
  }

  async function retry() {
    if (!eventSlug || !sessionId) {
      return;
    }
    const result = await mindCard.retry();
    if (result) {
      await afterSuccessfulSave(result);
    }
  }

  function goToSelectPeerCard() {
    if (!eventSlug || cards.length < 1) {
      return;
    }
    navigate(`/e/${encodeURIComponent(eventSlug)}/cards/select`);
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

  const canAddMore = cards.length < maxCards;
  const canGoNext = cards.length >= 1;
  const actionPending = Boolean(actionPendingId);

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">마음카드</p>
        <h1>마음에 남은 스트레스 상황을 적어주세요.</h1>
        <p>
          마음 한 켠에 남아 있는 상황이나 장면, 그 때 느꼈던 감정을 짧게 적어주세요.
          작성된 마음카드는 다른 사람들에게 공개되어 서로의 경험을 공유하는 데 사용됩니다.
        </p>
      </div>

      <div className="mind-card-sticky-notice">
        <NoticeBox tone="warning" title="식별정보 입력 금지">
          <p>실명, 소속, 연락처, 구체적 장소, 날짜, 사건명과 같은 구체적인 정보는 적지 말아 주세요.</p>
        </NoticeBox>
      </div>

      <section className="panel mind-card-progress" aria-label="내 마음카드 작성 현황">
        <div>
          <p className="eyebrow">내가 작성한 카드</p>
          <strong>{cards.length} / {maxCards}</strong>
        </div>
        <p>
          개인 정보나 민감한 내용이 포함되지 않도록 주의해 주세요.
          최대 {maxCards}개까지 작성할 수 있습니다.
        </p>
      </section>

      {lastSavedCard ? (
        <NoticeBox tone={statusNoticeTone(lastSavedCard)} title="저장 결과">
          <p>{cardStatusMessage(lastSavedCard)}</p>
          {lastSavedCard.safetyStatus === "exclude" || lastSavedCard.publicStatus === "excluded" ? (
            <p>지금 안전이 걱정된다면 혼자 견디지 말고 현장 운영자나 가까운 사람에게 도움을 요청해 주세요.</p>
          ) : null}
        </NoticeBox>
      ) : null}

      <section className="mind-card-list" aria-label="내가 작성한 마음카드 목록">
        {cards.length === 0 ? (
          <div className="panel mind-card-empty">
            <p>아직 작성한 카드가 없습니다.</p>
            <p>마음카드를 1개 이상 작성하면 다음 단계로 이동할 수 있습니다.</p>
          </div>
        ) : (
          cards.map((card) => (
            <article className="mind-card-item" key={card.id}>
              {editingCardId === card.id ? (
                <>
                  <header className="mind-card-item__header">
                    <span>카드 수정</span>
                    <time dateTime={card.createdAt ?? undefined}>{formatCreatedAt(card.createdAt)}</time>
                  </header>
                  <MindCardForm
                    content={editContent}
                    onContentChange={setEditContent}
                    onSubmit={() => submitEdit(card.id)}
                    pending={actionPendingId === card.id}
                    pendingLabel="수정 중"
                    submitLabel="수정 저장"
                  />
                  <div className="mind-card-actions">
                    <Button
                      disabled={actionPending}
                      onClick={cancelEditing}
                      type="button"
                      variant="secondary"
                    >
                      취소
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <header className="mind-card-item__header">
                    <span>마음카드</span>
                    <time dateTime={card.createdAt ?? undefined}>{formatCreatedAt(card.createdAt)}</time>
                  </header>
                  <p className="mind-card-item__content">{card.content}</p>
                  <div className="status-badge-row" aria-label="카드 상태">
                    <span className={`status-badge status-badge--${statusBadgeTone(card.safetyStatus)}`}>
                      {SAFETY_LABELS[card.safetyStatus] ?? card.safetyStatus}
                    </span>
                    <span className={`status-badge status-badge--${statusBadgeTone(card.publicStatus)}`}>
                      {PUBLIC_LABELS[card.publicStatus] ?? card.publicStatus}
                    </span>
                  </div>
                  <p className="mind-card-item__status">{cardStatusMessage(card)}</p>
                  <div className="mind-card-actions">
                    <Button
                      disabled={actionPending}
                      onClick={() => startEditing(card)}
                      type="button"
                      variant="secondary"
                    >
                      수정
                    </Button>
                    <Button
                      disabled={actionPending}
                      onClick={() => removeCard(card.id)}
                      type="button"
                      variant="danger"
                    >
                      {actionPendingId === card.id ? "삭제 중" : "삭제"}
                    </Button>
                  </div>
                </>
              )}
            </article>
          ))
        )}
      </section>

      {cardsError ? <RetryNotice message={cardsError} onRetry={refreshCards} /> : null}
      {actionError ? <RetryNotice message={actionError} /> : null}

      {canAddMore && !editingCardId ? (
        <section className="panel">
          <MindCardForm
            content={content}
            onContentChange={updateContent}
            onSubmit={submit}
            pending={mindCard.pending}
          />
        </section>
      ) : !editingCardId ? (
        <NoticeBox tone="safe">
          <p>최대 {maxCards}개까지 작성했습니다. 다음 단계로 이동해 주세요.</p>
        </NoticeBox>
      ) : null}

      {editingCardId ? (
        <NoticeBox tone="info">
          <p>수정을 마치거나 취소하면 새 카드를 추가할 수 있습니다.</p>
        </NoticeBox>
      ) : null}

      {mindCard.error ? (
        <RetryNotice
          message={mindCard.error}
          onRetry={mindCard.canRetry ? retry : submit}
          pending={mindCard.pending}
        />
      ) : null}

      <div className="action-row action-row--single">
        <Button
          disabled={!canGoNext || mindCard.pending || actionPending || Boolean(editingCardId)}
          onClick={goToSelectPeerCard}
        >
          다음: 다른 사람의 마음카드 살펴보기
        </Button>
      </div>
      {!canGoNext ? (
        <p className="field-help">마음카드를 1개 이상 작성하면 다음 단계로 이동할 수 있습니다.</p>
      ) : null}
    </main>
  );
}
