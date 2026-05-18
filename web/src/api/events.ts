import { requestJson } from "./client";
import type { PublicEventResponse } from "../types/event";
import type { PublicSurveyContentResponse } from "../types/survey";

export function getPublicEvent(eventSlug: string): Promise<PublicEventResponse> {
  return requestJson<PublicEventResponse>(`/events/${encodeURIComponent(eventSlug)}/public`);
}

export function getPublicSurveyContent(eventSlug: string): Promise<PublicSurveyContentResponse> {
  return requestJson<PublicSurveyContentResponse>(
    `/events/${encodeURIComponent(eventSlug)}/survey-content`
  );
}
