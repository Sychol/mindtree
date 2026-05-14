type ProgressBarProps = {
  value: number;
  max: number;
  label?: string;
};

export function ProgressBar({ value, max, label }: ProgressBarProps) {
  const ratio = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;

  return (
    <div className="progress" aria-label={label ?? "진행률"}>
      <div className="progress__track">
        <div className="progress__bar" style={{ width: `${ratio}%` }} />
      </div>
      {label ? <span>{label}</span> : null}
    </div>
  );
}
