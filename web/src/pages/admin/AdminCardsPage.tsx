import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { listAdminCards, reviewAdminCard } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import { ModerationTable } from "../../components/admin/ModerationTable";
import type { AdminCardReviewItem, AdminReviewItemBase, AdminReviewRequest } from "../../types/admin";
import { adminErrorMessage, adminStatusLabel } from "../../utils/adminLabels";

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return adminErrorMessage(error, "마음카드 목록을 불러오지 못했습니다.");
  }
  return "마음카드 목록을 불러오지 못했습니다.";
}

export function AdminCardsPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const [status, setStatus] = useState("review");
  const [items, setItems] = useState<AdminCardReviewItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listAdminCards(eventSlug, { status });
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
    await reviewAdminCard(item.id, request);
    await load();
  };

  return (
    <section className="admin-section">
      <ListHeader title="마음카드 검수" status={status} total={total} onStatusChange={setStatus} />
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      <ModerationTable items={items} loading={loading} onReview={handleReview} />
    </section>
  );
}

function ListHeader({
  title,
  status,
  total,
  onStatusChange,
}: {
  title: string;
  status: string;
  total: number;
  onStatusChange: (status: string) => void;
}) {
  return (
    <div className="admin-section__header">
      <div>
        <p className="admin-eyebrow">{total}건</p>
        <h2>{title}</h2>
      </div>
      <select className="admin-select" onChange={(event) => onStatusChange(event.target.value)} value={status}>
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
  );
}
