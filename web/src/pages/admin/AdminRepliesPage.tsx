import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "react-router-dom";

import {
  createManualReply,
  listAdminReplies,
  reviewAdminReply,
  updateManualReplyStatus,
} from "../../api/admin";
import { ApiClientError } from "../../api/client";
import { ModerationTable } from "../../components/admin/ModerationTable";
import type {
  AdminManualContentStatusRequest,
  AdminManualReplyCreateRequest,
  AdminReplyReviewItem,
  AdminReviewItemBase,
  AdminReviewRequest,
} from "../../types/admin";
import { adminErrorMessage, adminReplyTypeLabel, adminStatusLabel } from "../../utils/adminLabels";

const ORIGINS = ["all", "participant", "admin_manual", "system_seed"] as const;
const REPLY_TYPES: AdminManualReplyCreateRequest["replyType"][] = [
  "comfort",
  "empathy",
  "small_coping",
];
const PUBLIC_STATUSES: Array<NonNullable<AdminManualReplyCreateRequest["publicStatus"]>> = [
  "public",
  "pending",
  "hidden",
  "excluded",
];

type ManualReplyForm = {
  replyType: AdminManualReplyCreateRequest["replyType"];
  content: string;
  targetCardId: string;
  originTag: string;
  publicStatus: NonNullable<AdminManualReplyCreateRequest["publicStatus"]>;
  createKeywordJob: boolean;
  reason: string;
};

const DEFAULT_MANUAL_FORM: ManualReplyForm = {
  replyType: "comfort",
  content: "",
  targetCardId: "",
  originTag: "운영자추가",
  publicStatus: "public",
  createKeywordJob: true,
  reason: "",
};

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return adminErrorMessage(error, "응원문장 요청을 처리하지 못했습니다.");
  }
  return "응원문장 요청을 처리하지 못했습니다.";
}

function originLabel(value: string): string {
  if (value === "participant") {
    return "실제 수집";
  }
  if (value === "admin_manual") {
    return "관리자 추가";
  }
  if (value === "system_seed") {
    return "Seed";
  }
  return "전체 출처";
}

export function AdminRepliesPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const [status, setStatus] = useState("all");
  const [origin, setOrigin] = useState<(typeof ORIGINS)[number]>("all");
  const [items, setItems] = useState<AdminReplyReviewItem[]>([]);
  const [total, setTotal] = useState(0);
  const [manualForm, setManualForm] = useState<ManualReplyForm>(DEFAULT_MANUAL_FORM);
  const [loading, setLoading] = useState(false);
  const [submittingManual, setSubmittingManual] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listAdminReplies(eventSlug, { status, origin });
      setItems(response.items);
      setTotal(response.total);
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [eventSlug, status, origin]);

  const patchManualForm = (patch: Partial<ManualReplyForm>) => {
    setManualForm((current) => ({ ...current, ...patch }));
  };

  const handleManualSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmittingManual(true);
    setError(null);
    try {
      await createManualReply(eventSlug, {
        replyType: manualForm.replyType,
        content: manualForm.content,
        targetCardId: manualForm.targetCardId.trim() || null,
        originTag: manualForm.originTag.trim() || undefined,
        publicStatus: manualForm.publicStatus,
        createKeywordJob: manualForm.createKeywordJob,
        reason: manualForm.reason.trim() || undefined,
      });
      setManualForm(DEFAULT_MANUAL_FORM);
      await load();
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setSubmittingManual(false);
    }
  };

  const handleReview = async (item: AdminReviewItemBase, request: AdminReviewRequest) => {
    await reviewAdminReply(item.id, request);
    await load();
  };

  const handleManualStatus = async (
    item: AdminReviewItemBase,
    request: AdminManualContentStatusRequest
  ) => {
    await updateManualReplyStatus(item.id, request);
    await load();
  };

  return (
    <div className="admin-page-stack">
      <section className="admin-section">
        <div className="admin-section__header">
          <div>
            <p className="admin-eyebrow">manual reply</p>
            <h2>수동 응원문장 추가</h2>
          </div>
        </div>
        <form className="admin-form-grid" onSubmit={handleManualSubmit}>
          <label className="admin-field">
            문장 유형
            <select
              className="admin-select"
              onChange={(event) =>
                patchManualForm({ replyType: event.target.value as ManualReplyForm["replyType"] })
              }
              value={manualForm.replyType}
            >
              {REPLY_TYPES.map((value) => (
                <option key={value} value={value}>
                  {adminReplyTypeLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label className="admin-field admin-field--wide">
            내용
            <textarea
              className="admin-textarea"
              maxLength={300}
              onChange={(event) => patchManualForm({ content: event.target.value })}
              required
              value={manualForm.content}
            />
          </label>
          <label className="admin-field">
            대상 카드 ID
            <input
              className="admin-input"
              onChange={(event) => patchManualForm({ targetCardId: event.target.value })}
              placeholder="선택 사항"
              value={manualForm.targetCardId}
            />
          </label>
          <label className="admin-field">
            출처 태그
            <input
              className="admin-input"
              maxLength={30}
              onChange={(event) => patchManualForm({ originTag: event.target.value })}
              value={manualForm.originTag}
            />
          </label>
          <label className="admin-field">
            공개 상태
            <select
              className="admin-select"
              onChange={(event) =>
                patchManualForm({
                  publicStatus: event.target.value as ManualReplyForm["publicStatus"],
                })
              }
              value={manualForm.publicStatus}
            >
              {PUBLIC_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {adminStatusLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label className="admin-field admin-field--checkbox">
            <input
              checked={manualForm.createKeywordJob}
              onChange={(event) => patchManualForm({ createKeywordJob: event.target.checked })}
              type="checkbox"
            />
            키워드 작업 생성
          </label>
          <label className="admin-field admin-field--wide">
            사유
            <input
              className="admin-input"
              maxLength={500}
              onChange={(event) => patchManualForm({ reason: event.target.value })}
              value={manualForm.reason}
            />
          </label>
          <div className="admin-form-actions">
            <button className="admin-button admin-button--primary" disabled={submittingManual} type="submit">
              추가
            </button>
          </div>
        </form>
      </section>

      <section className="admin-section">
        <div className="admin-section__header">
          <div>
            <p className="admin-eyebrow">{total}건</p>
            <h2>응원문장 검토</h2>
          </div>
          <div className="admin-filter-row">
            <select className="admin-select" onChange={(event) => setStatus(event.target.value)} value={status}>
              <option value="review">{adminStatusLabel("review")}</option>
              <option value="safe">{adminStatusLabel("safe")}</option>
              <option value="exclude">{adminStatusLabel("exclude")}</option>
              <option value="pending">{adminStatusLabel("pending")}</option>
              <option value="public">{adminStatusLabel("public")}</option>
              <option value="hidden">{adminStatusLabel("hidden")}</option>
              <option value="excluded">{adminStatusLabel("excluded")}</option>
              <option value="all">{adminStatusLabel("all")}</option>
            </select>
            <select
              className="admin-select"
              onChange={(event) => setOrigin(event.target.value as (typeof ORIGINS)[number])}
              value={origin}
            >
              {ORIGINS.map((value) => (
                <option key={value} value={value}>
                  {originLabel(value)}
                </option>
              ))}
            </select>
          </div>
        </div>
        {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
        <ModerationTable
          items={items}
          loading={loading}
          onManualStatus={handleManualStatus}
          onReview={handleReview}
        />
      </section>
    </div>
  );
}
