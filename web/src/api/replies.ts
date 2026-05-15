import { requestJson } from "./client";
import type { CreateReplyRequest, CreateReplyResponse } from "../types/reply";

export function createReply(
  sessionId: string,
  request: CreateReplyRequest
): Promise<CreateReplyResponse> {
  return requestJson<CreateReplyResponse>(`/sessions/${encodeURIComponent(sessionId)}/replies`, {
    method: "POST",
    body: request
  });
}
