import { useParams } from "react-router-dom";

import { RewardCodeLookup } from "../../components/admin/RewardCodeLookup";

export function AdminRewardsPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();

  return (
    <section className="admin-section">
      <div className="admin-section__header">
        <div>
          <p className="admin-eyebrow">상품 지급</p>
          <h2>완료 코드 조회</h2>
        </div>
      </div>
      <RewardCodeLookup eventSlug={eventSlug} />
    </section>
  );
}
