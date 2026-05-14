import { Link, useParams } from "react-router-dom";

import { NoticeBox } from "../../components/common/NoticeBox";

export function SubmitResultPage() {
  const { eventSlug } = useParams();
  const summaryPath = `/e/${encodeURIComponent(eventSlug ?? "fire-expo-2026")}/summary`;

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">저장 완료</p>
        <h1>문항 응답이 저장되었습니다.</h1>
      </div>
      <NoticeBox tone="safe">
        <p>다음 단계에서는 마음신호 요약을 확인하게 됩니다.</p>
      </NoticeBox>
      <Link className="button button--primary button--full" to={summaryPath}>
        다음 단계로 이동
      </Link>
    </main>
  );
}
