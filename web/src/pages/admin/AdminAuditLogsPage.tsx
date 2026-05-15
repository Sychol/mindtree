import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { listAuditLogs } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import { AuditLogTable } from "../../components/admin/AuditLogTable";
import type { AdminAuditLogItem } from "../../types/admin";

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  return "Request failed.";
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
          <p className="admin-eyebrow">{items.length} logs</p>
          <h2>Audit logs</h2>
        </div>
        <div className="admin-filter-row">
          <input
            className="admin-input"
            onChange={(event) => setAction(event.target.value)}
            placeholder="action"
            value={action}
          />
          <input
            className="admin-input"
            onChange={(event) => setTargetType(event.target.value)}
            placeholder="target type"
            value={targetType}
          />
        </div>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      <AuditLogTable items={items} loading={loading} />
    </section>
  );
}
