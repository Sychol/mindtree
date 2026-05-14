import { Button } from "./Button";

type RetryNoticeProps = {
  message?: string;
  onRetry?: () => void;
  pending?: boolean;
};

export function RetryNotice({
  message = "일시적으로 연결이 원활하지 않습니다. 입력한 내용은 유지되어 있습니다.",
  onRetry,
  pending = false
}: RetryNoticeProps) {
  return (
    <div className="notice notice--retry" role="alert">
      <p>{message}</p>
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry} disabled={pending}>
          {pending ? "재시도 중" : "다시 제출"}
        </Button>
      ) : null}
    </div>
  );
}
