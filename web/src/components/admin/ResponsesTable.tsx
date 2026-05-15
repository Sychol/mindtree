import type { AdminResponseColumn, AdminResponseRowValue } from "../../types/admin";

type ResponsesTableProps = {
  columns: AdminResponseColumn[];
  rows: Array<Record<string, AdminResponseRowValue>>;
  loading: boolean;
};

function displayValue(value: AdminResponseRowValue): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  return String(value);
}

export function ResponsesTable({ columns, rows, loading }: ResponsesTableProps) {
  if (!rows.length) {
    return (
      <div className="admin-empty">
        {loading ? "응답 데이터를 불러오는 중입니다." : "조건에 맞는 응답 데이터가 없습니다."}
      </div>
    );
  }

  return (
    <div className="admin-table-wrap admin-response-table-wrap">
      <table className="admin-table admin-response-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} title={column.label}>
                <span>{column.key}</span>
                <small>{column.label}</small>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${row.sessionShortId ?? rowIndex}-${rowIndex}`}>
              {columns.map((column) => (
                <td key={column.key} title={displayValue(row[column.key])}>
                  {displayValue(row[column.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
