import type { DisplayKeyword } from "../../types/display";
import { CanopyWordCloud } from "./CanopyWordCloud";
import { TrunkWordCloud } from "./TrunkWordCloud";

type TreeWordCloudProps = {
  keywords: DisplayKeyword[];
};

function isMindSignalKeyword(keyword: DisplayKeyword): boolean {
  if (keyword.displayPart) {
    return keyword.displayPart === "trunk";
  }
  return keyword.category === "mind_signal";
}

function isCanopyKeyword(keyword: DisplayKeyword): boolean {
  if (keyword.displayPart) {
    return keyword.displayPart === "canopy";
  }
  return (
    keyword.category === "support" ||
    keyword.category === "recovery" ||
    keyword.category === "coping" ||
    keyword.category === "neutral" ||
    !keyword.category
  );
}

export function TreeWordCloud({ keywords }: TreeWordCloudProps) {
  const mindSignalKeywords = keywords.filter(isMindSignalKeyword);
  const supportKeywords = keywords.filter(isCanopyKeyword);

  if (keywords.length === 0) {
    return (
      <div className="maeum-tree maeum-tree--empty">
        <p>아직 마음나무가 자라는 중입니다.</p>
        <span>첫 번째 잎을 남겨보세요.</span>
        <div className="maeum-tree__ground" aria-hidden="true" />
      </div>
    );
  }

  return (
    <div className="maeum-tree" aria-label="마음나무 키워드">
      <CanopyWordCloud keywords={supportKeywords} />
      <TrunkWordCloud keywords={mindSignalKeywords} />
      <div className="maeum-tree__ground" aria-hidden="true" />
    </div>
  );
}
