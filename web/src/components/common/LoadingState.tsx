type LoadingStateProps = {
  title?: string;
  message?: string;
};

export function LoadingState({
  title = "불러오는 중입니다",
  message = "잠시만 기다려 주세요."
}: LoadingStateProps) {
  return (
    <div className="state-box" role="status">
      <div className="spinner" aria-hidden="true" />
      <h1>{title}</h1>
      <p>{message}</p>
    </div>
  );
}
