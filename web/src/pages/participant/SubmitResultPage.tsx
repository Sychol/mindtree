import { Link, useParams } from "react-router-dom";

import { NoticeBox } from "../../components/common/NoticeBox";
import { useSurveyContent } from "../../hooks/useSurveyContent";

export function SubmitResultPage() {
  const { eventSlug } = useParams();
  const { surveyConfig } = useSurveyContent(eventSlug);
  const thanks = surveyConfig.thanks;
  const summaryPath = `/e/${encodeURIComponent(eventSlug ?? "fire-expo-2026")}/summary`;
  const [primaryParagraph, ...extraParagraphs] = thanks.paragraphs;

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">섹션 8 / 8</p>
        <h1>{thanks.title}</h1>
        {primaryParagraph ? <p>{primaryParagraph}</p> : null}
      </div>
      {extraParagraphs.length ? (
        <NoticeBox tone="safe">
          {extraParagraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </NoticeBox>
      ) : null}
      <Link className="button button--primary button--full" to={summaryPath}>
        마음신호 요약 보기
      </Link>
    </main>
  );
}
