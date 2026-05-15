import { useParams } from "react-router-dom";

import { RewardCodeLookup } from "../../components/admin/RewardCodeLookup";

export function AdminRewardsPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();

  return (
    <section className="admin-section">
      <div className="admin-section__header">
        <div>
          <p className="admin-eyebrow">Rewards</p>
          <h2>Completion code lookup</h2>
        </div>
      </div>
      <RewardCodeLookup eventSlug={eventSlug} />
    </section>
  );
}
