import { Link, useParams } from "react-router-dom";

import { NoticeBox } from "../../components/common/NoticeBox";

export function SubmitResultPage() {
  const { eventSlug } = useParams();
  const summaryPath = `/e/${encodeURIComponent(eventSlug ?? "fire-expo-2026")}/summary`;

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">섹션 8 / 8</p>
        <h1>참여해주셔서 감사합니다.</h1>
        <p>응답이 저장되었습니다.</p>
      </div>
      <NoticeBox tone="safe">
        <p>이제 마음신호 요약을 확인할 수 있습니다.</p>
      </NoticeBox>
      <Link className="button button--primary button--full" to={summaryPath}>
        마음신호 요약 보기
      </Link>
    </main>
  );
}
