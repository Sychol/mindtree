import type { CSSProperties } from "react";
import { useParams } from "react-router-dom";

import acceptIconUrl from "../../assets/display/accept.svg";
import backgroundHillsUrl from "../../assets/display/background-hills.svg";
import barGraphIconUrl from "../../assets/display/bar-graph.svg";
import heartIconUrl from "../../assets/display/heart.svg";
import usersIconUrl from "../../assets/display/users.svg";
import { ConnectionStatusBadge } from "../../components/display/ConnectionStatusBadge";
import { DisplayNotice } from "../../components/display/DisplayNotice";
import { DisplayHeroTitle } from "../../components/display/DisplayHeroTitle";
import { DisplayMetricCard } from "../../components/display/DisplayMetricCard";
import { LiveBadge } from "../../components/display/LiveBadge";
import { TreeWordCloud } from "../../components/display/TreeWordCloud";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { useDisplaySnapshot } from "../../hooks/useDisplaySnapshot";
import { useDisplaySse } from "../../hooks/useDisplaySse";
import type { DisplayKeyword } from "../../types/display";

type RankingListProps = {
  keywords: DisplayKeyword[];
};

function RankingList({ keywords }: RankingListProps) {
  if (!keywords.length) {
    return <p className="display-ranking-empty">아직 키워드가 모이는 중입니다.</p>;
  }

  return (
    <ol className="display-top-list">
      {keywords.slice(0, 5).map((keyword, index) => (
        <li key={`${keyword.text}-${index}`}>
          <span>{index + 1}.</span>
          <strong>{keyword.text}</strong>
        </li>
      ))}
    </ol>
  );
}

export function DisplayPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const initial = useDisplaySnapshot(eventSlug);
  const stream = useDisplaySse(eventSlug, initial.snapshot);
  const snapshot = stream.snapshot ?? initial.snapshot;
  const displayStyle = {
    "--display-hills-url": `url(${backgroundHillsUrl})`,
  } as CSSProperties;

  if (!snapshot && initial.loading) {
    return <LoadingState title="마음나무를 불러오는 중입니다" message="현장의 마음 잎을 모으고 있습니다." />;
  }

  if (!snapshot && initial.error) {
    return (
      <ErrorState
        title="마음나무를 불러오지 못했습니다"
        message={initial.error}
        onRetry={initial.retry}
      />
    );
  }

  if (!snapshot) {
    return null;
  }

  return (
    <main className="display-screen display-screen--tree" style={displayStyle}>
      <LiveBadge status={stream.connectionStatus} />

      <header className="display-hero">
        <DisplayHeroTitle />
        <p className="display-hero__subtitle">소방안전박람회 실시간 응원 키워드</p>
        <p className="display-hero__notice">참여자들의 문장에서 추출한 익명 키워드만 표시됩니다</p>
      </header>

      <section className="display-stage" aria-label="TV 마음나무">
        <div className="display-tree-stage">
          <TreeWordCloud keywords={snapshot.cloudKeywords} />
        </div>

        <aside className="display-dashboard" aria-label="마음나무 지표">
          <DisplayMetricCard
            iconSrc={usersIconUrl}
            title="참여자 수"
            value={snapshot.participantCount}
            unit="명"
          />
          <DisplayMetricCard
            iconSrc={acceptIconUrl}
            title="완료자 수"
            value={snapshot.completedCount}
            unit="명"
          />
          <DisplayMetricCard iconSrc={barGraphIconUrl} title="마음신호 TOP5">
            <RankingList keywords={snapshot.topMindKeywords} />
          </DisplayMetricCard>
          <DisplayMetricCard iconSrc={heartIconUrl} title="응원·회복 TOP5">
            <RankingList keywords={snapshot.topSupportKeywords} />
          </DisplayMetricCard>
        </aside>
      </section>

      <footer className="display-footer">
        <DisplayNotice />
        <p className="display-footer__hint">큰 단어일수록 더 자주 등장한 마음입니다</p>
        <div className="display-footer__status">
          <ConnectionStatusBadge status={stream.connectionStatus} />
          <span>{stream.lastUpdatedAt ? `마지막 갱신 ${new Date(stream.lastUpdatedAt).toLocaleTimeString("ko-KR")}` : ""}</span>
        </div>
      </footer>
    </main>
  );
}
