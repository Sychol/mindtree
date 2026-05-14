import { ProgressBar } from "../common/ProgressBar";

type ProgressHeaderProps = {
  current: number;
  total: number;
  answered: number;
  sectionName: string;
};

export function ProgressHeader({ current, total, answered, sectionName }: ProgressHeaderProps) {
  return (
    <header className="progress-header">
      <div>
        <p className="eyebrow">{sectionName}</p>
        <h1>
          {current} / {total}
        </h1>
      </div>
      <ProgressBar value={answered} max={total} label={`${answered}개 응답`} />
    </header>
  );
}
