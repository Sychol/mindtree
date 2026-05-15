import type { DisplayConnectionStatus } from "../../types/display";

type ConnectionStatusBadgeProps = {
  status: DisplayConnectionStatus;
};

const STATUS_TEXT: Record<DisplayConnectionStatus, string> = {
  connecting: "연결 중",
  connected: "실시간 연결됨",
  reconnecting: "연결 재시도 중입니다. 마지막 데이터를 표시하고 있습니다.",
  polling: "보조 갱신 중입니다.",
  disconnected: "연결이 끊겼습니다. 마지막 데이터를 표시하고 있습니다."
};

export function ConnectionStatusBadge({ status }: ConnectionStatusBadgeProps) {
  return <span className={`display-status display-status--${status}`}>{STATUS_TEXT[status]}</span>;
}
