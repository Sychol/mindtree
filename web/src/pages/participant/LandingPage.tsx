import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { useEventSession } from "../../hooks/useEventSession";
import { routeForSessionStatus } from "../../lib/routeGuards";

export function LandingPage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const { sessionState, loading, error, retry } = useEventSession(eventSlug);

  useEffect(() => {
    if (!eventSlug || !sessionState) {
      return;
    }
    navigate(routeForSessionStatus(eventSlug, sessionState.session, sessionState.progress), {
      replace: true
    });
  }, [eventSlug, navigate, sessionState]);

  if (loading) {
    return (
      <main className="screen">
        <LoadingState title="마음나무에 연결 중입니다" message="이벤트와 세션을 확인하고 있습니다." />
      </main>
    );
  }

  if (error) {
    return (
      <main className="screen">
        <ErrorState message={error} onRetry={retry} />
      </main>
    );
  }

  return (
    <main className="screen">
      <LoadingState title="다음 화면으로 이동합니다" />
    </main>
  );
}
