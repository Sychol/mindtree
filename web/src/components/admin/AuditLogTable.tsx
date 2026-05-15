import type { AdminAuditLogItem } from "../../types/admin";

type AuditLogTableProps = {
  items: AdminAuditLogItem[];
  loading: boolean;
};

export function AuditLogTable({ items, loading }: AuditLogTableProps) {
  if (!items.length) {
    return <div className="admin-empty">{loading ? "Loading..." : "No audit logs."}</div>;
  }

  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Action</th>
            <th>Target</th>
            <th>Admin</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{new Date(item.createdAt).toLocaleString()}</td>
              <td>{item.action}</td>
              <td>
                {item.targetType}
                {item.targetId ? <span className="admin-muted"> {item.targetId.slice(0, 8)}</span> : null}
              </td>
              <td>{item.adminUserId?.slice(0, 8) ?? "-"}</td>
              <td>{item.reason ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
