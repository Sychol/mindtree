import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "react-router-dom";

import {
  createManualKeyword,
  listAdminKeywords,
  updateAdminKeyword,
  updateManualKeywordStatus,
} from "../../api/admin";
import { ApiClientError } from "../../api/client";
import { ContentOriginBadge } from "../../components/admin/ContentOriginBadge";
import type {
  AdminKeywordItem,
  AdminManualKeywordCreateRequest,
  AdminManualKeywordStatusRequest,
  ContentOrigin,
} from "../../types/admin";
import {
  adminCategoryLabel,
  adminErrorMessage,
  adminSourceTypeLabel,
  adminStatusLabel,
} from "../../utils/adminLabels";

type KeywordDraft = {
  normalizedKeyword: string;
  category: string;
  status: string;
  reason: string;
};

type ManualKeywordForm = {
  keywordText: string;
  normalizedKeyword: string;
  category: AdminManualKeywordCreateRequest["category"];
  weight: string;
  status: AdminManualKeywordStatusRequest["status"];
  originTag: string;
  reason: string;
};

const CATEGORIES: AdminManualKeywordCreateRequest["category"][] = [
  "mind_signal",
  "support",
  "recovery",
  "coping",
  "neutral",
];
const STATUSES: AdminManualKeywordStatusRequest["status"][] = ["active", "hidden", "excluded"];
const ORIGINS = ["all", "participant", "admin_manual", "system_seed"] as const;

const DEFAULT_MANUAL_FORM: ManualKeywordForm = {
  keywordText: "",
  normalizedKeyword: "",
  category: "neutral",
  weight: "3",
  status: "active",
  originTag: "운영자추가",
  reason: "",
};

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return adminErrorMessage(error, "키워드 요청에 실패했습니다.");
  }
  return "키워드 요청에 실패했습니다.";
}

