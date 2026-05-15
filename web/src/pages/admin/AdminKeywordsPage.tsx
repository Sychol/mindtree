import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { listAdminKeywords, updateAdminKeyword } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import type { AdminKeywordItem } from "../../types/admin";
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

const CATEGORIES = ["mind_signal", "support", "recovery", "coping", "neutral"];
const STATUSES = ["active", "hidden", "excluded"];

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return adminErrorMessage(error, "키워드 요청에 실패했습니다.");
  }
  return "키워드 요청에 실패했습니다.";
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
  const [status, setStatus] = useState("active");
  const [category, setCategory] = useState("");
  const [items, setItems] = useState<AdminKeywordItem[]>([]);
  const [drafts, setDrafts] = useState<Record<string, KeywordDraft>>({});
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const response = await listAdminKeywords(eventSlug, { status, category });
      setItems(response.items);
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };

  useEffect(() => {
    void load();
  }, [eventSlug, status, category]);

  const patchDraft = (keyword: AdminKeywordItem, patch: Partial<KeywordDraft>) => {
    setDrafts((current) => ({
      ...current,
      [keyword.id]: {
        ...(current[keyword.id] ?? initialDraft(keyword)),
        ...patch,
      },
    }));
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

  return (
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
        </div>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>키워드</th>
              <th>정규화</th>
              <th>분류</th>
              <th>상태</th>
              <th>원본</th>
              <th>조치</th>
            </tr>
          </thead>
          <tbody>
            {items.map((keyword) => {
              const draft = drafts[keyword.id] ?? initialDraft(keyword);
              return (
                <tr key={keyword.id}>
                  <td>
                    <strong>{keyword.keywordText}</strong>
                    <span className="admin-muted">{keyword.weight}</span>
                  </td>
                  <td>
                    <input
                      className="admin-input"
                      onChange={(event) => patchDraft(keyword, { normalizedKeyword: event.target.value })}
                      value={draft.normalizedKeyword}
                    />
                  </td>
                  <td>
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
                  </td>
                  <td>
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
                  </td>
                  <td>
                    {adminSourceTypeLabel(keyword.sourceType)}
                    <span className="admin-muted"> {keyword.sourceId.slice(0, 8)}</span>
                  </td>
                  <td>
                    <input
                      className="admin-input"
                      onChange={(event) => patchDraft(keyword, { reason: event.target.value })}
                      placeholder="변경 사유"
                      value={draft.reason}
                    />
                    <button className="admin-button admin-button--primary" onClick={() => void saveKeyword(keyword)} type="button">
                      저장
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
