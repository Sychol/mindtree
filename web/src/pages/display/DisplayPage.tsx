import { useParams } from "react-router-dom";

import { ConnectionStatusBadge } from "../../components/display/ConnectionStatusBadge";
import { DisplayNotice } from "../../components/display/DisplayNotice";
import { ParticipantCount } from "../../components/display/ParticipantCount";
import { TopKeywordsPanel } from "../../components/display/TopKeywordsPanel";
import { TreeWordCloud } from "../../components/display/TreeWordCloud";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { useDisplaySnapshot } from "../../hooks/useDisplaySnapshot";
import { useDisplaySse } from "../../hooks/useDisplaySse";

export function DisplayPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const initial = useDisplaySnapshot(eventSlug);
  const stream = useDisplaySse(eventSlug, initial.snapshot);
  const snapshot = stream.snapshot ?? initial.snapshot;

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
    <main className="display-screen">
      <header className="display-header">
        <div>
          <p className="display-eyebrow">마음나무</p>
          <h1>오늘 남겨진 마음의 잎들이 자라고 있습니다</h1>
        </div>
        <ConnectionStatusBadge status={stream.connectionStatus} />
      </header>

      <section className="display-layout" aria-label="TV 마음나무">
        <div className="display-tree-area">
          <TreeWordCloud keywords={snapshot.cloudKeywords} />
        </div>
        <aside className="display-side">
          <ParticipantCount
            participantCount={snapshot.participantCount}
            completedCount={snapshot.completedCount}
          />
          <TopKeywordsPanel
            topMindKeywords={snapshot.topMindKeywords}
            topSupportKeywords={snapshot.topSupportKeywords}
          />
        </aside>
      </section>

      <footer className="display-footer">
        <DisplayNotice />
        <span>{stream.lastUpdatedAt ? `마지막 갱신 ${new Date(stream.lastUpdatedAt).toLocaleTimeString("ko-KR")}` : ""}</span>
      </footer>
    </main>
  );
}
