import type { DisplayKeyword } from "../../types/display";

type KeywordRankingProps = {
  title: string;
  keywords: DisplayKeyword[];
};

export function KeywordRanking({ title, keywords }: KeywordRankingProps) {
  return (
    <section className="display-ranking" aria-label={title}>
      <h2>{title}</h2>
      {keywords.length > 0 ? (
        <ol>
          {keywords.slice(0, 5).map((keyword) => (
            <li key={keyword.text}>
              <span>{keyword.text}</span>
              <strong>{Math.round(keyword.weight)}</strong>
            </li>
          ))}
        </ol>
      ) : (
        <p>아직 키워드가 모이는 중입니다.</p>
      )}
    </section>
  );
}
