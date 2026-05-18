import type { SessionInfo, SessionProgress, SessionStatus } from "../types/session";

const STATUS_ORDER: SessionStatus[] = [
  "created",
  "consented",
  "questions_completed",
  "summary_viewed",
  "card_created",
  "reply_created",
  "completed"
];

export function statusAtLeast(current: SessionStatus, target: SessionStatus): boolean {
  const currentIndex = STATUS_ORDER.indexOf(current);
  const targetIndex = STATUS_ORDER.indexOf(target);
  return currentIndex >= 0 && targetIndex >= 0 && currentIndex >= targetIndex;
}

export function routeForSessionStatus(
  eventSlug: string,
  session: SessionInfo,
  progress?: SessionProgress
): string {
  const base = `/e/${encodeURIComponent(eventSlug)}`;

  if (session.status === "created") {
    return `${base}/consent`;
  }
  if (session.status === "consented") {
    return `${base}/questions`;
  }
  if (statusAtLeast(session.status, "questions_completed") && !statusAtLeast(session.status, "summary_viewed")) {
    return `${base}/summary`;
  }
  if (statusAtLeast(session.status, "summary_viewed") && !statusAtLeast(session.status, "card_created")) {
    return `${base}/cards/new`;
  }
  if (session.status === "card_created") {
    if (progress?.selectedCard) {
      return `${base}/replies/new`;
    }
    return (progress?.mindCardCount ?? 0) >= 3 ? `${base}/cards/select` : `${base}/cards/new`;
  }
  if (statusAtLeast(session.status, "reply_created") || progress?.completionCodeIssued) {
    return `${base}/complete`;
  }
  return `${base}/questions`;
}
