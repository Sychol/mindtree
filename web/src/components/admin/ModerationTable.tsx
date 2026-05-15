import { useMemo, useState } from "react";

import type { AdminCardReviewItem, AdminReplyReviewItem, AdminReviewRequest } from "../../types/admin";
import {
  adminPromptTypeLabel,
  adminReplyTypeLabel,
  adminStatusLabel,
} from "../../utils/adminLabels";
import { ReviewStatusBadge } from "./ReviewStatusBadge";

type ModerationItem = AdminCardReviewItem | AdminReplyReviewItem;

type ModerationDraft = {
  safetyStatus: string;
  publicStatus: string;
  contentRedacted: string;
  reason: string;
};

type ModerationTableProps = {
  items: ModerationItem[];
  loading: boolean;
  onReview: (item: ModerationItem, request: AdminReviewRequest) => Promise<void>;
};

const TRUE_RISK_LABELS: Array<[keyof ModerationItem["riskFlags"], string]> = [
  ["phq9Item9Positive", "PHQ-9 9번"],
  ["crisisExpressionDetected", "위기 표현"],
  ["traumaHighSignal", "외상 신호"],
  ["moralInjuryHighSignal", "도덕적 손상 신호"],
  ["publicRestriction", "공개 제한"],
  ["helpNoticeRequired", "도움 안내 필요"],
];

function initialDraft(item: ModerationItem): ModerationDraft {
  return {
    safetyStatus: item.safetyStatus,
    publicStatus: item.publicStatus,
    contentRedacted: item.contentRedacted ?? "",
    reason: "",
  };
}

function toneForPublicStatus(status: string): "default" | "safe" | "warning" | "danger" {
  if (status === "public") {
    return "safe";
  }
  if (status === "hidden") {
    return "warning";
  }
  if (status === "excluded") {
    return "danger";
  }
  return "default";
}

export function ModerationTable({ items, loading, onReview }: ModerationTableProps) {
  const [drafts, setDrafts] = useState<Record<string, ModerationDraft>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  const emptyText = useMemo(() => (loading ? "불러오는 중입니다." : "검수할 항목이 없습니다."), [loading]);

  const patchDraft = (item: ModerationItem, patch: Partial<ModerationDraft>) => {
    setDrafts((current) => ({
      ...current,
      [item.id]: {
        ...(current[item.id] ?? initialDraft(item)),
        ...patch,
      },
    }));
  };

  const handleSubmit = async (item: ModerationItem) => {
    const draft = drafts[item.id] ?? initialDraft(item);
    setSavingId(item.id);
    try {
      await onReview(item, {
        safetyStatus: draft.safetyStatus,
        publicStatus: draft.publicStatus,
        contentRedacted: draft.contentRedacted.trim() || null,
        reason: draft.reason.trim() || null,
      });
      setDrafts((current) => {
        const next = { ...current };
        delete next[item.id];
        return next;
      });
    } finally {
      setSavingId(null);
    }
  };

  if (!items.length) {
    return <div className="admin-empty">{emptyText}</div>;
  }

  return (
    <div className="admin-table-wrap">
      <table className="admin-table admin-table--moderation">
        <thead>
          <tr>
            <th>원본</th>
            <th>내용</th>
            <th>상태</th>
            <th>위험 플래그</th>
            <th>조치</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const draft = drafts[item.id] ?? initialDraft(item);
            const riskLabels = TRUE_RISK_LABELS.filter(([key]) => item.riskFlags[key]).map(([, label]) => label);
            const sourceLabel =
              "promptType" in item
                ? adminPromptTypeLabel(item.promptType)
                : `${adminReplyTypeLabel(item.replyType)} / 카드 ${item.targetCardId.slice(0, 8)}`;

            return (
              <tr key={item.id}>
                <td>
                  <strong>{sourceLabel}</strong>
                  <span className="admin-muted">{new Date(item.createdAt).toLocaleString()}</span>
                </td>
                <td>
                  <p className="admin-raw-text">{item.contentRaw}</p>
                  <textarea
                    aria-label="공개용 수정 문장"
                    className="admin-textarea"
                    onChange={(event) => patchDraft(item, { contentRedacted: event.target.value })}
                    placeholder="공개할 때 사용할 수정 문장"
                    value={draft.contentRedacted}
                  />
                </td>
                <td>
                  <div className="admin-status-stack">
                    <ReviewStatusBadge label={adminStatusLabel(item.safetyStatus)} tone={item.safetyStatus === "safe" ? "safe" : "warning"} />
                    <ReviewStatusBadge label={adminStatusLabel(item.publicStatus)} tone={toneForPublicStatus(item.publicStatus)} />
                  </div>
                  <select
                    className="admin-select"
                    onChange={(event) => patchDraft(item, { safetyStatus: event.target.value })}
                    value={draft.safetyStatus}
                  >
                    <option value="safe">{adminStatusLabel("safe")}</option>
                    <option value="review">{adminStatusLabel("review")}</option>
                    <option value="exclude">{adminStatusLabel("exclude")}</option>
                  </select>
                  <select
                    className="admin-select"
                    onChange={(event) => patchDraft(item, { publicStatus: event.target.value })}
                    value={draft.publicStatus}
                  >
                    <option value="pending">{adminStatusLabel("pending")}</option>
                    <option value="public">{adminStatusLabel("public")}</option>
                    <option value="hidden">{adminStatusLabel("hidden")}</option>
                    <option value="excluded">{adminStatusLabel("excluded")}</option>
                  </select>
                </td>
                <td>
                  {riskLabels.length ? (
                    <div className="admin-risk-list">
                      {riskLabels.map((label) => (
                        <ReviewStatusBadge key={label} label={label} tone="danger" />
                      ))}
                    </div>
                  ) : (
                    <span className="admin-muted">없음</span>
                  )}
                </td>
                <td>
                  <input
                    className="admin-input"
                    onChange={(event) => patchDraft(item, { reason: event.target.value })}
                    placeholder="처리 사유"
                    type="text"
                    value={draft.reason}
                  />
                  <button
                    className="admin-button admin-button--primary"
                    disabled={savingId === item.id}
                    onClick={() => void handleSubmit(item)}
                    type="button"
                  >
                    {savingId === item.id ? "저장 중" : "저장"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
