import { NoticeBox } from "../common/NoticeBox";
import type { RiskNotice } from "../../types/summary";

type HelpNoticeProps = {
  riskNotice: RiskNotice;
};

const DEFAULT_MESSAGE =
  "혼자 감당하기 어렵거나 자신을 해치고 싶은 생각이 든다면, 가까운 사람이나 현장 운영자에게 바로 도움을 요청해 주세요. 이 안내는 진단이나 치료가 아니라 안전을 위한 안내입니다.";

export function HelpNotice({ riskNotice }: HelpNoticeProps) {
  if (!riskNotice.showHelpNotice) {
    return null;
  }

  return (
    <NoticeBox tone="warning" title="도움 안내">
      <p>{riskNotice.text ?? DEFAULT_MESSAGE}</p>
    </NoticeBox>
  );
}
