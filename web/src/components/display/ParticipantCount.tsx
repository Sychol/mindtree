type ParticipantCountProps = {
  participantCount: number;
  completedCount: number;
};

export function ParticipantCount({ participantCount, completedCount }: ParticipantCountProps) {
  return (
    <div className="display-counts" aria-label="참여 현황">
      <div className="display-count">
        <span>참여자 수</span>
        <strong>{participantCount.toLocaleString("ko-KR")}</strong>
      </div>
      <div className="display-count display-count--complete">
        <span>완료자 수</span>
        <strong>{completedCount.toLocaleString("ko-KR")}</strong>
      </div>
    </div>
  );
}
