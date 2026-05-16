import type { DisplayConnectionStatus } from "../../types/display";

type LiveBadgeProps = {
  status: DisplayConnectionStatus;
};

export function LiveBadge({ status }: LiveBadgeProps) {
  return (
    <div className={`live-badge live-badge--${status}`} aria-label={`LIVE ${status}`}>
      <span aria-hidden="true" />
      LIVE
    </div>
  );
}
