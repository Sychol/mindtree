import type { CSSProperties } from "react";

import { layoutCanopyKeywords } from "../../lib/displayTreeLayout";
import type { DisplayKeyword } from "../../types/display";

type CanopyWordCloudProps = {
  keywords: DisplayKeyword[];
};

function categoryClass(category: string | null | undefined): string {
  if (category === "support" || category === "recovery" || category === "coping" || category === "neutral") {
    return category;
  }
  return "neutral";
}

export function CanopyWordCloud({ keywords }: CanopyWordCloudProps) {
  const positionedKeywords = layoutCanopyKeywords(keywords);

  return (
    <div className="maeum-tree__canopy" aria-label="응원과 회복 키워드">
      {positionedKeywords.map((keyword, index) => (
        <span
          className={`canopy-keyword canopy-keyword--${categoryClass(keyword.category)} canopy-keyword--tone-${keyword.colorVariant}`}
          key={`${keyword.text}-${keyword.category ?? "neutral"}-${index}`}
          style={
            {
              left: `${keyword.left}%`,
              top: `${keyword.top}%`,
              fontSize: `${keyword.fontSize}px`,
              opacity: keyword.opacity,
              transform: `translate(-50%, -50%) rotate(${keyword.rotate}deg)`,
            } as CSSProperties
          }
        >
          {keyword.text}
        </span>
      ))}
    </div>
  );
}
