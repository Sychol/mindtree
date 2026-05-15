import type { DraftAnswerMap } from "../types/answer";
import type { Question } from "../types/question";

const PREFIX = "maeumnamu";

function localKey(eventSlug: string, key: "resumeToken" | "sessionId"): string {
  return `${PREFIX}:${eventSlug}:${key}`;
}

function sessionKey(eventSlug: string, sessionId: string, key: string): string {
  return `${PREFIX}:${eventSlug}:${sessionId}:${key}`;
}

function safeGet(storage: Storage, key: string): string | null {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(storage: Storage, key: string, value: string): void {
  try {
    storage.setItem(key, value);
  } catch {
    // Storage can be unavailable in private modes; the app still works in memory.
  }
}

function safeRemove(storage: Storage, key: string): void {
  try {
    storage.removeItem(key);
  } catch {
    // Ignore storage failures.
  }
}

export function getStoredResumeToken(eventSlug: string): string | undefined {
  return safeGet(window.localStorage, localKey(eventSlug, "resumeToken")) ?? undefined;
}

export function setStoredResumeToken(eventSlug: string, resumeToken: string): void {
  safeSet(window.localStorage, localKey(eventSlug, "resumeToken"), resumeToken);
}

export function getStoredSessionId(eventSlug: string): string | undefined {
  return safeGet(window.localStorage, localKey(eventSlug, "sessionId")) ?? undefined;
}

export function setStoredSessionId(eventSlug: string, sessionId: string): void {
  safeSet(window.localStorage, localKey(eventSlug, "sessionId"), sessionId);
}

export function getQuestionsCache(eventSlug: string, sessionId: string): Question[] | undefined {
  const raw = safeGet(window.sessionStorage, sessionKey(eventSlug, sessionId, "questionsCache"));
  if (!raw) {
    return undefined;
  }
  try {
    return JSON.parse(raw) as Question[];
  } catch {
    return undefined;
  }
}

export function setQuestionsCache(eventSlug: string, sessionId: string, questions: Question[]): void {
  safeSet(
    window.sessionStorage,
    sessionKey(eventSlug, sessionId, "questionsCache"),
    JSON.stringify(questions)
  );
}

export function getQuestionDraft(eventSlug: string, sessionId: string): DraftAnswerMap {
  const raw = safeGet(window.sessionStorage, sessionKey(eventSlug, sessionId, "questionDraft"));
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw) as DraftAnswerMap;
  } catch {
    return {};
  }
}

export function setQuestionDraft(eventSlug: string, sessionId: string, draft: DraftAnswerMap): void {
  safeSet(window.sessionStorage, sessionKey(eventSlug, sessionId, "questionDraft"), JSON.stringify(draft));
  safeSet(window.sessionStorage, sessionKey(eventSlug, sessionId, "lastLocalUpdatedAt"), new Date().toISOString());
}

export function getCurrentQuestionNo(eventSlug: string, sessionId: string): number | undefined {
  const value = safeGet(window.sessionStorage, sessionKey(eventSlug, sessionId, "currentQuestionNo"));
  if (!value) {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function setCurrentQuestionNo(eventSlug: string, sessionId: string, questionNo: number): void {
  safeSet(window.sessionStorage, sessionKey(eventSlug, sessionId, "currentQuestionNo"), String(questionNo));
  safeSet(window.sessionStorage, sessionKey(eventSlug, sessionId, "lastLocalUpdatedAt"), new Date().toISOString());
}

export function clearQuestionTemporaryStorage(eventSlug: string, sessionId: string): void {
  for (const key of ["questionDraft", "currentQuestionNo", "lastLocalUpdatedAt"]) {
    safeRemove(window.sessionStorage, sessionKey(eventSlug, sessionId, key));
  }
}

export function getMindCardDraft(eventSlug: string, sessionId: string): string {
  return safeGet(window.sessionStorage, sessionKey(eventSlug, sessionId, "mindCardDraft")) ?? "";
}

export function setMindCardDraft(eventSlug: string, sessionId: string, value: string): void {
  safeSet(window.sessionStorage, sessionKey(eventSlug, sessionId, "mindCardDraft"), value);
}

export function clearMindCardDraft(eventSlug: string, sessionId: string): void {
  safeRemove(window.sessionStorage, sessionKey(eventSlug, sessionId, "mindCardDraft"));
}

export function getReplyDraft(eventSlug: string, sessionId: string): string {
  return safeGet(window.sessionStorage, sessionKey(eventSlug, sessionId, "replyDraft")) ?? "";
}

export function setReplyDraft(eventSlug: string, sessionId: string, value: string): void {
  safeSet(window.sessionStorage, sessionKey(eventSlug, sessionId, "replyDraft"), value);
}

export function clearReplyDraft(eventSlug: string, sessionId: string): void {
  safeRemove(window.sessionStorage, sessionKey(eventSlug, sessionId, "replyDraft"));
}

export function getSelectedCardId(eventSlug: string, sessionId: string): string | undefined {
  return safeGet(window.sessionStorage, sessionKey(eventSlug, sessionId, "selectedCardId")) ?? undefined;
}

export function setSelectedCardId(eventSlug: string, sessionId: string, selectedCardId: string): void {
  safeSet(window.sessionStorage, sessionKey(eventSlug, sessionId, "selectedCardId"), selectedCardId);
}
