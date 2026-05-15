import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getAdminDashboard } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import type { AdminDashboardResponse } from "../../types/admin";
import { adminErrorMessage, adminStatusLabel } from "../../utils/adminLabels";

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return adminErrorMessage(error, "대시보드를 불러오지 못했습니다.");
  }
  return "대시보드를 불러오지 못했습니다.";
}

export function AdminDashboardPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const [dashboard, setDashboard] = useState<AdminDashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    void getAdminDashboard(eventSlug)
      .then((response) => {
        if (!cancelled) {
          setDashboard(response);
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(errorText(requestError));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [eventSlug]);

  const metrics = dashboard?.metrics;

  return (
    <section className="admin-section">
      <div className="admin-section__header">
        <div>
          <p className="admin-eyebrow">대시보드</p>
          <h2>운영 요약</h2>
        </div>
        <span className="admin-badge admin-badge--safe">{adminStatusLabel(dashboard?.event.status ?? "loading")}</span>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      <div className="admin-metric-grid">
        <Metric label="전체 세션" value={metrics?.sessionCount} />
        <Metric label="완료 세션" value={metrics?.completedCount} />
        <Metric label="마음카드" value={metrics?.cardCount} />
        <Metric label="응원 문장" value={metrics?.replyCount} />
        <Metric label="검수 대기" value={metrics?.reviewCount} />
        <Metric label="대기 중 작업" value={metrics?.keywordPendingCount} />
        <Metric label="실패한 작업" value={metrics?.keywordFailedCount} />
        <Metric label="발급 코드" value={metrics?.completionIssuedCount} />
        <Metric label="지급 완료" value={metrics?.redeemedCount} />
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value?: number }) {
  return (
    <div className="admin-metric">
      <span>{label}</span>
      <strong>{value ?? "-"}</strong>
    </div>
  );
}
