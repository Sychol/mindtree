import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "react-router-dom";

import {
  createManualCard,
  listAdminCards,
  reviewAdminCard,
  updateManualCardStatus,
} from "../../api/admin";
import { ApiClientError } from "../../api/client";
import { ModerationTable } from "../../components/admin/ModerationTable";
import type {
  AdminCardReviewItem,
  AdminManualCardCreateRequest,
  AdminManualContentStatusRequest,
  AdminReviewItemBase,
  AdminReviewRequest,
} from "../../types/admin";
import { adminErrorMessage, adminPromptTypeLabel, adminStatusLabel } from "../../utils/adminLabels";

const ORIGINS = ["all", "participant", "admin_manual", "system_seed"] as const;
const PROMPT_TYPES = ["to_past_me", "to_now_me", "to_colleague", "stress_memory"] as const;
const PUBLIC_STATUSES: Array<NonNullable<AdminManualCardCreateRequest["publicStatus"]>> = [
  "public",
  "pending",
  "hidden",
  "excluded",
];

type ManualCardForm = {
  promptType: string;
  content: string;
  originTag: string;
  publicStatus: NonNullable<AdminManualCardCreateRequest["publicStatus"]>;
  createKeywordJob: boolean;
  reason: string;
};

const DEFAULT_MANUAL_FORM: ManualCardForm = {
  promptType: "to_colleague",
  content: "",
  originTag: "운영자추가",
  publicStatus: "public",
  createKeywordJob: true,
  reason: "",
};

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return adminErrorMessage(error, "마음카드 요청을 처리하지 못했습니다.");
  }
  return "마음카드 요청을 처리하지 못했습니다.";
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

export function AdminCardsPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const [status, setStatus] = useState("all");
  const [origin, setOrigin] = useState<(typeof ORIGINS)[number]>("all");
  const [items, setItems] = useState<AdminCardReviewItem[]>([]);
  const [total, setTotal] = useState(0);
  const [manualForm, setManualForm] = useState<ManualCardForm>(DEFAULT_MANUAL_FORM);
  const [loading, setLoading] = useState(false);
  const [submittingManual, setSubmittingManual] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listAdminCards(eventSlug, { status, origin });
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

  const patchManualForm = (patch: Partial<ManualCardForm>) => {
    setManualForm((current) => ({ ...current, ...patch }));
  };

  const handleManualSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmittingManual(true);
    setError(null);
    try {
      await createManualCard(eventSlug, {
        promptType: manualForm.promptType,
        content: manualForm.content,
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
    await reviewAdminCard(item.id, request);
    await load();
  };

  const handleManualStatus = async (
    item: AdminReviewItemBase,
    request: AdminManualContentStatusRequest
  ) => {
    await updateManualCardStatus(item.id, request);
    await load();
  };

  return (
    <div className="admin-page-stack">
      <section className="admin-section">
        <div className="admin-section__header">
          <div>
            <p className="admin-eyebrow">manual card</p>
            <h2>수동 마음카드 추가</h2>
          </div>
        </div>
        <form className="admin-form-grid" onSubmit={handleManualSubmit}>
          <label className="admin-field">
            카드 유형
            <select
              className="admin-select"
              onChange={(event) => patchManualForm({ promptType: event.target.value })}
              value={manualForm.promptType}
            >
              {PROMPT_TYPES.map((value) => (
                <option key={value} value={value}>
                  {adminPromptTypeLabel(value)}
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
                  publicStatus: event.target.value as ManualCardForm["publicStatus"],
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
            <h2>마음카드 검토</h2>
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
