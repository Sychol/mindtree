import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { listAdminReplies, reviewAdminReply } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import { ModerationTable } from "../../components/admin/ModerationTable";
import type { AdminReplyReviewItem, AdminReviewItemBase, AdminReviewRequest } from "../../types/admin";

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  return "Request failed.";
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
          <p className="admin-eyebrow">{total} items</p>
          <h2>Reply review</h2>
        </div>
        <select className="admin-select" onChange={(event) => setStatus(event.target.value)} value={status}>
          <option value="review">review</option>
          <option value="safe">safe</option>
          <option value="exclude">exclude</option>
          <option value="pending">pending</option>
          <option value="public">public</option>
          <option value="hidden">hidden</option>
          <option value="excluded">excluded</option>
          <option value="all">all</option>
        </select>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      <ModerationTable items={items} loading={loading} onReview={handleReview} />
    </section>
  );
}
