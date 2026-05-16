import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getSession } from "../../api/sessions";
import { Button } from "../../components/common/Button";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { NoticeBox } from "../../components/common/NoticeBox";
import { ProgressHeader } from "../../components/participant/ProgressHeader";
import { QuestionRenderer } from "../../components/participant/QuestionRenderer";
import { usePreloadedQuestions } from "../../hooks/usePreloadedQuestions";
import { useQuestionProgress } from "../../hooks/useQuestionProgress";
import { toUserMessage } from "../../lib/errors";
import { statusAtLeast } from "../../lib/routeGuards";
import { getQuestionsForSurveySection, TOTAL_SURVEY_SECTIONS } from "../../lib/surveySections";
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
  const [attemptedAdvance, setAttemptedAdvance] = useState(false);

  useEffect(() => {
    setAttemptedAdvance(false);
  }, [progress.currentSectionId]);

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

  if (!progress.currentSection || !progress.currentSectionQuestions.length) {
    return (
      <main className="screen">
        <ErrorState message="표시할 문항이 없습니다." onRetry={retry} />
      </main>
    );
  }

  const hiddenQuestionNos = getQuestionsForSurveySection(questions, progress.currentSection)
    .filter(
      (question) =>
        !progress.currentSectionQuestions.some((visibleQuestion) => visibleQuestion.id === question.id)
    )
    .map((question) => question.questionNo);

  const missingQuestionNos = progress.missingRequiredQuestionNosForSection;

  function validateSection(): boolean {
    setAttemptedAdvance(true);
    return missingQuestionNos.length === 0;
  }

  function handleNextSection() {
    if (!validateSection()) {
      return;
    }
    progress.goNextSection();
  }

  function handleReview() {
    if (!validateSection() || !eventSlug) {
      return;
    }
    navigate(`/e/${encodeURIComponent(eventSlug)}/questions/review`);
  }

  return (
    <main className="screen screen--questions">
      <ProgressHeader
        sectionNo={progress.currentSection.sectionNo}
        totalSections={TOTAL_SURVEY_SECTIONS}
        title={progress.currentSection.title}
        description={progress.currentSection.description}
        sectionAnswered={progress.sectionAnsweredCount}
        sectionTotal={progress.sectionTotalCount}
        answered={progress.answeredCount}
        total={progress.totalCount}
      />
      <section className="question-surface survey-section">
        <div className="survey-section__header survey-section-header">
          <p className="eyebrow">문항 {progress.currentSection.questionNoRange?.join("~")}</p>
          <h1>{progress.currentSection.title}</h1>
          {progress.currentSection.description ? <p>{progress.currentSection.description}</p> : null}
        </div>
        {hiddenQuestionNos.length ? (
          <NoticeBox tone="info">
            <p>응답에 따라 {hiddenQuestionNos.join(", ")}번 문항은 건너뜁니다.</p>
          </NoticeBox>
        ) : null}
        <div className="survey-question-list">
          {progress.currentSectionQuestions.map((question) => {
            const value = progress.getAnswerValue(question.id);
            return (
              <section
                key={question.id}
                className="survey-question-card"
                aria-labelledby={`question-${question.id}-title`}
              >
                <div className="survey-question-card__header">
                  <p className="eyebrow">문항 {question.questionNo}</p>
                  <h2 id={`question-${question.id}-title`}>{question.title}</h2>
                  {question.description ? <p>{question.description}</p> : null}
                </div>
                <QuestionRenderer
                  question={question}
                  value={value}
                  onChange={(nextValue) => progress.updateAnswer(question, nextValue)}
                />
              </section>
            );
          })}
        </div>
      </section>
      {attemptedAdvance && missingQuestionNos.length ? (
        <NoticeBox tone="warning" title="아직 응답하지 않은 문항">
          <p>{missingQuestionNos.join(", ")}번 문항을 확인해 주세요.</p>
        </NoticeBox>
      ) : null}
      <div className="action-row survey-section-footer">
        <Button variant="secondary" disabled={progress.isFirstQuestionSection} onClick={progress.goPreviousSection}>
          이전
        </Button>
        {progress.isLastQuestionSection ? (
          <Button onClick={handleReview}>
            제출 전 확인
          </Button>
        ) : (
          <Button onClick={handleNextSection}>
            다음
          </Button>
        )}
      </div>
    </main>
  );
}
