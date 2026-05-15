import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { listAdminKeywords, updateAdminKeyword } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import type { AdminKeywordItem } from "../../types/admin";

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
    return error.message;
  }
  return "Request failed.";
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
          <p className="admin-eyebrow">{items.length} keywords</p>
          <h2>Keyword management</h2>
        </div>
        <div className="admin-filter-row">
          <select className="admin-select" onChange={(event) => setStatus(event.target.value)} value={status}>
            <option value="active">active</option>
            <option value="hidden">hidden</option>
            <option value="excluded">excluded</option>
            <option value="all">all</option>
          </select>
          <select className="admin-select" onChange={(event) => setCategory(event.target.value)} value={category}>
            <option value="">all categories</option>
            {CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {value}
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
              <th>Keyword</th>
              <th>Normalized</th>
              <th>Category</th>
              <th>Status</th>
              <th>Source</th>
              <th>Action</th>
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
                          {value}
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
                          {value}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    {keyword.sourceType}
                    <span className="admin-muted"> {keyword.sourceId.slice(0, 8)}</span>
                  </td>
                  <td>
                    <input
                      className="admin-input"
                      onChange={(event) => patchDraft(keyword, { reason: event.target.value })}
                      placeholder="Reason"
                      value={draft.reason}
                    />
                    <button className="admin-button admin-button--primary" onClick={() => void saveKeyword(keyword)} type="button">
                      Save
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
