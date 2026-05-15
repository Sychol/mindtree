import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { listAuditLogs } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import { AuditLogTable } from "../../components/admin/AuditLogTable";
import type { AdminAuditLogItem } from "../../types/admin";
import {
  adminActionLabel,
  adminErrorMessage,
  adminTargetTypeLabel,
  AUDIT_ACTION_FILTERS,
  AUDIT_TARGET_FILTERS,
} from "../../utils/adminLabels";

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return adminErrorMessage(error, "감사 로그를 불러오지 못했습니다.");
  }
  return "감사 로그를 불러오지 못했습니다.";
}

export function AdminAuditLogsPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const [action, setAction] = useState("");
  const [targetType, setTargetType] = useState("");
  const [items, setItems] = useState<AdminAuditLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listAuditLogs(eventSlug, { action, targetType });
      setItems(response.items);
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [eventSlug, action, targetType]);

  return (
    <section className="admin-section">
      <div className="admin-section__header">
        <div>
          <p className="admin-eyebrow">{items.length}건</p>
          <h2>감사 로그</h2>
        </div>
        <div className="admin-filter-row">
          <select className="admin-select" onChange={(event) => setAction(event.target.value)} value={action}>
            {AUDIT_ACTION_FILTERS.map((value) => (
              <option key={value || "all"} value={value}>
                {adminActionLabel(value)}
              </option>
            ))}
          </select>
          <select className="admin-select" onChange={(event) => setTargetType(event.target.value)} value={targetType}>
            {AUDIT_TARGET_FILTERS.map((value) => (
              <option key={value || "all"} value={value}>
                {value ? adminTargetTypeLabel(value) : "전체 대상"}
              </option>
            ))}
          </select>
        </div>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      <AuditLogTable items={items} loading={loading} />
    </section>
  );
}
