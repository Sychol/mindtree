import { requestJson } from "./client";
import type { SummaryResponse, SummaryViewedResponse } from "../types/summary";

export function getSummary(sessionId: string): Promise<SummaryResponse> {
  return requestJson<SummaryResponse>(`/sessions/${encodeURIComponent(sessionId)}/summary`);
}

export function markSummaryViewed(sessionId: string): Promise<SummaryViewedResponse> {
  return requestJson<SummaryViewedResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/summary/viewed`,
    {
      method: "POST"
    }
  );
}
