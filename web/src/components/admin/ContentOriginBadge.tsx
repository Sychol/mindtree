import type { ContentOrigin } from "../../types/admin";

type ContentOriginBadgeProps = {
  origin?: ContentOrigin | string | null;
  originTag?: string | null;
};

const ORIGIN_LABELS: Record<ContentOrigin, string> = {
  participant: "실제 수집",
  admin_manual: "관리자 추가",
  system_seed: "Seed",
};

function toneForOrigin(origin?: string | null): string {
  if (origin === "participant") {
    return "safe";
  }
  if (origin === "admin_manual") {
    return "warning";
  }
  if (origin === "system_seed") {
    return "default";
  }
  return "default";
}

export function ContentOriginBadge({ origin, originTag }: ContentOriginBadgeProps) {
  const label = ORIGIN_LABELS[origin as ContentOrigin] ?? "실제 수집";
  const detail = originTag ? ` · ${originTag}` : "";

  return <span className={`admin-badge admin-badge--${toneForOrigin(origin)}`}>{label}{detail}</span>;
}
