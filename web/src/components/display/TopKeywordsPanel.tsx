import type { DisplayKeyword } from "../../types/display";
import { KeywordRanking } from "./KeywordRanking";

type TopKeywordsPanelProps = {
  topMindKeywords: DisplayKeyword[];
  topSupportKeywords: DisplayKeyword[];
};

export function TopKeywordsPanel({ topMindKeywords, topSupportKeywords }: TopKeywordsPanelProps) {
  return (
    <div className="display-ranking-grid">
      <KeywordRanking title="마음신호 TOP" keywords={topMindKeywords} />
      <KeywordRanking title="응원·회복 TOP" keywords={topSupportKeywords} />
    </div>
  );
}
