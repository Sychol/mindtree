import { requestJson } from "./client";
import type { BulkAnswersRequest, BulkAnswersResponse } from "../types/answer";

export function submitAnswersBulk(
  sessionId: string,
  request: BulkAnswersRequest,
  idempotencyKey?: string
): Promise<BulkAnswersResponse> {
  return requestJson<BulkAnswersResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/answers/bulk`,
    {
      method: "PUT",
      body: request,
      idempotencyKey
    }
  );
}
