import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { listAdminResponses } from "../../api/admin";
import { ResponseExportPanel } from "../../components/admin/ResponseExportPanel";
import { ResponsesTable } from "../../components/admin/ResponsesTable";
import type {
  AdminResponseColumn,
  AdminResponseRowValue,
  AdminResponsesView,
} from "../../types/admin";
import { adminErrorMessage, adminStatusLabel } from "../../utils/adminLabels";

const PAGE_SIZE = 50;
const STATUS_OPTIONS = [
  "all",
  "created",
  "consented",
  "questions_completed",
  "summary_viewed",
  "card_created",
  "reply_created",
  "completed",
];

export function AdminResponsesPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const [view, setView] = useState<AdminResponsesView>("summary");
  const [status, setStatus] = useState("all");
  const [completedOnly, setCompletedOnly] = useState(false);
  const [includeScores, setIncludeScores] = useState(true);
  const [includeRiskFlags, setIncludeRiskFlags] = useState(false);
  const [includeCompletionStatus, setIncludeCompletionStatus] = useState(true);
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [columns, setColumns] = useState<AdminResponseColumn[]>([]);
  const [rows, setRows] = useState<Array<Record<string, AdminResponseRowValue>>>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filterKey = useMemo(
    () =>
      JSON.stringify({
        eventSlug,
        view,
        status,
        completedOnly,
        includeScores,
        includeRiskFlags,
        includeCompletionStatus,
        createdFrom,
        createdTo,
      }),
    [
      eventSlug,
      view,
      status,
      completedOnly,
      includeScores,
      includeRiskFlags,
      includeCompletionStatus,
      createdFrom,
      createdTo,
    ]
  );

  useEffect(() => {
    setOffset(0);
  }, [filterKey]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void listAdminResponses(eventSlug, {
      view,
      status,
      completedOnly,
      includeScores,
      includeRiskFlags,
      includeCompletionStatus,
      createdFrom: createdFrom || undefined,
      createdTo: createdTo || undefined,
      limit: PAGE_SIZE,
      offset,
    })
      .then((response) => {
        if (!cancelled) {
          setColumns(response.columns);
          setRows(response.rows);
          setTotal(response.total);
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(adminErrorMessage(requestError, "응답 데이터를 불러오지 못했습니다."));
          setColumns([]);
          setRows([]);
          setTotal(0);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [
    eventSlug,
    view,
    status,
    completedOnly,
    includeScores,
    includeRiskFlags,
    includeCompletionStatus,
    createdFrom,
    createdTo,
    offset,
  ]);

  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="admin-section">
      <div className="admin-section__header">
        <div>
          <p className="admin-eyebrow">관리자 전용 제한 데이터입니다.</p>
          <h2>응답 데이터</h2>
        </div>
        <span className="admin-badge">{total} sessions</span>
      </div>

      <div className="admin-response-grid">
        <section className="admin-response-filters" aria-label="응답 데이터 필터">
          <label className="admin-field">
            보기
            <select className="admin-select" value={view} onChange={(event) => setView(event.target.value as AdminResponsesView)}>
              <option value="summary">summary</option>
              <option value="wide">wide</option>
              <option value="long">long</option>
            </select>
          </label>
          <label className="admin-field">
            상태
            <select className="admin-select" value={status} onChange={(event) => setStatus(event.target.value)}>
              {STATUS_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value === "all" ? "전체" : adminStatusLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label className="admin-field">
            생성 시작
            <input
              className="admin-input"
              type="datetime-local"
              value={createdFrom}
              onChange={(event) => setCreatedFrom(event.target.value)}
            />
          </label>
          <label className="admin-field">
            생성 종료
            <input
              className="admin-input"
              type="datetime-local"
              value={createdTo}
              onChange={(event) => setCreatedTo(event.target.value)}
            />
          </label>
          <label className="admin-check">
            <input type="checkbox" checked={completedOnly} onChange={(event) => setCompletedOnly(event.target.checked)} />
            완료 세션만
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
          <p className="admin-warning-text">위험 플래그는 제한 데이터입니다. 운영 목적에 필요한 경우에만 포함하세요.</p>
        </section>

        <ResponseExportPanel
          eventSlug={eventSlug}
          status={status}
          completedOnly={completedOnly}
          createdFrom={createdFrom}
          createdTo={createdTo}
        />
      </div>

      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}

      <ResponsesTable columns={columns} rows={rows} loading={loading} />

      <div className="admin-pagination">
        <button
          className="admin-button admin-button--secondary"
          type="button"
          disabled={offset <= 0 || loading}
          onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
        >
          이전
        </button>
        <span>
          {currentPage} / {maxPage}
        </span>
        <button
          className="admin-button admin-button--secondary"
          type="button"
          disabled={offset + PAGE_SIZE >= total || loading}
          onClick={() => setOffset(offset + PAGE_SIZE)}
        >
          다음
        </button>
      </div>
    </section>
  );
}
