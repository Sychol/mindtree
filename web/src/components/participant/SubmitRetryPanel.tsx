import { RetryNotice } from "../common/RetryNotice";

type SubmitRetryPanelProps = {
  error?: string;
  pending: boolean;
  canRetry: boolean;
  onRetry: () => void;
};

export function SubmitRetryPanel({ error, pending, canRetry, onRetry }: SubmitRetryPanelProps) {
  if (!error) {
    return null;
  }

  return (
    <RetryNotice
      message={error}
      pending={pending}
      onRetry={canRetry ? onRetry : undefined}
    />
  );
}
