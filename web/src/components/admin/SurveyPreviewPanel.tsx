import type { AdminSurveyResponse } from "../../types/survey";

type SurveyPreviewPanelProps = {
  data: AdminSurveyResponse;
};

export function SurveyPreviewPanel({ data }: SurveyPreviewPanelProps) {
  const { surveyConfig } = data;
  const sectionSummariesById = new Map(
    data.sectionSummaries.map((section) => [section.id, section])
  );
  const totalQuestionCount = data.questionsBySection.reduce(
    (sum, section) => sum + section.questions.length,
    0
  );

  return (
    <div className="admin-survey-preview">
      <section className="admin-survey-preview__block">
        <p className="admin-eyebrow">섹션 1 / 8</p>
        <h3>{surveyConfig.intro.title}</h3>
        {surveyConfig.intro.subtitle ? <strong>{surveyConfig.intro.subtitle}</strong> : null}
        {surveyConfig.intro.paragraphs.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </section>

      <section className="admin-survey-preview__block">
        <p className="admin-eyebrow">섹션 2 / 8</p>
        <h3>{surveyConfig.consent.title}</h3>
        {surveyConfig.consent.sections.map((section) => (
          <article key={section.heading}>
            <h4>{section.heading}</h4>
            {section.paragraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </article>
        ))}
        <ul>
          {surveyConfig.consent.items.map((item) => (
            <li key={item.key}>
              <strong>{item.label}</strong>
              <span>{item.description}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="admin-survey-preview__block">
        <p className="admin-eyebrow">문항 섹션 · 총 {totalQuestionCount}문항</p>
        {data.questionsBySection.map((section) => (
          <article key={section.sectionId} className="admin-survey-preview__section">
            <h3>{section.sectionNo}. {section.title}</h3>
            <p>
              문항 {sectionSummariesById.get(section.sectionId)?.questionNoRange?.join("~") ?? "-"} ·{" "}
              {section.questions.length}문항
            </p>
            {section.questions.map((question) => (
              <div key={question.id} className="admin-survey-preview__question">
                <span>문항 {question.questionNo}</span>
                <strong>{question.displayTitle}</strong>
                {question.displayDescription ? <p>{question.displayDescription}</p> : null}
              </div>
            ))}
          </article>
        ))}
      </section>

      <section className="admin-survey-preview__block">
        <p className="admin-eyebrow">섹션 8 / 8</p>
        <h3>{surveyConfig.thanks.title}</h3>
        {surveyConfig.thanks.paragraphs.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </section>
    </div>
  );
}
