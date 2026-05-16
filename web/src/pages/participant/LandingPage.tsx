import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import reborntalkScreensUrl from "../../assets/brand/reborntalk-app-screens.png";
import reborntalkLogoUrl from "../../assets/brand/reborntalk-logo.png";
import { Button } from "../../components/common/Button";
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
        <img className="reborntalk-logo" src={reborntalkLogoUrl} alt="리본톡" />
        <h1>리본톡 소개 및 설문</h1>
        <p className="survey-intro__lead">
          리본톡은 소방공무원 등 재난 현장에서 강한 외상 사건을 반복적으로 경험하는 분들의
          트라우마 예방과 회복을 돕기 위한 공감 기반 AI 심리상담 앱입니다.
        </p>
        <img
          className="reborntalk-screens"
          src={reborntalkScreensUrl}
          alt="리본톡 앱 화면 예시"
        />
      </section>

      <section className="panel survey-intro__body">
        <p>
          리본톡은 실제 소방공무원·경찰·군인 등의 외상 경험, 당시의 감정, 그리고 회복
          과정을 인터뷰 형태로 모아 익명화한 뒤, AI가 이를 학습하여 상담에 활용합니다.
        </p>
        <p>
          사용자가 자신의 힘들었던 경험을 이야기하면, 나와 비슷한 경험을 한 동료의 이야기와
          회복 과정을 공감적으로 연결해 주는 방식입니다.
        </p>
        <p>
          리본톡은 진단이나 치료를 대신하는 의료서비스가 아니라, 언제든지 접근 가능한 심리적
          지지 도구로서, 추후 필요 시 전문 상담·치료로 연결되는 다리 역할을 목표로 하고
          있습니다.
        </p>
      </section>

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
