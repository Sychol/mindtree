import { useState } from "react";

import { exportAdminResponsesCsv } from "../../api/admin";
import { adminErrorMessage } from "../../utils/adminLabels";
import type { AdminResponsesExportRequest } from "../../types/admin";

type ResponseExportPanelProps = {
  eventSlug: string;
  status: string;
  completedOnly: boolean;
  createdFrom: string;
  createdTo: string;
};

function fallbackFilename(eventSlug: string): string {
  const timestamp = new Date().toISOString().replace(/\D/g, "").slice(0, 14);
  return `maeumnamu_${eventSlug}_responses_${timestamp}.csv`;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function ResponseExportPanel({
  eventSlug,
  status,
  completedOnly,
  createdFrom,
  createdTo,
}: ResponseExportPanelProps) {
  const [format, setFormat] = useState<"wide" | "long">("wide");
  const [includeScores, setIncludeScores] = useState(true);
  const [includeRiskFlags, setIncludeRiskFlags] = useState(false);
  const [includeCompletionStatus, setIncludeCompletionStatus] = useState(true);
  const [reason, setReason] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    const trimmedReason = reason.trim();
    if (!trimmedReason) {
      setError("CSV 다운로드 사유를 입력하세요.");
      setMessage(null);
      return;
    }

    const request: AdminResponsesExportRequest = {
      format,
      includeScores,
      includeRiskFlags,
      includeCompletionStatus,
      status,
      completedOnly,
      createdFrom: createdFrom || null,
      createdTo: createdTo || null,
      reason: trimmedReason,
    };

    setDownloading(true);
    setError(null);
    setMessage(null);
    try {
      const blob = await exportAdminResponsesCsv(eventSlug, request);
      const filename = blob instanceof File && blob.name ? blob.name : fallbackFilename(eventSlug);
      downloadBlob(blob, filename);
      setMessage("CSV 다운로드를 시작했습니다.");
    } catch (requestError) {
      setError(adminErrorMessage(requestError, "CSV 다운로드에 실패했습니다."));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <section className="admin-export-panel" aria-label="CSV export">
      <div>
        <p className="admin-eyebrow">CSV export</p>
        <h3>응답 데이터 다운로드</h3>
      </div>

      <div className="admin-filter-row">
        <label className="admin-field">
          형식
          <select className="admin-select" value={format} onChange={(event) => setFormat(event.target.value as "wide" | "long")}>
            <option value="wide">wide</option>
            <option value="long">long</option>
          </select>
        </label>
        <label className="admin-check">
          <input type="checkbox" checked={includeScores} onChange={(event) => setIncludeScores(event.target.checked)} />
          점수 포함
        </label>
        <label className="admin-check">
          <input
            type="checkbox"
            checked={includeCompletionStatus}
            onChange={(event) => setIncludeCompletionStatus(event.target.checked)}
          />
          완료 상태 포함
        </label>
        <label className="admin-check admin-check--warning">
          <input
            type="checkbox"
            checked={includeRiskFlags}
            onChange={(event) => setIncludeRiskFlags(event.target.checked)}
          />
          위험 플래그 포함
        </label>
      </div>

      <p className="admin-warning-text">위험 플래그는 제한 데이터입니다. 운영 목적에 필요한 경우에만 포함하세요.</p>

      <label className="admin-field">
        다운로드 사유
        <textarea
          className="admin-textarea"
          placeholder="행사 종료 후 응답 데이터 확인"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
      </label>

      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      {message ? <div className="admin-alert">{message}</div> : null}

      <div>
        <button
          className="admin-button admin-button--primary"
          type="button"
          disabled={downloading}
          onClick={() => void handleDownload()}
        >
          {downloading ? "다운로드 준비 중" : "CSV 다운로드"}
        </button>
      </div>
    </section>
  );
}
