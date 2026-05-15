import { API_BASE_URL, requestJson } from "./client";
import type { DisplaySnapshot } from "../types/display";
import { warnIfDisplayContractUnsafe } from "../utils/displayContractCheck";

export function getDisplaySnapshot(eventSlug: string): Promise<DisplaySnapshot> {
  return requestJson<DisplaySnapshot>(`/events/${encodeURIComponent(eventSlug)}/display/snapshot`).then((snapshot) => {
    warnIfDisplayContractUnsafe(snapshot);
    return snapshot;
  });
}

export function getDisplayStreamUrl(eventSlug: string): string {
  return `${API_BASE_URL}/events/${encodeURIComponent(eventSlug)}/stream`;
}