function originLabel(value: string): string {
  if (value === "all") {
    return "전체 출처";
  }
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

function keywordOrigin(keyword: AdminKeywordItem): ContentOrigin {
  return keyword.origin ?? "participant";
}

function isManualStatusOrigin(origin: ContentOrigin): boolean {
  return origin === "admin_manual" || origin === "system_seed";
}

function initialDraft(keyword: AdminKeywordItem): KeywordDraft {
  return {
    normalizedKeyword: keyword.normalizedKeyword,
    category: keyword.category,
    status: keyword.status,
    reason: "",
  };
}

export function AdminKeywordsPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const [status, setStatus] = useState("all");
  const [category, setCategory] = useState("");
  const [origin, setOrigin] = useState<(typeof ORIGINS)[number]>("all");
  const [items, setItems] = useState<AdminKeywordItem[]>([]);
  const [drafts, setDrafts] = useState<Record<string, KeywordDraft>>({});
  const [manualForm, setManualForm] = useState<ManualKeywordForm>(DEFAULT_MANUAL_FORM);
  const [manualReasons, setManualReasons] = useState<Record<string, string>>({});
  const [submittingManual, setSubmittingManual] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const response = await listAdminKeywords(eventSlug, { status, category, origin });
      setItems(response.items);
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };

  useEffect(() => {
    void load();
  }, [eventSlug, status, category, origin]);

  const patchDraft = (keyword: AdminKeywordItem, patch: Partial<KeywordDraft>) => {
    setDrafts((current) => ({
      ...current,
      [keyword.id]: {
        ...(current[keyword.id] ?? initialDraft(keyword)),
        ...patch,
      },
    }));
  };

  const patchManualForm = (patch: Partial<ManualKeywordForm>) => {
    setManualForm((current) => ({ ...current, ...patch }));
  };

  const saveKeyword = async (keyword: AdminKeywordItem) => {
    const draft = drafts[keyword.id] ?? initialDraft(keyword);
    await updateAdminKeyword(keyword.id, {
      normalizedKeyword: draft.normalizedKeyword,
      category: draft.category,
      status: draft.status,
      reason: draft.reason || null,
    });
    setDrafts((current) => {
      const next = { ...current };
      delete next[keyword.id];
      return next;
    });
    await load();
  };

  const submitManualKeyword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmittingManual(true);
    try {
      await createManualKeyword(eventSlug, {
        keywordText: manualForm.keywordText,
        normalizedKeyword: manualForm.normalizedKeyword.trim() || undefined,
        category: manualForm.category,
        weight: Number(manualForm.weight || 3),
        status: manualForm.status,
        originTag: manualForm.originTag.trim() || undefined,
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

  const setManualReason = (keywordId: string, reason: string) => {
    setManualReasons((current) => ({ ...current, [keywordId]: reason }));
  };

  const changeManualStatus = async (
    keyword: AdminKeywordItem,
    nextStatus: AdminManualKeywordStatusRequest["status"]
  ) => {
    const reason = (manualReasons[keyword.id] ?? "").trim();
    if (!reason) {
      setError("수동 키워드 상태 변경 사유를 입력해 주세요.");
      return;
    }
    setError(null);
    try {
      await updateManualKeywordStatus(keyword.id, { status: nextStatus, reason });
      setManualReasons((current) => {
        const next = { ...current };
        delete next[keyword.id];
        return next;
      });
      await load();
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };

  return (
    <div className="admin-page-stack">
      <section className="admin-section">
        <div className="admin-section__header">
          <div>
            <p className="admin-eyebrow">TV word cloud</p>
            <h2>수동 키워드 추가</h2>
          </div>
        </div>
        <form className="admin-form-grid" onSubmit={submitManualKeyword}>
          <label className="admin-field">
            키워드
            <input
              className="admin-input"
              maxLength={40}
              onChange={(event) => patchManualForm({ keywordText: event.target.value })}
              required
              value={manualForm.keywordText}
            />
          </label>
          <label className="admin-field">
            정규화
            <input
              className="admin-input"
              maxLength={40}
              onChange={(event) => patchManualForm({ normalizedKeyword: event.target.value })}
              value={manualForm.normalizedKeyword}
            />
          </label>
          <label className="admin-field">
            분류
            <select
              className="admin-select"
              onChange={(event) =>
                patchManualForm({ category: event.target.value as AdminManualKeywordCreateRequest["category"] })
              }
              value={manualForm.category}
            >
              {CATEGORIES.map((value) => (
                <option key={value} value={value}>
                  {adminCategoryLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label className="admin-field">
            가중치
            <input
              className="admin-input"
              max={50}
              min={1}
              onChange={(event) => patchManualForm({ weight: event.target.value })}
              type="number"
              value={manualForm.weight}
            />
          </label>
          <label className="admin-field">
            상태
            <select
              className="admin-select"
              onChange={(event) =>
                patchManualForm({ status: event.target.value as AdminManualKeywordStatusRequest["status"] })
              }
              value={manualForm.status}
            >
              {STATUSES.map((value) => (
                <option key={value} value={value}>
                  {adminStatusLabel(value)}
                </option>
              ))}
            </select>
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
            <p className="admin-eyebrow">{items.length}개 키워드</p>
            <h2>키워드 관리</h2>
          </div>
          <div className="admin-filter-row">
            <select className="admin-select" onChange={(event) => setStatus(event.target.value)} value={status}>
              <option value="active">{adminStatusLabel("active")}</option>
              <option value="hidden">{adminStatusLabel("hidden")}</option>
              <option value="excluded">{adminStatusLabel("excluded")}</option>
              <option value="all">{adminStatusLabel("all")}</option>
            </select>
            <select className="admin-select" onChange={(event) => setCategory(event.target.value)} value={category}>
              <option value="">전체 분류</option>
              {CATEGORIES.map((value) => (
                <option key={value} value={value}>
                  {adminCategoryLabel(value)}
                </option>
              ))}
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
        <div className="admin-table-wrap">
          <table className="admin-table admin-table--keywords">
            <thead>
              <tr>
                <th>키워드</th>
                <th>정규화</th>
                <th>분류</th>
                <th>상태</th>
                <th>출처</th>
                <th>원본</th>
                <th>조치</th>
              </tr>
            </thead>
            <tbody>
              {items.map((keyword) => {
                const itemOrigin = keywordOrigin(keyword);
                const manualStatus = isManualStatusOrigin(itemOrigin);
                const draft = drafts[keyword.id] ?? initialDraft(keyword);
                const sourceIdLabel = keyword.sourceId ? keyword.sourceId.slice(0, 8) : "-";
                return (
                  <tr key={keyword.id}>
                    <td>
                      <strong>{keyword.keywordText}</strong>
                      <span className="admin-muted">weight {keyword.weight}</span>
                    </td>
                    <td>
                      {manualStatus ? (
                        <span>{keyword.normalizedKeyword}</span>
                      ) : (
                        <input
                          className="admin-input"
                          onChange={(event) => patchDraft(keyword, { normalizedKeyword: event.target.value })}
                          value={draft.normalizedKeyword}
                        />
                      )}
                    </td>
                    <td>
                      {manualStatus ? (
                        <span>{adminCategoryLabel(keyword.category)}</span>
                      ) : (
                        <select
                          className="admin-select"
                          onChange={(event) => patchDraft(keyword, { category: event.target.value })}
                          value={draft.category}
                        >
                          {CATEGORIES.map((value) => (
                            <option key={value} value={value}>
                              {adminCategoryLabel(value)}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td>
                      {manualStatus ? (
                        <span className="admin-badge">{adminStatusLabel(keyword.status)}</span>
                      ) : (
                        <select
                          className="admin-select"
                          onChange={(event) => patchDraft(keyword, { status: event.target.value })}
                          value={draft.status}
                        >
                          {STATUSES.map((value) => (
                            <option key={value} value={value}>
                              {adminStatusLabel(value)}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td>
                      <ContentOriginBadge origin={itemOrigin} originTag={keyword.originTag} />
                      {keyword.createdByAdminId ? (
                        <span className="admin-muted">{keyword.createdByAdminId.slice(0, 8)}</span>
                      ) : null}
                    </td>
                    <td>
                      {adminSourceTypeLabel(keyword.sourceType)}
                      <span className="admin-muted">{sourceIdLabel}</span>
                    </td>
                    <td>
                      {manualStatus ? (
                        <div className="admin-keyword-actions">
                          <input
                            className="admin-input"
                            maxLength={500}
                            onChange={(event) => setManualReason(keyword.id, event.target.value)}
                            placeholder="상태 변경 사유"
                            value={manualReasons[keyword.id] ?? ""}
                          />
                          <div className="admin-inline-actions">
                            {keyword.status === "active" ? (
                              <>
                                <button
                                  className="admin-button admin-button--secondary"
                                  onClick={() => void changeManualStatus(keyword, "hidden")}
                                  type="button"
                                >
                                  숨김
                                </button>
                                <button
                                  className="admin-button admin-button--secondary"
                                  onClick={() => void changeManualStatus(keyword, "excluded")}
                                  type="button"
                                >
                                  제외
                                </button>
                              </>
                            ) : (
                              <button
                                className="admin-button admin-button--primary"
                                onClick={() => void changeManualStatus(keyword, "active")}
                                type="button"
                              >
                                복구
                              </button>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="admin-keyword-actions">
                          <input
                            className="admin-input"
                            maxLength={500}
                            onChange={(event) => patchDraft(keyword, { reason: event.target.value })}
                            placeholder="변경 사유"
                            value={draft.reason}
                          />
                          <button
                            className="admin-button admin-button--primary"
                            onClick={() => void saveKeyword(keyword)}
                            type="button"
                          >
                            저장
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
