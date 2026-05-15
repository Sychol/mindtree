type ReviewStatusBadgeProps = {
  label: string;
  tone?: "default" | "safe" | "warning" | "danger";
};

export function ReviewStatusBadge({ label, tone = "default" }: ReviewStatusBadgeProps) {
  return <span className={`admin-badge admin-badge--${tone}`}>{label}</span>;
}
