import type { SurveySectionSummary } from "../../types/survey";

type SurveySectionOverviewProps = {
  sections: SurveySectionSummary[];
  onEditSection: (sectionId: string) => void;
};

const FLOW_LABELS: Record<string, string> = {
  intro: "리본톡 소개 및 설문",
  consent: "연구 참여 동의설명문 및 동의서",
  profile: "인구통계",
  kmies: "K-MIES",
  phq9: "K-PHQ-9",
  pcl5: "K-PCL-5",
  kscs: "K-SCS-SF",
  thanks: "참여해주셔서 감사합니다"
};

export function SurveySectionOverview({ sections, onEditSection }: SurveySectionOverviewProps) {
  return (
    <div className="admin-survey-flow">
      {sections.map((section) => (
        <article key={section.id} className="admin-survey-flow__item">
          <div>
            <p className="admin-eyebrow">섹션 {section.sectionNo} / {sections.length}</p>
            <h3>{FLOW_LABELS[section.id] ?? section.title}</h3>
            {FLOW_LABELS[section.id] !== section.title ? <p>{section.title}</p> : null}
            {section.description ? <p>{section.description}</p> : null}
          </div>
          <dl>
            <div>
              <dt>문항 범위</dt>
              <dd>{section.questionNoRange ? section.questionNoRange.join("~") : "-"}</dd>
            </div>
            <div>
              <dt>문항 수</dt>
              <dd>{section.questionCount}</dd>
            </div>
            <div>
              <dt>필수 문항</dt>
              <dd>{section.requiredCount}</dd>
            </div>
          </dl>
          <button
            className="admin-button admin-button--secondary"
            type="button"
            onClick={() => onEditSection(section.id)}
          >
            수정
          </button>
        </article>
      ))}
    </div>
  );
}
