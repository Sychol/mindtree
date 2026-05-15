const PREFIX = "maeumnamu";

const TEMPORARY_SESSION_KEYS = [
  "questionDraft",
  "currentQuestionNo",
  "lastLocalUpdatedAt",
  "mindCardDraft",
  "replyDraft",
  "selectedCardId"
] as const;

function sessionKey(eventSlug: string, sessionId: string, key: string): string {
  return `${PREFIX}:${eventSlug}:${sessionId}:${key}`;
}

function safeRemove(storage: Storage, key: string): void {
  try {
    storage.removeItem(key);
  } catch {
    // Storage may be unavailable in private modes.
  }
}

export function cleanupCompletedParticipantStorage(eventSlug: string, sessionId: string): void {
  for (const key of TEMPORARY_SESSION_KEYS) {
    safeRemove(window.sessionStorage, sessionKey(eventSlug, sessionId, key));
  }
}

export function listTemporaryParticipantStorageKeys(eventSlug: string, sessionId: string): string[] {
  return TEMPORARY_SESSION_KEYS.map((key) => sessionKey(eventSlug, sessionId, key));
}
