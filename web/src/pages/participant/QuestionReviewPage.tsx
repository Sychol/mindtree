import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getSession } from "../../api/sessions";
import { Button } from "../../components/common/Button";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { NoticeBox } from "../../components/common/NoticeBox";
import { SubmitRetryPanel } from "../../components/participant/SubmitRetryPanel";
import { usePreloadedQuestions } from "../../hooks/usePreloadedQuestions";
import { useQuestionProgress } from "../../hooks/useQuestionProgress";
import { useSubmitWithRetry } from "../../hooks/useSubmitWithRetry";
import { toUserMessage } from "../../lib/errors";
import { statusAtLeast } from "../../lib/routeGuards";
import { clearQuestionTemporaryStorage, getStoredSessionId } from "../../lib/storage";
import type { BulkAnswersResponse } from "../../types/answer";

export function QuestionReviewPage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const sessionId = eventSlug ? getStoredSessionId(eventSlug) : undefined;
  const { questions, loading, error, retry } = usePreloadedQuestions(eventSlug, sessionId);
  const progress = useQuestionProgress(eventSlug, sessionId, questions);
  const submitState = useSubmitWithRetry(sessionId);
  const [serverMissing, setServerMissing] = useState<number[]>([]);
  const [checkingSession, setCheckingSession] = useState(true);
  const [guardError, setGuardError] = useState<string | undefined>();

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
        if (nextSession.session.status === "created") {
          navigate(`/e/${encodeURIComponent(eventSlug)}/consent`, { replace: true });
        } else if (statusAtLeast(nextSession.session.status, "questions_completed")) {
          navigate(`/e/${encodeURIComponent(eventSlug)}/summary`, { replace: true });
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

  function handleResponse(response: BulkAnswersResponse | undefined) {
    if (!response) {
      return;
    }
    const missing = response.missingQuestionNos ?? [];
    setServerMissing(missing);
    if (missing.length === 0 && eventSlug && sessionId) {
      clearQuestionTemporaryStorage(eventSlug, sessionId);
      navigate(`/e/${encodeURIComponent(eventSlug)}/summary`, { replace: true });
    }
  }

  async function submit() {
    handleResponse(await submitState.submit(progress.toBulkRequest()));
  }

  async function retrySubmit() {
    handleResponse(await submitState.retry());
  }

  if (loading || checkingSession) {
    return (
      <main className="screen">
        <LoadingState title="응답을 확인하고 있습니다" />
      </main>
    );
  }

  if (guardError || error || !eventSlug || !sessionId) {
    return (
      <main className="screen">
        <ErrorState message={guardError ?? error ?? "세션을 확인할 수 없습니다."} onRetry={retry} />
      </main>
    );
  }

  const localMissing = progress.missingRequiredQuestionNos;

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">제출 전 확인</p>
        <h1>응답을 저장할까요?</h1>
        <p>{progress.answeredCount}개 문항에 응답했습니다.</p>
      </div>
      {localMissing.length ? (
        <NoticeBox tone="warning" title="아직 응답하지 않은 문항">
          <p>{localMissing.join(", ")}번 문항을 확인해 주세요.</p>
        </NoticeBox>
      ) : (
        <NoticeBox tone="safe">
          <p>필수 문항 응답이 모두 입력되었습니다. 제출 실패 시 입력값은 유지됩니다.</p>
        </NoticeBox>
      )}
      {serverMissing.length ? (
        <NoticeBox tone="warning" title="서버에서 확인한 누락 문항">
          <p>{serverMissing.join(", ")}번 문항을 다시 확인해 주세요.</p>
        </NoticeBox>
      ) : null}
      <SubmitRetryPanel
        error={submitState.error}
        pending={submitState.pending}
        canRetry={submitState.canRetry}
        onRetry={retrySubmit}
      />
      <div className="action-row">
        <Button variant="secondary" onClick={() => navigate(`/e/${encodeURIComponent(eventSlug)}/questions`)}>
          돌아가기
        </Button>
        <Button disabled={Boolean(localMissing.length) || submitState.pending} onClick={submit}>
          {submitState.pending ? "제출 중" : "최종 제출"}
        </Button>
      </div>
    </main>
  );
}
