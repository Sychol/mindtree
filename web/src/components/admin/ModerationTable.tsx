import { useMemo, useState } from "react";

import type {
  AdminCardReviewItem,
  AdminManualContentStatusRequest,
  AdminReplyReviewItem,
  AdminReviewRequest,
  ContentOrigin,
} from "../../types/admin";
import {
  adminPromptTypeLabel,
  adminReplyTypeLabel,
  adminStatusLabel,
} from "../../utils/adminLabels";
import { ContentOriginBadge } from "./ContentOriginBadge";
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
  onManualStatus?: (item: ModerationItem, request: AdminManualContentStatusRequest) => Promise<void>;
};

const TRUE_RISK_LABELS: Array<[keyof ModerationItem["riskFlags"], string]> = [
  ["phq9Item9Positive", "PHQ-9 9"],
  ["crisisExpressionDetected", "위기 표현"],
  ["traumaHighSignal", "트라우마 신호"],
  ["moralInjuryHighSignal", "도덕 손상 신호"],
  ["publicRestriction", "공개 제한"],
  ["helpNoticeRequired", "지원 안내 필요"],
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

function itemOrigin(item: ModerationItem): ContentOrigin {
  return item.origin ?? "participant";
}

function isManualStatusOrigin(origin: ContentOrigin): boolean {
  return origin === "admin_manual" || origin === "system_seed";
}

export function ModerationTable({ items, loading, onReview, onManualStatus }: ModerationTableProps) {
  const [drafts, setDrafts] = useState<Record<string, ModerationDraft>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  const emptyText = useMemo(
    () => (loading ? "불러오는 중입니다." : "검토할 항목이 없습니다."),
    [loading]
  );

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

  const handleManualStatus = async (
    item: ModerationItem,
    safetyStatus: AdminManualContentStatusRequest["safetyStatus"],
    publicStatus: AdminManualContentStatusRequest["publicStatus"]
  ) => {
    if (!onManualStatus) {
      return;
    }
    const draft = drafts[item.id] ?? initialDraft(item);
    setSavingId(item.id);
    try {
      await onManualStatus(item, {
        safetyStatus,
        publicStatus,
        reason: draft.reason.trim() || undefined,
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
            <th>출처</th>
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
            const origin = itemOrigin(item);
            const manualStatus = isManualStatusOrigin(origin);
            const targetCardLabel =
              "targetCardId" in item && item.targetCardId ? item.targetCardId.slice(0, 8) : "-";
            const sourceLabel =
              "promptType" in item
                ? adminPromptTypeLabel(item.promptType)
                : `${adminReplyTypeLabel(item.replyType)} / card ${targetCardLabel}`;

            return (
              <tr key={item.id}>
                <td>
                  <strong>{sourceLabel}</strong>
                  <ContentOriginBadge origin={origin} originTag={item.originTag} />
                  {item.sessionId ? <span className="admin-muted">session {item.sessionId.slice(0, 8)}</span> : null}
                  {item.createdByAdminId ? (
                    <span className="admin-muted">admin {item.createdByAdminId.slice(0, 8)}</span>
                  ) : null}
                  <span className="admin-muted">{new Date(item.createdAt).toLocaleString()}</span>
                </td>
                <td>
                  <p className="admin-raw-text">{item.contentRaw}</p>
                  {!manualStatus ? (
                    <textarea
                      aria-label="공개용 수정 문장"
                      className="admin-textarea"
                      onChange={(event) => patchDraft(item, { contentRedacted: event.target.value })}
                      placeholder="공개에 사용할 수정 문장"
                      value={draft.contentRedacted}
                    />
                  ) : null}
                </td>
                <td>
                  <div className="admin-status-stack">
                    <ReviewStatusBadge
                      label={adminStatusLabel(item.safetyStatus)}
                      tone={item.safetyStatus === "safe" ? "safe" : "warning"}
                    />
                    <ReviewStatusBadge
                      label={adminStatusLabel(item.publicStatus)}
                      tone={toneForPublicStatus(item.publicStatus)}
                    />
                  </div>
                  {!manualStatus ? (
                    <>
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
                    </>
                  ) : null}
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
                  {manualStatus ? (
                    <div className="admin-inline-actions">
                      <button
                        className="admin-button admin-button--secondary"
                        disabled={savingId === item.id}
                        onClick={() => void handleManualStatus(item, "safe", "hidden")}
                        type="button"
                      >
                        숨김
                      </button>
                      <button
                        className="admin-button admin-button--secondary"
                        disabled={savingId === item.id}
                        onClick={() => void handleManualStatus(item, "exclude", "excluded")}
                        type="button"
                      >
                        제외
                      </button>
                      <button
                        className="admin-button admin-button--primary"
                        disabled={savingId === item.id}
                        onClick={() => void handleManualStatus(item, "safe", "public")}
                        type="button"
                      >
                        복구
                      </button>
                    </div>
                  ) : (
                    <button
                      className="admin-button admin-button--primary"
                      disabled={savingId === item.id}
                      onClick={() => void handleSubmit(item)}
                      type="button"
                    >
                      {savingId === item.id ? "저장 중" : "저장"}
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
