import { ProgressBar } from "../common/ProgressBar";

type ProgressHeaderProps = {
  sectionNo: number;
  totalSections: number;
  title: string;
  description?: string;
  sectionAnswered: number;
  sectionTotal: number;
  answered: number;
  total: number;
};

export function ProgressHeader({
  sectionNo,
  totalSections,
  title,
  description,
  sectionAnswered,
  sectionTotal,
  answered,
  total
}: ProgressHeaderProps) {
  return (
    <header className="progress-header">
      <div>
        <p className="eyebrow">섹션 {sectionNo} / {totalSections}</p>
        <h1>{title}</h1>
        {description ? <p>{description}</p> : null}
      </div>
      <div className="progress-header__bars">
        <ProgressBar
          value={sectionAnswered}
          max={sectionTotal}
          label={`${sectionTotal}개 중 ${sectionAnswered}개 응답 완료`}
        />
        <span>
          전체 {total}개 중 {answered}개 응답
        </span>
      </div>
    </header>
  );
}
