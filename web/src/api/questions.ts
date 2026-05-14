import { requestJson } from "./client";
import type { QuestionsResponse } from "../types/question";

export function getQuestions(eventSlug: string): Promise<QuestionsResponse> {
  return requestJson<QuestionsResponse>(`/events/${encodeURIComponent(eventSlug)}/questions`);
}
