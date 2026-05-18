import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import reborntalkScreensUrl from "../../assets/brand/reborntalk-app-screens.png";
import reborntalkLogoUrl from "../../assets/brand/reborntalk-logo.png";
import { Button } from "../../components/common/Button";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { useEventSession } from "../../hooks/useEventSession";
import { useSurveyContent } from "../../hooks/useSurveyContent";
import { routeForSessionStatus } from "../../lib/routeGuards";

export function LandingPage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const { sessionState, loading, error, retry } = useEventSession(eventSlug);
  const { surveyConfig } = useSurveyContent(eventSlug);
  const intro = surveyConfig.intro;
  const lead = intro.paragraphs[0];
  const bodyParagraphs = intro.paragraphs.slice(1);

  useEffect(() => {
    if (!eventSlug || !sessionState) {
      return;
    }
    if (sessionState.session.status === "created") {
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

  const consentPath = `/e/${encodeURIComponent(eventSlug ?? "fire-expo-2026")}/consent`;

  return (
    <main className="screen survey-intro">
      <section className="survey-intro__hero">
        <p className="eyebrow">섹션 1 / 8</p>
        {intro.showLogo ? <img className="reborntalk-logo" src={reborntalkLogoUrl} alt="리본톡" /> : null}
        <h1>{intro.title}</h1>
        {intro.subtitle ? <p className="survey-intro__subtitle">{intro.subtitle}</p> : null}
        {lead ? <p className="survey-intro__lead">{lead}</p> : null}
        {intro.showAppScreens ? (
          <img
            className="reborntalk-screens"
            src={reborntalkScreensUrl}
            alt="리본톡 앱 화면 예시"
          />
        ) : null}
      </section>

      {bodyParagraphs.length ? (
        <section className="panel survey-intro__body">
          {bodyParagraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </section>
      ) : null}

      <section className="notice notice--info survey-intro__notice">
        <h2>참여 전 안내</h2>
        <p>본 설문은 진단이나 치료가 아닌 체험형 마음 점검입니다.</p>
        <p>예상 소요시간: 약 15~20분</p>
      </section>

      <Button fullWidth onClick={() => navigate(consentPath)}>
        연구 참여 설명문 확인하기
      </Button>
    </main>
  );
}
