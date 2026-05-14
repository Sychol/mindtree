import { requestJson } from "./client";
import type {
  ConsentRequest,
  ConsentResponse,
  CreateOrResumeSessionRequest,
  CreateOrResumeSessionResponse,
  SessionStatusResponse
} from "../types/session";

export function createOrResumeSession(
  eventSlug: string,
  request: CreateOrResumeSessionRequest
): Promise<CreateOrResumeSessionResponse> {
  return requestJson<CreateOrResumeSessionResponse>(
    `/events/${encodeURIComponent(eventSlug)}/sessions`,
    {
      method: "POST",
      body: request
    }
  );
}

export function getSession(sessionId: string): Promise<SessionStatusResponse> {
  return requestJson<SessionStatusResponse>(`/sessions/${encodeURIComponent(sessionId)}`);
}

export function submitConsent(
  sessionId: string,
  request: ConsentRequest
): Promise<ConsentResponse> {
  return requestJson<ConsentResponse>(`/sessions/${encodeURIComponent(sessionId)}/consent`, {
    method: "POST",
    body: request
  });
}
