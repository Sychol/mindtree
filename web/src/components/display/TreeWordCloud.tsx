import type { CSSProperties } from "react";

import type { DisplayKeyword } from "../../types/display";

type TreeWordCloudProps = {
  keywords: DisplayKeyword[];
};

function leafStyle(keyword: DisplayKeyword, index: number, minWeight: number, maxWeight: number): CSSProperties {
  const spread = Math.max(maxWeight - minWeight, 1);
  const ratio = (keyword.weight - minWeight) / spread;
  const fontSize = 18 + ratio * 30;
  return {
    "--leaf-index": index,
    fontSize: `${fontSize}px`
  } as CSSProperties;
}

export function TreeWordCloud({ keywords }: TreeWordCloudProps) {
  if (keywords.length === 0) {
    return (
      <div className="tree-cloud tree-cloud--empty">
        <p>아직 마음나무가 자라는 중입니다.</p>
        <span>첫 번째 잎을 남겨보세요.</span>
      </div>
    );
  }

  const visibleKeywords = keywords.slice(0, 40);
  const weights = visibleKeywords.map((keyword) => keyword.weight);
  const minWeight = Math.min(...weights);
  const maxWeight = Math.max(...weights);

  return (
    <div className="tree-cloud" aria-label="마음나무 키워드">
      <div className="tree-cloud__canopy">
        {visibleKeywords.map((keyword, index) => (
          <span
            className={`tree-cloud__leaf tree-cloud__leaf--${keyword.category ?? "neutral"}`}
            key={`${keyword.text}-${index}`}
            style={leafStyle(keyword, index, minWeight, maxWeight)}
          >
            {keyword.text}
          </span>
        ))}
      </div>
      <div className="tree-cloud__trunk" aria-hidden="true" />
    </div>
  );
}
