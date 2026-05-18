import type { ConsentAcceptedItems } from "../../types/session";
import type { SurveyConsentItem } from "../../types/survey";
import { Button } from "../common/Button";
import { NoticeBox } from "../common/NoticeBox";

type ConsentPanelProps = {
  value: ConsentAcceptedItems;
  pending: boolean;
  items?: SurveyConsentItem[];
  onChange: (value: ConsentAcceptedItems) => void;
  onSubmit: () => void;
};

const CONSENT_ITEMS: SurveyConsentItem[] = [
  {
    key: "researchParticipationConsent",
    label: "[필수] 연구 참여 동의",
    description: "연구의 목적, 절차, 예상 소요시간, 예상되는 불편감, 연구 참여 중단 및 철회 가능성에 대한 설명을 확인하였으며, 자발적으로 본 연구에 참여하는 것에 동의합니다.",
    required: true
  },
  {
    key: "personalDataUseConsent",
    label: "[필수] 개인정보 수집·이용 동의",
    description: "연령대, 성별, 직무 관련 정보, 사건 경험 관련 정보, 설문 응답자료를 연구 목적의 통계 분석, 학술연구 및 서비스 개선에 이용하는 것에 동의합니다.",
    required: true
  },
  {
    key: "sensitiveInfoConsent",
    label: "[필수] 민감정보 처리 동의",
    description: "우울감, 자해 관련 생각, 외상 경험, 심리적 고통, 상담·병원 이용 경험 등 건강 또는 정신건강과 관련될 수 있는 문항이 포함되어 있음을 확인하였으며, 해당 정보를 연구 목적의 분석에 이용하는 것에 동의합니다.",
    required: true
  },
  {
    key: "deidentifiedAiRagUseConsent",
    label: "[필수] 비식별 자료의 AI 학습/RAG 활용 동의",
    description: "응답자료가 익명화·가명화 등 비식별 처리된 후 AI 상담 서비스 리본톡의 성능 개선, AI 학습 데이터 구축 또는 RAG 데이터 구축에 활용될 수 있음에 동의합니다.",
    required: true
  }
];

export const EMPTY_CONSENT: ConsentAcceptedItems = {
  researchParticipationConsent: false,
  personalDataUseConsent: false,
  sensitiveInfoConsent: false,
  deidentifiedAiRagUseConsent: false
};

export function ConsentPanel({ value, pending, items = CONSENT_ITEMS, onChange, onSubmit }: ConsentPanelProps) {
  const requiredItems = items.filter((item) => item.required);
  const allChecked = requiredItems.every((item) => value[item.key]);

  return (
    <section className="panel consent-check-panel">
      <NoticeBox title="필수 동의 항목" tone="info">
        <p>아래 4개 항목에 모두 동의해야 설문을 시작할 수 있습니다.</p>
      </NoticeBox>
      <div className="check-list">
        {items.map((item) => (
          <label key={item.key} className="check-row consent-checkbox-card">
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
            <span>
              <strong>{item.label}</strong>
              {item.description}
            </span>
          </label>
        ))}
      </div>
      <Button fullWidth disabled={!allChecked || pending} onClick={onSubmit}>
        {pending ? "저장 중" : "모두 동의하고 설문 시작"}
      </Button>
    </section>
  );
}
