import { requestJson } from "./client";
import type { PublicEventResponse } from "../types/event";

export function getPublicEvent(eventSlug: string): Promise<PublicEventResponse> {
  return requestJson<PublicEventResponse>(`/events/${encodeURIComponent(eventSlug)}/public`);
}
