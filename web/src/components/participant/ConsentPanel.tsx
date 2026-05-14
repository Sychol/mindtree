import type { ConsentAcceptedItems } from "../../types/session";
import { Button } from "../common/Button";
import { NoticeBox } from "../common/NoticeBox";

type ConsentPanelProps = {
  value: ConsentAcceptedItems;
  pending: boolean;
  onChange: (value: ConsentAcceptedItems) => void;
  onSubmit: () => void;
};

const CONSENT_ITEMS: Array<{
  key: keyof ConsentAcceptedItems;
  text: string;
}> = [
  {
    key: "eventIsNotDiagnosis",
    text: "본 이벤트는 진단이나 치료가 아닌 체험형 마음 점검입니다."
  },
  {
    key: "anonymousKeywordDisplay",
    text: "TV에는 원문이 아닌 익명 키워드만 표시됩니다."
  },
  {
    key: "cardMayBeShownAnonymously",
    text: "마음카드는 익명 상태로 다른 참가자에게 보일 수 있습니다."
  },
  {
    key: "noIdentifyingInfo",
    text: "실명, 소속, 연락처, 구체적 장소, 날짜, 사건명은 입력하지 않습니다."
  },
  {
    key: "adminModeration",
    text: "관리자는 개인정보, 위기 표현, 부적절 표현을 수정, 숨김, 삭제할 수 있습니다."
  }
];

export const EMPTY_CONSENT: ConsentAcceptedItems = {
  eventIsNotDiagnosis: false,
  anonymousKeywordDisplay: false,
  cardMayBeShownAnonymously: false,
  noIdentifyingInfo: false,
  adminModeration: false
};

export function ConsentPanel({ value, pending, onChange, onSubmit }: ConsentPanelProps) {
  const allChecked = Object.values(value).every(Boolean);

  return (
    <section className="panel">
      <NoticeBox title="참여 전 확인" tone="info">
        <p>아래 내용을 확인한 뒤 문항 응답을 시작합니다.</p>
      </NoticeBox>
      <div className="check-list">
        {CONSENT_ITEMS.map((item) => (
          <label key={item.key} className="check-row">
            <input
              type="checkbox"
              checked={value[item.key]}
              onChange={(event) =>
                onChange({
                  ...value,
                  [item.key]: event.target.checked
                })
              }
            />
            <span>{item.text}</span>
          </label>
        ))}
      </div>
      <Button fullWidth disabled={!allChecked || pending} onClick={onSubmit}>
        {pending ? "저장 중" : "동의하고 시작"}
      </Button>
    </section>
  );
}
