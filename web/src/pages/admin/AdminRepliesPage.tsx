import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { listAdminReplies, reviewAdminReply } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import { ModerationTable } from "../../components/admin/ModerationTable";
import type { AdminReplyReviewItem, AdminReviewItemBase, AdminReviewRequest } from "../../types/admin";
import { adminErrorMessage, adminStatusLabel } from "../../utils/adminLabels";

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return adminErrorMessage(error, "응원 문장 목록을 불러오지 못했습니다.");
  }
  return "응원 문장 목록을 불러오지 못했습니다.";
}

export function AdminRepliesPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const [status, setStatus] = useState("review");
  const [items, setItems] = useState<AdminReplyReviewItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listAdminReplies(eventSlug, { status });
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
  }, [eventSlug, status]);

  const handleReview = async (item: AdminReviewItemBase, request: AdminReviewRequest) => {
    await reviewAdminReply(item.id, request);
    await load();
  };

  return (
    <section className="admin-section">
      <div className="admin-section__header">
        <div>
          <p className="admin-eyebrow">{total}건</p>
          <h2>응원 문장 검수</h2>
        </div>
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
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      <ModerationTable items={items} loading={loading} onReview={handleReview} />
    </section>
  );
}
