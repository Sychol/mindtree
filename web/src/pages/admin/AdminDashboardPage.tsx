import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getAdminDashboard } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import type { AdminDashboardResponse } from "../../types/admin";

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  return "Failed to load dashboard.";
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
          <p className="admin-eyebrow">Dashboard</p>
          <h2>Operations summary</h2>
        </div>
        <span className="admin-badge admin-badge--safe">{dashboard?.event.status ?? "loading"}</span>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      <div className="admin-metric-grid">
        <Metric label="Sessions" value={metrics?.sessionCount} />
        <Metric label="Completed" value={metrics?.completedCount} />
        <Metric label="Cards" value={metrics?.cardCount} />
        <Metric label="Replies" value={metrics?.replyCount} />
        <Metric label="Waiting review" value={metrics?.reviewCount} />
        <Metric label="Jobs pending" value={metrics?.keywordPendingCount} />
        <Metric label="Jobs failed" value={metrics?.keywordFailedCount} />
        <Metric label="Codes issued" value={metrics?.completionIssuedCount} />
        <Metric label="Rewards redeemed" value={metrics?.redeemedCount} />
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
