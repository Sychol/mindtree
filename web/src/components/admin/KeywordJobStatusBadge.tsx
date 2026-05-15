type KeywordJobStatusBadgeProps = {
  status: string;
};

function toneForStatus(status: string): string {
  if (status === "succeeded") {
    return "safe";
  }
  if (status === "failed" || status === "retry_wait") {
    return "danger";
  }
  if (status === "processing" || status === "pending") {
    return "warning";
  }
  return "default";
}

export function KeywordJobStatusBadge({ status }: KeywordJobStatusBadgeProps) {
  return <span className={`admin-badge admin-badge--${toneForStatus(status)}`}>{status}</span>;
}
