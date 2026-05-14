import { Button } from "./Button";

type ErrorStateProps = {
  title?: string;
  message: string;
  onRetry?: () => void;
};

export function ErrorState({ title = "다시 시도해 주세요", message, onRetry }: ErrorStateProps) {
  return (
    <div className="state-box state-box--error">
      <h1>{title}</h1>
      <p>{message}</p>
      {onRetry ? <Button onClick={onRetry}>다시 시도</Button> : null}
    </div>
  );
}
