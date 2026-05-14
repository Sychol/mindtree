import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getSession } from "../../api/sessions";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { NoticeBox } from "../../components/common/NoticeBox";
import { routeForSessionStatus, statusAtLeast } from "../../lib/routeGuards";
import { getStoredSessionId } from "../../lib/storage";
import type { SessionStatusResponse } from "../../types/session";

type PlaceholderStep =
  | "summary"
  | "cards-new"
  | "cards-select"
  | "replies-new"
  | "complete"
  | "help";

type ParticipantPlaceholderPageProps = {
  step: PlaceholderStep;
};

const STEP_COPY: Record<PlaceholderStep, { title: string; body: string }> = {
  summary: {
    title: "문항 응답이 저장되었습니다.",
    body: "다음 단계에서는 마음신호 요약을 확인하게 됩니다."
  },
  "cards-new": {
    title: "마음카드 단계",
    body: "이후 단계에서 내 마음을 짧은 카드로 정리하게 됩니다."
  },
  "cards-select": {
    title: "타인 카드 선택 단계",
    body: "다른 참가자의 익명 마음카드를 살펴보고 하나를 고르게 됩니다."
  },
  "replies-new": {
    title: "응원 문장 단계",
    body: "고른 카드에 공감이나 응원의 문장을 남기게 됩니다."
  },
  complete: {
    title: "완료 단계",
    body: "참여 완료 확인은 다음 단계에서 안내됩니다."
  },
  help: {
    title: "도움 안내",
    body: "필요한 경우 도움 받을 수 있는 안내를 이 화면에서 확인하게 됩니다."
  }
};

function canAccessStep(step: PlaceholderStep, sessionState: SessionStatusResponse): boolean {
  const status = sessionState.session.status;
  const progress = sessionState.progress;

  if (step === "summary") {
    return statusAtLeast(status, "questions_completed");
  }
  if (step === "cards-new") {
    return statusAtLeast(status, "summary_viewed");
  }
  if (step === "cards-select") {
    return statusAtLeast(status, "card_created");
  }
  if (step === "replies-new") {
    return statusAtLeast(status, "card_created") && progress.selectedCard;
  }
  if (step === "complete") {
    return statusAtLeast(status, "reply_created") || progress.completionCodeIssued;
  }
  return true;
}

export function ParticipantPlaceholderPage({ step }: ParticipantPlaceholderPageProps) {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const sessionId = eventSlug ? getStoredSessionId(eventSlug) : undefined;
  const [sessionState, setSessionState] = useState<SessionStatusResponse | undefined>();
  const [error, setError] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!eventSlug || !sessionId) {
      navigate(`/e/${encodeURIComponent(eventSlug ?? "fire-expo-2026")}`, { replace: true });
      return;
    }
    let alive = true;
    getSession(sessionId)
      .then((next) => {
        if (!alive) {
          return;
        }
        setSessionState(next);
        if (!canAccessStep(step, next)) {
          navigate(routeForSessionStatus(eventSlug, next.session, next.progress), { replace: true });
        }
      })
      .catch(() => {
        if (alive) {
          setError("세션 상태를 확인할 수 없습니다.");
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
  }, [eventSlug, navigate, sessionId, step]);

  if (loading) {
    return (
      <main className="screen">
        <LoadingState title="상태를 확인하고 있습니다" />
      </main>
    );
  }

  if (error || !eventSlug || !sessionState) {
    return (
      <main className="screen">
        <ErrorState message={error ?? "세션을 확인할 수 없습니다."} />
      </main>
    );
  }

  const copy = STEP_COPY[step];

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">다음 단계</p>
        <h1>{copy.title}</h1>
      </div>
      <NoticeBox tone="info">
        <p>{copy.body}</p>
      </NoticeBox>
      <Link className="button button--secondary button--full" to={`/e/${encodeURIComponent(eventSlug)}`}>
        현재 상태 다시 확인
      </Link>
    </main>
  );
}
