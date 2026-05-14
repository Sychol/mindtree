import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getSession } from "../../api/sessions";
import { Button } from "../../components/common/Button";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { NoticeBox } from "../../components/common/NoticeBox";
import { ProgressHeader } from "../../components/participant/ProgressHeader";
import { QuestionRenderer } from "../../components/participant/QuestionRenderer";
import { QuestionSectionTabs, sectionLabel } from "../../components/participant/QuestionSectionTabs";
import { usePreloadedQuestions } from "../../hooks/usePreloadedQuestions";
import { useQuestionProgress } from "../../hooks/useQuestionProgress";
import { toUserMessage } from "../../lib/errors";
import { statusAtLeast } from "../../lib/routeGuards";
import { getStoredSessionId } from "../../lib/storage";
import type { SessionStatusResponse } from "../../types/session";

export function QuestionsPage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const sessionId = eventSlug ? getStoredSessionId(eventSlug) : undefined;
  const [sessionState, setSessionState] = useState<SessionStatusResponse | undefined>();
  const [sessionError, setSessionError] = useState<string | undefined>();
  const [sessionLoading, setSessionLoading] = useState(true);

  const { questions, loading, error, retry } = usePreloadedQuestions(eventSlug, sessionId);
  const progress = useQuestionProgress(eventSlug, sessionId, questions);
  const currentQuestion = progress.currentQuestion;

  useEffect(() => {
    if (!eventSlug || !sessionId) {
      navigate(`/e/${encodeURIComponent(eventSlug ?? "fire-expo-2026")}`, { replace: true });
      return;
    }

    let alive = true;
    setSessionLoading(true);
    getSession(sessionId)
      .then((nextSession) => {
        if (!alive) {
          return;
        }
        setSessionState(nextSession);
        if (nextSession.session.status === "created") {
          navigate(`/e/${encodeURIComponent(eventSlug)}/consent`, { replace: true });
        } else if (statusAtLeast(nextSession.session.status, "questions_completed")) {
          navigate(`/e/${encodeURIComponent(eventSlug)}/summary`, { replace: true });
        }
      })
      .catch((loadError) => {
        if (alive) {
          setSessionError(toUserMessage(loadError));
        }
      })
      .finally(() => {
        if (alive) {
          setSessionLoading(false);
        }
      });

    return () => {
      alive = false;
    };
  }, [eventSlug, navigate, sessionId]);

  if (sessionLoading || loading) {
    return (
      <main className="screen">
        <LoadingState title="문항을 준비하고 있습니다" message="전체 문항을 한 번에 불러오고 있습니다." />
      </main>
    );
  }

  if (sessionError || error || !eventSlug || !sessionId || !sessionState) {
    return (
      <main className="screen">
        <ErrorState message={sessionError ?? error ?? "문항을 확인할 수 없습니다."} onRetry={retry} />
      </main>
    );
  }

  if (!currentQuestion) {
    return (
      <main className="screen">
        <ErrorState message="표시할 문항이 없습니다." onRetry={retry} />
      </main>
    );
  }

  const currentValue = progress.getAnswerValue(currentQuestion.id);

  return (
    <main className="screen screen--questions">
      <ProgressHeader
        current={progress.currentIndex + 1}
        total={progress.totalCount}
        answered={progress.answeredCount}
        sectionName={sectionLabel(currentQuestion.scaleCode)}
      />
      <QuestionSectionTabs
        questions={progress.visibleQuestions}
        currentQuestionNo={currentQuestion.questionNo}
        onSelectQuestionNo={progress.goToQuestionNo}
      />
      <section className="question-surface">
        <p className="eyebrow">문항 {currentQuestion.questionNo}</p>
        <h1>{currentQuestion.title}</h1>
        {currentQuestion.description ? <p>{currentQuestion.description}</p> : null}
        <QuestionRenderer
          question={currentQuestion}
          value={currentValue}
          onChange={(value) => progress.updateAnswer(currentQuestion, value)}
        />
      </section>
      {!progress.currentAnswered ? (
        <NoticeBox tone="warning">
          <p>이 문항에 응답하면 다음으로 이동할 수 있습니다.</p>
        </NoticeBox>
      ) : null}
      <div className="action-row">
        <Button variant="secondary" disabled={progress.isFirst} onClick={progress.goPrevious}>
          이전
        </Button>
        {progress.isLast ? (
          <Button
            disabled={progress.missingRequiredQuestionNos.length > 0}
            onClick={() => navigate(`/e/${encodeURIComponent(eventSlug)}/questions/review`)}
          >
            제출 전 확인
          </Button>
        ) : (
          <Button disabled={!progress.currentAnswered} onClick={progress.goNext}>
            다음
          </Button>
        )}
      </div>
    </main>
  );
}
