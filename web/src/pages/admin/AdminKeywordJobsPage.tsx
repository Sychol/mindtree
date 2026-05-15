import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { listAdminKeywordJobs, retryAdminKeywordJob } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import { KeywordJobStatusBadge } from "../../components/admin/KeywordJobStatusBadge";
import type { AdminKeywordJobItem } from "../../types/admin";

const JOB_STATUSES = ["failed", "retry_wait", "pending", "processing", "succeeded", "all"];

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  return "Request failed.";
}

export function AdminKeywordJobsPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const [status, setStatus] = useState("failed");
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
    await retryAdminKeywordJob(job.id, "operator retry");
    await load();
  };

  return (
    <section className="admin-section">
      <div className="admin-section__header">
        <div>
          <p className="admin-eyebrow">{items.length} jobs</p>
          <h2>Keyword jobs</h2>
        </div>
        <select className="admin-select" onChange={(event) => setStatus(event.target.value)} value={status}>
          {JOB_STATUSES.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Status</th>
              <th>Attempts</th>
              <th>Provider</th>
              <th>Error</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((job) => (
              <tr key={job.id}>
                <td>
                  {job.sourceType}
                  <span className="admin-muted"> {job.sourceId.slice(0, 8)}</span>
                </td>
                <td>
                  <KeywordJobStatusBadge status={job.status} />
                </td>
                <td>
                  {job.attempts}/{job.maxAttempts}
                </td>
                <td>
                  {job.provider ?? "-"}
                  {job.fallbackUsed ? <span className="admin-muted"> fallback</span> : null}
                </td>
                <td>{job.errorMessage ?? "-"}</td>
                <td>
                  <button
                    className="admin-button admin-button--secondary"
                    disabled={!["failed", "retry_wait"].includes(job.status)}
                    onClick={() => void retry(job)}
                    type="button"
                  >
                    Retry
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
