import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { listAdminKeywordJobs, retryAdminKeywordJob } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import { KeywordJobStatusBadge } from "../../components/admin/KeywordJobStatusBadge";
import type { AdminKeywordJobItem } from "../../types/admin";
import {
  adminErrorMessage,
  adminJobErrorLabel,
  adminProviderLabel,
  adminSourceTypeLabel,
  adminStatusLabel,
} from "../../utils/adminLabels";

const JOB_STATUSES = ["failed", "retry_wait", "pending", "processing", "succeeded", "all"];

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return adminErrorMessage(error, "키워드 작업 요청에 실패했습니다.");
  }
  return "키워드 작업 요청에 실패했습니다.";
}

export function AdminKeywordJobsPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const [status, setStatus] = useState("all");
  const [items, setItems] = useState<AdminKeywordJobItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const response = await listAdminKeywordJobs(eventSlug, { status });
      setItems(response.items);
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };

  useEffect(() => {
    void load();
  }, [eventSlug, status]);

  const retry = async (job: AdminKeywordJobItem) => {
    await retryAdminKeywordJob(job.id, "운영자 재시도");
    await load();
  };

  return (
    <section className="admin-section">
      <div className="admin-section__header">
        <div>
          <p className="admin-eyebrow">{items.length}개 작업</p>
          <h2>키워드 작업 상태</h2>
        </div>
        <select className="admin-select" onChange={(event) => setStatus(event.target.value)} value={status}>
          {JOB_STATUSES.map((value) => (
            <option key={value} value={value}>
              {adminStatusLabel(value)}
            </option>
          ))}
        </select>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>원본</th>
              <th>상태</th>
              <th>시도</th>
              <th>처리 방식</th>
              <th>오류</th>
              <th>조치</th>
            </tr>
          </thead>
          <tbody>
            {items.map((job) => (
              <tr key={job.id}>
                <td>
                  {adminSourceTypeLabel(job.sourceType)}
                  <span className="admin-muted"> {job.sourceId.slice(0, 8)}</span>
                </td>
                <td>
                  <KeywordJobStatusBadge status={job.status} />
                </td>
                <td>
                  {job.attempts}/{job.maxAttempts}
                </td>
                <td>
                  {adminProviderLabel(job.provider)}
                  {job.fallbackUsed ? <span className="admin-muted"> 대체 추출</span> : null}
                </td>
                <td>{adminJobErrorLabel(job.errorMessage)}</td>
                <td>
                  <button
                    className="admin-button admin-button--secondary"
                    disabled={!["failed", "retry_wait"].includes(job.status)}
                    onClick={() => void retry(job)}
                    type="button"
                  >
                    재시도
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
