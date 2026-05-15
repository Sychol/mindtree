import type { AdminAuditLogItem } from "../../types/admin";
import { adminActionLabel, adminTargetTypeLabel } from "../../utils/adminLabels";

type AuditLogTableProps = {
  items: AdminAuditLogItem[];
  loading: boolean;
};

export function AuditLogTable({ items, loading }: AuditLogTableProps) {
  if (!items.length) {
    return <div className="admin-empty">{loading ? "불러오는 중입니다." : "감사 로그가 없습니다."}</div>;
  }

  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>시각</th>
            <th>작업</th>
            <th>대상</th>
            <th>관리자</th>
            <th>사유</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{new Date(item.createdAt).toLocaleString()}</td>
              <td>{adminActionLabel(item.action)}</td>
              <td>
                {adminTargetTypeLabel(item.targetType)}
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
