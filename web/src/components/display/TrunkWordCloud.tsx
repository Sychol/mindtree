import { useMemo, type CSSProperties } from "react";

import { layoutTrunkKeywords } from "../../lib/displayTreeLayout";
import type { DisplayKeyword } from "../../types/display";

type TrunkWordCloudProps = {
  keywords: DisplayKeyword[];
};

export function TrunkWordCloud({ keywords }: TrunkWordCloudProps) {
  const positionedKeywords = useMemo(() => layoutTrunkKeywords(keywords), [keywords]);

  return (
    <div className="maeum-tree__trunk" aria-label="마음신호 키워드">
      {positionedKeywords.map((keyword, index) => (
        <span
          className={`trunk-keyword trunk-keyword--tone-${keyword.colorVariant}`}
          key={`${keyword.text}-${index}`}
          style={
            {
              left: `${keyword.x}%`,
              top: `${keyword.y}%`,
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
